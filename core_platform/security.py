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
        if set(trusted_keys) != set(ROLES):
            raise ValueError('Two distinct trusted authority keys are required')
        decoded = {r: bytes.fromhex(k) for r, k in trusted_keys.items()}
        for value in decoded.values():
            Ed25519PublicKey.from_public_bytes(value)
        if len(set(decoded.values())) != 2:
            raise ValueError('Two distinct trusted authority keys are required')
        self.keys = {r: value.hex() for r, value in decoded.items()}

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
    """Durable one-use leases on one trusted SQLite host.

    No private signing keys are held here. SQLite is not an immutable store.
    """
    def __init__(self, path, twin_gate, max_lifetime, clock=time.time):
        if not max_lifetime or any(type(v) is not int or v < 1 for v in max_lifetime.values()):
            raise ValueError('Explicit positive lease lifetime policy required')
        self.max_lifetime = dict(max_lifetime)
        self.path, self.gate, self.clock = str(path), twin_gate, clock
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS leases (
              id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def request(self, agent_key, scope, payload, ttl, tier, requesting_agent, artifact_hash):
        from .protocol import utc, GATES, assert_record
        if type(ttl) is not int or ttl < 1:
            raise Denied('Explicit positive lease lifetime required')
        now = self.clock()
        body = {
            'lease_metadata': {'lease_id': secrets.token_hex(32),
                'timestamp_utc': utc(now), 'expires_at_utc': utc(now + ttl),
                'nonce': secrets.token_hex(32)},
            'agent_identity': {'requesting_agent': requesting_agent,
                'agent_identity_assertion': '', 'commanding_authority': 'IT_AI_Manager_v15.0'},
            'operational_bounds': {'target_endpoint': scope['endpoint'],
                'allowed_verbs': list(scope['allowed_verbs']),
                'network_jail_ips': list(scope['network_jail_ips']), 'max_execution_limit': 1},
            'dual_governance_gates': {name: '' for name in GATES},
            'execution_binding': {'agent_public_key': agent_key, 'payload_hash': digest(payload),
                'operation': scope['operation'], 'token_class': tier, 'artifact_hash': artifact_hash}}
        assert_record(body, self.max_lifetime, now)
        return body

    def mint(self, body):
        from .protocol import assert_record, signing_material, GATES
        assert_record(body, self.max_lifetime, self.clock())
        material = signing_material(body)
        self.gate.validate('pbd-lease-v2', material,
            dict(zip(ROLES, (body['dual_governance_gates'][name] for name in GATES))))
        verify(body['execution_binding']['agent_public_key'],
               body['agent_identity']['agent_identity_assertion'], 'pbd-agent-assertion-v2', material)
        lease_id = body['lease_metadata']['lease_id']
        with self.connect() as db:
            try:
                db.execute('INSERT INTO leases VALUES (?, ?, ?)',
                           (lease_id, canonical(body).decode(), 'READY'))
            except sqlite3.IntegrityError as exc:
                raise Denied('Lease already issued') from exc
        return lease_id

    def claim(self, lease_id, scope, payload, agent_proof):
        from .protocol import assert_record, check_operation
        error = None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body, state FROM leases WHERE id=?', (lease_id,)).fetchone()
            if not row:
                raise Denied('Unknown lease')
            body, state = json.loads(row[0]), row[1]
            try:
                if state != 'READY':
                    raise Denied('Revoked or consumed lease')
                assert_record(body, self.max_lifetime, self.clock())
                check_operation(body, scope, payload)
                verify(body['execution_binding']['agent_public_key'], agent_proof,
                       'pbd-agent-proof-v2', {'lease': body, 'operation': scope})
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
