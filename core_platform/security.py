"""Sanders Dash & Seal: development implementation of bounded authority.

Trusted host library; does not execute payloads or claim OS/network isolation.
Production trust keys must be supplied by separately operated authorities.
"""
import base64
import hashlib
import json
import math
import secrets
import sqlite3
import time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PLATFORM = 'Sanders Dash & Seal'
ROLES = ('IT_AI_Manager_v15.0', 'MINOTAUR')

class Denied(Exception):
    """Fail-closed authorization result."""

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(payload):
    return hashlib.sha256(payload).hexdigest()

def public_hex(key):
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

def sign(key, domain, value):
    return base64.b64encode(key.sign(domain.encode() + b'\0' + canonical(value))).decode()

def verify(key_hex, signature, domain, value):
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(
            base64.b64decode(signature, validate=True), domain.encode() + b'\0' + canonical(value))
    except Exception as exc:
        raise Denied('Invalid cryptographic proof') from exc

class TwinGate:
    def __init__(self, trusted_keys):
        if set(trusted_keys) != set(ROLES) or len(set(trusted_keys.values())) != 2:
            raise ValueError('Two distinct trusted authority keys are required')
        self.keys = dict(trusted_keys)

    def validate(self, domain, body, signatures):
        for role in ROLES:
            if role not in signatures:
                raise Denied('Both authorities must approve')
            verify(self.keys[role], signatures[role], domain, body)

class PBDManifestGenerator:
    @staticmethod
    def prepare(payload, artifact, scope):
        """Prepare unsigned material. This method grants no authority."""
        return {'schema': 1, 'platform': PLATFORM, 'artifact': artifact,
                'payload_hash': digest(payload), 'scope': scope}

class PBDScriptValidationEngine:
    def __init__(self, twin_gate):
        self.gate = twin_gate

    def validate(self, payload, artifact, scope, manifest):
        expected = PBDManifestGenerator.prepare(payload, artifact, scope)
        if manifest.get('body') != expected:
            raise Denied('Manifest payload, identity, or scope mismatch')
        self.gate.validate('pbd-manifest-v1', expected, manifest.get('signatures', {}))
        return expected

class Vault:
    """Durable one-use leases and chained receipts on one trusted SQLite host.

    No private signing keys are held here. SQLite is not an immutable store.
    """
    def __init__(self, path, twin_gate, clock=time.time):
        self.path, self.gate, self.clock = str(path), twin_gate, clock
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS leases (
              id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS receipts (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL, hash TEXT NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def request(self, agent_key, scope, payload, ttl=60, tier='STANDARD'):
        if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 60:
            raise Denied('Lease TTL must be 1–60 seconds')
        if tier not in ('STANDARD', 'EMERGENCY', 'PLATINUM_BLUE_DIAMOND_EMERGENCY'):
            raise Denied('Unknown authority class')
        if set(scope) != {'endpoint', 'method', 'ip', 'operation'} or not all(
                isinstance(v, str) and v for v in scope.values()):
            raise Denied('Exact non-empty scope fields required')
        if any('*' in v for v in scope.values()):
            raise Denied('Wildcard scopes are forbidden')
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(agent_key))
        except Exception as exc:
            raise Denied('Invalid agent public key') from exc
        now = self.clock()
        return {'schema': 1, 'platform': PLATFORM, 'id': secrets.token_hex(32),
                'issued': now, 'expires': now + ttl, 'agent_key': agent_key,
                'scope': dict(scope), 'payload_hash': digest(payload), 'tier': tier,
                'max_execution_limit': 1}

    def mint(self, body, signatures):
        self.gate.validate('pbd-lease-v1', body, signatures)
        now = self.clock()
        try:
            valid = (body['platform'] == PLATFORM and body['schema'] == 1
                and body['max_execution_limit'] == 1
                and math.isfinite(body['issued']) and math.isfinite(body['expires'])
                and body['issued'] <= now < body['expires']
                and 0 < body['expires'] - body['issued'] <= 60)
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise Denied('Invalid lease lifetime or constraints')
        with self.connect() as db:
            try:
                db.execute('INSERT INTO leases VALUES (?, ?, ?)',
                           (body['id'], canonical(body).decode(), 'READY'))
            except sqlite3.IntegrityError as exc:
                raise Denied('Lease already issued') from exc
        return body['id']

    def claim(self, lease_id, scope, payload, agent_proof):
        """Consume authority atomically before an adapter can perform its operation."""
        error = None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body, state FROM leases WHERE id=?', (lease_id,)).fetchone()
            if not row:
                raise Denied('Unknown lease')
            body, state = json.loads(row[0]), row[1]
            try:
                if state != 'READY' or not body['issued'] <= self.clock() < body['expires']:
                    raise Denied('Expired, revoked, or consumed lease')
                if scope != body['scope'] or digest(payload) != body['payload_hash']:
                    raise Denied('Request outside signed scope')
                verify(body['agent_key'], agent_proof, 'pbd-agent-proof-v1', body)
            except Denied as exc:
                error = exc
            db.execute('UPDATE leases SET state=? WHERE id=?',
                       ('REVOKED' if error else 'CONSUMED', lease_id))
        if error:
            raise error
        return body

    def revoke(self, lease_id):
        with self.connect() as db:
            db.execute('UPDATE leases SET state=? WHERE id=?', ('REVOKED', lease_id))

    def state(self, lease_id):
        with self.connect() as db:
            row = db.execute('SELECT state FROM leases WHERE id=?', (lease_id,)).fetchone()
        return row[0] if row else None

    def preserve(self, event):
        """Chained evidence; no secrets or business document payloads are included."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT hash FROM receipts ORDER BY seq DESC LIMIT 1').fetchone()
            body = {'previous_hash': previous[0] if previous else '0' * 64,
                    'timestamp': self.clock(), 'event': event}
            encoded = canonical(body)
            block_hash = digest(encoded)
            db.execute('INSERT INTO receipts(body, hash) VALUES (?, ?)', (encoded.decode(), block_hash))
        return block_hash

    def verify_audit(self):
        previous = '0' * 64
        with self.connect() as db:
            rows = db.execute('SELECT body, hash FROM receipts ORDER BY seq').fetchall()
        for raw, block_hash in rows:
            body = json.loads(raw)
            if body.get('previous_hash') != previous or digest(canonical(body)) != block_hash:
                raise Denied('Audit chain changed')
            previous = block_hash
        return previous

class GlobalPBDSentinel:
    """Read-only integrity scanner. Containment requires a separate deployment adapter."""
    def __init__(self, validator):
        self.validator = validator

    def scan(self, root, scope):
        findings = []
        for path in sorted(Path(root).rglob('*')):
            if path.suffix not in ('.py', '.js', '.sh'):
                continue
            artifact = path.relative_to(root).as_posix()
            try:
                if path.is_symlink():
                    raise Denied('Symlink executable is not accepted')
                manifest = json.loads(Path(str(path) + '.pbd.json').read_text())
                self.validator.validate(path.read_bytes(), artifact, scope, manifest)
                status = 'VALID'
            except (OSError, ValueError, TypeError, Denied):
                status = 'BLOCKED'
            findings.append({'artifact': artifact, 'status': status})
        return findings
