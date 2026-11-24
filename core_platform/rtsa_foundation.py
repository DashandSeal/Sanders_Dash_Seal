"""
Module: core_platform.rtsa_foundation
Architectural Layer: Shared RTSA Foundation for the Three Originals
Description: Shared-core capabilities inherited by the three
reconstructed original RTSA platforms — Uncle Nickey / Mao, CareHive
OS, and Sanders Home Healthcare & Caregivers RTSA — each retaining
its own independent identity, architecture, purpose and ownership.

This module provides: a platform identity record with a canonical
integrity digest; identity validation (NAICS codes and authorized
regions); a jurisdiction geofence policy gate; HIPAA-by-design
record-access control in which every granted access writes a
Glass-Box receipt before the record may be served (no record, no
access); and platform check-in records on a caller-owned SQLite
connection.

Honest scope: the identity record plus check-in record in this
module is the Phase I recall / check-in PATTERN at platform scale —
it is NOT the ecosystem recall protocol itself. The geofence is a
policy gate over declared jurisdiction values — it is NOT a location
proof: it evaluates the jurisdiction value a caller declares, and
proves nothing about where anyone physically is.

Python standard library only. No secrets, no network, no external
calls.
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass

REGION = re.compile(r'^[A-Z]{2}(-[A-Z]{2})?$', re.ASCII)
NAICS = re.compile(r'^[0-9]{6}$', re.ASCII)


class FoundationDenied(ValueError):
    """The requested foundation operation is invalid or cannot be
    evidenced, so it does not occur."""


class FoundationForbidden(ValueError):
    """The actor lacks authority for this record access."""


@dataclass(frozen=True)
class PlatformIdentity:
    """One platform's independent identity record. Platforms are
    never merged: each of the three originals carries its own
    identity, its own legal entities, its own NAICS codes and its
    own authorized regions."""

    platform_id: str
    name: str
    legal_entities: tuple = ()
    naics_codes: tuple = ()
    authorized_regions: tuple = ()
    status: str = 'REGISTERED'

    def to_dict(self):
        return {
            'platform_id': self.platform_id,
            'name': self.name,
            'legal_entities': list(self.legal_entities),
            'naics_codes': list(self.naics_codes),
            'authorized_regions': list(self.authorized_regions),
            'status': self.status,
        }

    def integrity_digest(self):
        """SHA-256 hex of the canonical JSON of to_dict()."""
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def validate_identity(identity):
    """Validate a PlatformIdentity; returns the identity unchanged.

    Raises FoundationDenied on an empty platform_id or name, on any
    NAICS code that is not exactly six digits, and on any authorized
    region that does not match ^[A-Z]{2}(-[A-Z]{2})?$.
    """
    if not isinstance(identity, PlatformIdentity):
        raise FoundationDenied('A PlatformIdentity is required')
    if not isinstance(identity.platform_id, str) \
            or not identity.platform_id.strip():
        raise FoundationDenied('platform_id must be a non-empty string')
    if not isinstance(identity.name, str) or not identity.name.strip():
        raise FoundationDenied('name must be a non-empty string')
    for code in identity.naics_codes:
        if not isinstance(code, str) or not NAICS.fullmatch(code):
            raise FoundationDenied(
                f'NAICS code must be exactly 6 digits: {code!r}')
    for region in identity.authorized_regions:
        if not isinstance(region, str) or not REGION.fullmatch(region):
            raise FoundationDenied(
                f'Invalid authorized region: {region!r}')
    return identity


class GeofencePolicy:
    """Jurisdiction-aware geofencing as a policy gate over declared
    jurisdiction values (not a location proof). Fail-closed:

    * a normalized declared jurisdiction the platform is authorized
      for -> 'ALLOW';
    * a well-formed region the platform is NOT authorized for ->
      'STEP_UP' (verification step-up, never a silent allow);
    * anything else — non-string, empty, malformed -> 'DENY'.

    Pure function over the identity's declared regions: no I/O, no
    audit writes.
    """

    def __init__(self, identity):
        validate_identity(identity)
        self.identity = identity
        self.authorized_regions = frozenset(
            region.upper() for region in identity.authorized_regions)

    def evaluate(self, jurisdiction):
        if not isinstance(jurisdiction, str):
            return 'DENY'
        normalized = jurisdiction.strip().upper()
        if not normalized:
            return 'DENY'
        if normalized in self.authorized_regions:
            return 'ALLOW'
        if REGION.fullmatch(normalized):
            return 'STEP_UP'
        return 'DENY'


class AccessGuard:
    """HIPAA-by-design record-access control for one platform.

    A Glass-Box audit adapter is required at construction: no
    record, no access. A granted access writes its receipt via the
    adapter BEFORE the caller may serve the record, and returns the
    receipt's block hash; if the receipt cannot be written, access
    raises FoundationDenied and the caller must not serve the
    record. A refused access writes no receipt at all.
    """

    def __init__(self, audit, platform_id, role_scopes):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise FoundationDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no access')
        if not isinstance(platform_id, str) or not platform_id.strip():
            raise FoundationDenied('platform_id must be a non-empty string')
        if not role_scopes:
            raise FoundationDenied('role_scopes must not be empty')
        scopes = {}
        for role, categories in role_scopes.items():
            scopes[role] = frozenset(categories)
        self.audit = audit
        self.platform_id = platform_id
        self.role_scopes = scopes

    def authorize(self, role, category):
        """True only when the role's scope includes the category.
        Fail-closed: an unknown role or category is False."""
        categories = self.role_scopes.get(role)
        if categories is None:
            return False
        return category in categories

    def access(self, actor, role, category, record_ref, purpose=''):
        """Authorize one record access and receipt it.

        Returns the Glass-Box block hash of the access receipt.
        Raises FoundationForbidden for a non-string/empty actor or an
        unauthorized role/category (no receipt is written), and
        FoundationDenied when the receipt cannot be preserved (no
        record, no access).
        """
        if not isinstance(actor, str) or not actor.strip():
            raise FoundationForbidden('A non-empty actor is required')
        if not self.authorize(role, category):
            raise FoundationForbidden(
                f'Role {role!r} may not access category {category!r}')
        try:
            return self.audit.preserve(
                'PLATFORM_RECORD_ACCESS',
                platform_id=self.platform_id,
                actor=actor,
                role=role,
                category=category,
                record_ref=record_ref,
                purpose=purpose)
        except Exception as exc:
            raise FoundationDenied(
                'Access receipt could not be preserved: '
                'no record, no access') from exc


def ensure_checkin_schema(db):
    """Create the platform check-ins table on a caller-owned SQLite
    connection. The caller owns the transaction: this never commits.
    """
    db.execute("""CREATE TABLE IF NOT EXISTS platform_check_ins (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_id TEXT NOT NULL,
        recorded_at INTEGER NOT NULL,
        deployment_location TEXT NOT NULL,
        operational_status TEXT NOT NULL,
        identity_digest TEXT NOT NULL,
        integrity_digest TEXT NOT NULL
    );""")


def _checkin_record(row):
    return {
        'seq': row[0],
        'platform_id': row[1],
        'recorded_at': row[2],
        'deployment_location': row[3],
        'operational_status': row[4],
        'identity_digest': row[5],
        'integrity_digest': row[6],
    }


def record_check_in(db, identity, deployment_location, operational_status,
                    clock=time.time):
    """Record one platform check-in on a caller-owned connection.

    Validates the identity, requires a non-empty deployment location
    and operational status, and binds the record to the identity's
    integrity digest. The caller owns the transaction: this inserts
    but never commits, so a caller rollback leaves no check-in.
    Returns the full record dict, including seq.
    """
    validate_identity(identity)
    if not isinstance(deployment_location, str) \
            or not deployment_location.strip():
        raise FoundationDenied(
            'deployment_location must be a non-empty string')
    if not isinstance(operational_status, str) \
            or not operational_status.strip():
        raise FoundationDenied(
            'operational_status must be a non-empty string')
    ensure_checkin_schema(db)
    recorded_at = int(clock())
    identity_digest = identity.integrity_digest()
    integrity_digest = hashlib.sha256(
        f"{identity_digest}|{deployment_location}"
        f"|{operational_status}|{recorded_at}".encode('utf-8')
    ).hexdigest()
    cursor = db.execute(
        "INSERT INTO platform_check_ins (platform_id, recorded_at, "
        "deployment_location, operational_status, identity_digest, "
        "integrity_digest) VALUES (?, ?, ?, ?, ?, ?);",
        (identity.platform_id, recorded_at, deployment_location,
         operational_status, identity_digest, integrity_digest))
    return {
        'seq': cursor.lastrowid,
        'platform_id': identity.platform_id,
        'recorded_at': recorded_at,
        'deployment_location': deployment_location,
        'operational_status': operational_status,
        'identity_digest': identity_digest,
        'integrity_digest': integrity_digest,
    }


def latest_check_in(db, platform_id):
    """The most recent check-in record dict for a platform, or None
    when the platform has never checked in."""
    ensure_checkin_schema(db)
    row = db.execute(
        "SELECT seq, platform_id, recorded_at, deployment_location, "
        "operational_status, identity_digest, integrity_digest "
        "FROM platform_check_ins WHERE platform_id = ? "
        "ORDER BY seq DESC LIMIT 1;", (platform_id,)).fetchone()
    if row is None:
        return None
    return _checkin_record(row)
