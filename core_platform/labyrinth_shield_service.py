"""Sanders Labyrinth Shield — production build-out (RTSA Build Program Q8).

The recovered ``labyrinth_shield.py`` at the repository root is the
foundation and is left untouched: ``LabyrinthShield.evaluate_packet``
runs the edge blocklist check and the structural scan (a payload
carrying a malicious indicator is rejected and its source is added
to the blocklist by the shield itself), and
``LabyrinthShield.compute_shield_hash`` self-audits the foundation
file's SHA-256. It is stateless — the blocklist lives in process
memory, evaluations leave no record, and nothing is queryable after
the fact.

This module is the production build-out the queue's Q8 completion
definition requires: the recovered shield's evaluations as durable,
receipted state on the shared RTSA foundation
(:mod:`core_platform.rtsa_foundation`) — a persistent evaluation
ledger that stores the SHA-256 of each evaluated payload and never
the payload itself, a durable operator blocklist kept in step with
the recovered instance, rate limiting per source, isolation of a
source after repeated malicious rejections, and a self-integrity pin
over the recovered foundation file, so a changed foundation is
detected rather than silently trusted.

MASTER section 5 and AGENTS.md are explicit: the Labyrinth Shield
and RTSA Minotaur are separate systems and are never merged. The
Minotaur patrols; the Shield evaluates what arrives at the edge.
This module contains no patrol logic and no Minotaur code.

Like every platform on the foundation, the service refuses to exist
without a working Glass-Box audit adapter: no record, no action.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
import uuid
from pathlib import Path

from labyrinth_shield import LabyrinthShield

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    validate_identity,
)
from .rtsa_foundation import (
    latest_check_in as _foundation_latest_check_in,
)
from .rtsa_foundation import (
    record_check_in as _foundation_record_check_in,
)


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='sanders_labyrinth_shield',
    name='Sanders Labyrinth Shield 🛡️',
    legal_entities=('Sanders Legal Helpers LLC',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The recovered foundation file this service wraps. The integrity pin
# is taken over exactly this file, resolved from this module's own
# location (repository root), never from a caller-supplied path.
FOUNDATION_FILE = Path(__file__).resolve().parent.parent / 'labyrinth_shield.py'

DECISIONS = ('allowed', 'rejected', 'blocked', 'isolated')


class LabyrinthShieldDenied(Exception):
    """The requested Labyrinth Shield operation is not allowed."""


class LabyrinthShieldForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class LabyrinthShieldService:
    """Durable, receipted Labyrinth Shield evaluations and perimeter state."""

    def __init__(self, database_path, operator_verifier, audit, *,
                 shield=None, rate_limit=30, rate_window_seconds=60.0,
                 isolation_threshold=3, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise LabyrinthShieldDenied(
                'Sanders Labyrinth Shield requires a working Glass-Box'
                ' audit adapter')
        if rate_limit < 1 or isolation_threshold < 1:
            raise LabyrinthShieldDenied('Invalid rate or isolation limits')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._shield = shield if shield is not None else LabyrinthShield()
        self._rate_limit = int(rate_limit)
        self._rate_window = float(rate_window_seconds)
        self._isolation_threshold = int(isolation_threshold)
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_labyrinth_shield', {
            'OPERATOR': {'EVALUATION', 'BLOCKLIST', 'ISOLATION', 'INTEGRITY'},
            'VERIFIER': {'EVALUATION'},
            'AUDITOR': {'EVALUATION', 'BLOCKLIST', 'ISOLATION', 'INTEGRITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS labyrinth_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    evaluated_at REAL NOT NULL,
                    source TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    shield_hash TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS labyrinth_evaluations_source_idx
                    ON labyrinth_evaluations (source, evaluated_at);
                CREATE TABLE IF NOT EXISTS labyrinth_blocklist (
                    blocklist_id TEXT PRIMARY KEY,
                    entry TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at REAL NOT NULL,
                    removed_by TEXT,
                    removed_at REAL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS labyrinth_blocklist_entry_idx
                    ON labyrinth_blocklist (entry, status);
                CREATE TABLE IF NOT EXISTS labyrinth_isolations (
                    isolation_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    isolated_at REAL NOT NULL,
                    released_by TEXT,
                    released_at REAL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS labyrinth_isolations_source_idx
                    ON labyrinth_isolations (source, status);
                CREATE TABLE IF NOT EXISTS labyrinth_integrity (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    pinned_file_hash TEXT NOT NULL,
                    pinned_by TEXT NOT NULL,
                    pinned_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                """
            )
            # The durable blocklist is the record; the recovered
            # instance is kept in step with it, so a restart loses
            # nothing.
            for row in db.execute(
                "SELECT entry FROM labyrinth_blocklist"
                " WHERE status = 'ACTIVE'"
            ):
                self._shield.blocklist.add(row['entry'])

    # -- plumbing ---------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self._path, timeout=10,
                             isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def _now(self) -> float:
        return float(self._clock())

    def _check_actor(self, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise LabyrinthShieldForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise LabyrinthShieldForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        # The geofence binds a declared jurisdiction. Surfaces that
        # declare none (the session-bound HTTP family declares no
        # jurisdiction field) pass None; wherever a jurisdiction IS
        # declared, the foundation policy decides, fail-closed.
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise LabyrinthShieldForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, category, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, category, record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise LabyrinthShieldForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise LabyrinthShieldDenied(str(exc)) from exc

    @staticmethod
    def _evaluation_view(row):
        return {
            'evaluation_id': row['evaluation_id'],
            'evaluated_at': row['evaluated_at'],
            'source': row['source'],
            'payload_sha256': row['payload_sha256'],
            'decision': row['decision'],
            'reason': row['reason'],
            'shield_hash': row['shield_hash'],
            'receipt_id': row['receipt_id'],
        }

    @staticmethod
    def _blocklist_view(row):
        return {
            'blocklist_id': row['blocklist_id'],
            'entry': row['entry'],
            'status': row['status'],
            'reason': row['reason'],
            'added_by': row['added_by'],
            'added_at': row['added_at'],
            'removed_by': row['removed_by'],
            'removed_at': row['removed_at'],
            'receipt_id': row['receipt_id'],
        }

    @staticmethod
    def _isolation_view(row):
        return {
            'isolation_id': row['isolation_id'],
            'source': row['source'],
            'status': row['status'],
            'reason': row['reason'],
            'isolated_at': row['isolated_at'],
            'released_by': row['released_by'],
            'released_at': row['released_at'],
            'receipt_id': row['receipt_id'],
        }

    # -- evaluation ---------------------------------------------------

    def evaluate(self, actor, role, source, payload, *, region=None):
        """Evaluate one payload through the recovered shield, receipted.

        The payload itself is never stored — only its SHA-256. An
        isolated source is refused at the edge and recorded as such
        without reaching the shield. A source rejected as malicious
        ``isolation_threshold`` times is isolated in the same
        transaction as the evaluation that crosses the threshold.
        """
        self._geo(region)
        self._guard_access(actor, role, 'EVALUATION', source or '',
                           'shield evaluation')
        if not isinstance(source, str) or not source.strip():
            raise LabyrinthShieldDenied('An evaluation source is required')
        if not isinstance(payload, str):
            raise LabyrinthShieldDenied('The payload must be text')
        source = source.strip()
        now = self._now()
        payload_sha256 = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        evaluation_id = f'ls-eval-{uuid.uuid4().hex[:16]}'
        isolation_created = None
        auto_block_id = None
        with self._connect() as db:
            recent = db.execute(
                'SELECT COUNT(*) AS n FROM labyrinth_evaluations'
                ' WHERE source = ? AND evaluated_at >= ?',
                (source, now - self._rate_window),
            ).fetchone()['n']
            isolated = db.execute(
                "SELECT isolation_id FROM labyrinth_isolations"
                " WHERE source = ? AND status = 'ISOLATED'"
                ' ORDER BY isolated_at DESC LIMIT 1',
                (source,),
            ).fetchone()
        if recent >= self._rate_limit:
            raise LabyrinthShieldDenied(
                'Rate limit exceeded: source is over its evaluation'
                ' allowance for the current window')
        if isolated is not None:
            decision, reason = 'isolated', 'source_isolated'
        elif source in self._shield.blocklist:
            decision, reason = 'blocked', 'source_blocked'
        elif self._shield.evaluate_packet(source, payload):
            decision, reason = 'allowed', 'structural_scan_passed'
        else:
            # The recovered shield has already added this source to
            # its own blocklist (its standing response to a malicious
            # indicator); the durable layer mirrors that act below so
            # a restart preserves it.
            decision, reason = 'rejected', 'structural_scan_rejected'
        try:
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE;')
                try:
                    receipt_id = self._record(
                        'LABYRINTH_EVALUATION', actor=actor,
                        evaluation_id=evaluation_id, source=source,
                        payload_sha256=payload_sha256, decision=decision,
                        reason=reason)
                    db.execute(
                        'INSERT INTO labyrinth_evaluations (evaluation_id,'
                        ' evaluated_at, source, payload_sha256, decision,'
                        ' reason, shield_hash, receipt_id)'
                        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (evaluation_id, now, source, payload_sha256,
                         decision, reason, self._shield.compute_shield_hash(),
                         receipt_id),
                    )
                    if decision == 'rejected':
                        auto_block_id = f'ls-block-{uuid.uuid4().hex[:16]}'
                        auto_receipt = self._record(
                            'LABYRINTH_BLOCKLIST_AUTO', actor='system',
                            blocklist_id=auto_block_id, entry=source)
                        db.execute(
                            'INSERT INTO labyrinth_blocklist (blocklist_id,'
                            ' entry, status, reason, added_by, added_at,'
                            ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (auto_block_id, source, 'ACTIVE',
                             'structural_scan_auto_block', 'system', now,
                             auto_receipt),
                        )
                    if decision in ('rejected', 'blocked'):
                        # Hostile arrivals since the source's most
                        # recent isolation: a release restarts the
                        # count, so one stray arrival while still
                        # blocklisted does not silently re-isolate.
                        since = db.execute(
                            'SELECT COALESCE(MAX(isolated_at), 0) AS t'
                            ' FROM labyrinth_isolations WHERE source = ?',
                            (source,),
                        ).fetchone()['t']
                        hostile = db.execute(
                            "SELECT COUNT(*) AS n FROM labyrinth_evaluations"
                            " WHERE source = ? AND decision IN"
                            " ('rejected', 'blocked')"
                            ' AND evaluated_at > ?',
                            (source, since),
                        ).fetchone()['n']
                        if hostile >= self._isolation_threshold:
                            isolation_id = f'ls-iso-{uuid.uuid4().hex[:16]}'
                            iso_receipt = self._record(
                                'LABYRINTH_ISOLATION', actor=actor,
                                isolation_id=isolation_id, source=source,
                                hostile_evaluations=hostile)
                            db.execute(
                                'INSERT INTO labyrinth_isolations'
                                ' (isolation_id, source, status, reason,'
                                ' isolated_at, receipt_id)'
                                ' VALUES (?, ?, ?, ?, ?, ?)',
                                (isolation_id, source, 'ISOLATED',
                                 'repeated_hostile_evaluations', now,
                                 iso_receipt),
                            )
                            isolation_created = isolation_id
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
                row = db.execute(
                    'SELECT * FROM labyrinth_evaluations'
                    ' WHERE evaluation_id = ?',
                    (evaluation_id,),
                ).fetchone()
        except Exception:
            if decision == 'rejected':
                # The commit failed, so the durable layer never took
                # the shield's auto-block: undo it in memory too.
                self._shield.blocklist.discard(source)
            raise
        result = self._evaluation_view(row)
        result['isolation_created'] = isolation_created
        result['auto_blocked'] = auto_block_id is not None
        return result

    def evaluation_view(self, actor, role, evaluation_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'EVALUATION', evaluation_id,
                           'evaluation view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM labyrinth_evaluations'
                ' WHERE evaluation_id = ?',
                (evaluation_id,),
            ).fetchone()
        if row is None:
            raise LabyrinthShieldDenied('Evaluation not found')
        return self._evaluation_view(row)

    # -- blocklist ------------------------------------------------------

    def blocklist_add(self, actor, entry, reason, *, region=None):
        """Add one entry to the durable blocklist (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(entry, str) or not entry.strip() \
                or len(entry.strip()) > 253:
            raise LabyrinthShieldDenied('A valid blocklist entry is required')
        entry = entry.strip()
        blocklist_id = f'ls-block-{uuid.uuid4().hex[:16]}'
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                existing = db.execute(
                    "SELECT blocklist_id FROM labyrinth_blocklist"
                    " WHERE entry = ? AND status = 'ACTIVE'",
                    (entry,),
                ).fetchone()
                if existing is not None:
                    raise LabyrinthShieldDenied(
                        'Blocklist entry is already active')
                receipt_id = self._record(
                    'LABYRINTH_BLOCKLIST_ADD', actor=actor,
                    blocklist_id=blocklist_id, entry=entry)
                db.execute(
                    'INSERT INTO labyrinth_blocklist (blocklist_id, entry,'
                    ' status, reason, added_by, added_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (blocklist_id, entry, 'ACTIVE', str(reason or ''),
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM labyrinth_blocklist WHERE blocklist_id = ?',
                (blocklist_id,),
            ).fetchone()
        self._shield.blocklist.add(entry)
        return self._blocklist_view(row)

    def blocklist_remove(self, actor, entry, *, region=None):
        """Remove one active entry from the blocklist (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        entry = entry.strip() if isinstance(entry, str) else ''
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    "SELECT * FROM labyrinth_blocklist"
                    " WHERE entry = ? AND status = 'ACTIVE'",
                    (entry,),
                ).fetchone()
                if row is None:
                    raise LabyrinthShieldDenied(
                        'Blocklist entry is not active')
                receipt_id = self._record(
                    'LABYRINTH_BLOCKLIST_REMOVE', actor=actor,
                    blocklist_id=row['blocklist_id'], entry=row['entry'])
                db.execute(
                    "UPDATE labyrinth_blocklist SET status = 'REMOVED',"
                    ' removed_by = ?, removed_at = ?, receipt_id = ?'
                    ' WHERE blocklist_id = ?',
                    (actor, now, receipt_id, row['blocklist_id']),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM labyrinth_blocklist WHERE blocklist_id = ?',
                (row['blocklist_id'],),
            ).fetchone()
        self._shield.blocklist.discard(entry)
        return self._blocklist_view(updated)

    def blocklist_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'BLOCKLIST', 'blocklist',
                           'blocklist view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM labyrinth_blocklist ORDER BY added_at, entry',
            ).fetchall()
        return [self._blocklist_view(row) for row in rows]

    # -- isolation --------------------------------------------------------

    def isolations_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'ISOLATION', 'isolations',
                           'isolation view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM labyrinth_isolations ORDER BY isolated_at',
            ).fetchall()
        return [self._isolation_view(row) for row in rows]

    def isolation_release(self, actor, isolation_id, *, region=None):
        """Release one active isolation (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM labyrinth_isolations'
                    ' WHERE isolation_id = ?',
                    (isolation_id,),
                ).fetchone()
                if row is None:
                    raise LabyrinthShieldDenied('Isolation not found')
                if row['status'] != 'ISOLATED':
                    raise LabyrinthShieldDenied('Isolation is not active')
                receipt_id = self._record(
                    'LABYRINTH_ISOLATION_RELEASE', actor=actor,
                    isolation_id=isolation_id, source=row['source'])
                db.execute(
                    "UPDATE labyrinth_isolations SET status = 'RELEASED',"
                    ' released_by = ?, released_at = ?, receipt_id = ?'
                    ' WHERE isolation_id = ?',
                    (actor, now, receipt_id, isolation_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM labyrinth_isolations WHERE isolation_id = ?',
                (isolation_id,),
            ).fetchone()
        return self._isolation_view(updated)

    # -- self-integrity ---------------------------------------------------

    def _current_file_hash(self) -> str:
        # The recovered foundation's own self-audit: SHA-256 of the
        # foundation file's bytes, exactly as the shield computes it.
        return self._shield.compute_shield_hash()

    def integrity_status(self, actor, role, *, region=None):
        """Compare the recovered foundation file against its pin."""
        self._geo(region)
        self._guard_access(actor, role, 'INTEGRITY', 'integrity',
                           'integrity view')
        current = self._current_file_hash()
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM labyrinth_integrity WHERE id = 1',
            ).fetchone()
        if row is None:
            state, pinned = 'UNPINNED', None
        else:
            pinned = row['pinned_file_hash']
            state = 'MATCH' if pinned == current else 'MISMATCH'
        return {
            'foundation_file': FOUNDATION_FILE.name,
            'state': state,
            'pinned_file_hash': pinned,
            'current_file_hash': current,
            'shield_id': self._shield.shield_id,
        }

    def integrity_pin(self, actor, *, region=None):
        """Pin the current foundation file hash (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        current = self._current_file_hash()
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_INTEGRITY_PIN', actor=actor,
                    foundation_file=FOUNDATION_FILE.name,
                    pinned_file_hash=current)
                db.execute(
                    'INSERT INTO labyrinth_integrity (id, pinned_file_hash,'
                    ' pinned_by, pinned_at, receipt_id)'
                    ' VALUES (1, ?, ?, ?, ?)'
                    ' ON CONFLICT(id) DO UPDATE SET'
                    ' pinned_file_hash = excluded.pinned_file_hash,'
                    ' pinned_by = excluded.pinned_by,'
                    ' pinned_at = excluded.pinned_at,'
                    ' receipt_id = excluded.receipt_id',
                    (current, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.integrity_status(actor, 'OPERATOR', region=region)

    # -- status / check-in --------------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            decisions = {d: 0 for d in DECISIONS}
            for row in db.execute(
                    'SELECT decision, COUNT(*) AS n'
                    ' FROM labyrinth_evaluations GROUP BY decision'):
                decisions[row['decision']] = row['n']
            blocklist_active = db.execute(
                "SELECT COUNT(*) AS n FROM labyrinth_blocklist"
                " WHERE status = 'ACTIVE'",
            ).fetchone()['n']
            isolations_active = db.execute(
                "SELECT COUNT(*) AS n FROM labyrinth_isolations"
                " WHERE status = 'ISOLATED'",
            ).fetchone()['n']
            pin = db.execute(
                'SELECT pinned_file_hash FROM labyrinth_integrity'
                ' WHERE id = 1',
            ).fetchone()
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        if pin is None:
            integrity_state = 'UNPINNED'
        else:
            integrity_state = (
                'MATCH'
                if pin['pinned_file_hash'] == self._current_file_hash()
                else 'MISMATCH')
        return {
            'identity': IDENTITY.to_dict(),
            'evaluations_total': sum(decisions.values()),
            'evaluations_by_decision': decisions,
            'blocklist_active': blocklist_active,
            'isolations_active': isolations_active,
            'integrity_state': integrity_state,
            'rate_limit': self._rate_limit,
            'rate_window_seconds': self._rate_window,
            'isolation_threshold': self._isolation_threshold,
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise LabyrinthShieldDenied(str(exc)) from exc
                self._record('LABYRINTH_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
