"""RTSA Minotaur — production build-out (RTSA Build Program Q9).

The recovered ``minotaur_sentinel.py`` at the repository root is the
foundation and is left untouched: ``MinotaurSentinel`` pins SHA-256
baselines over ``PROTECTED_TARGETS`` at construction and
``execute_patrol_cycle`` reports each target that is MISSING or whose
hash no longer matches its baseline. Its baselines live in process
memory — pinned from whatever the working directory held at import,
gone at exit — anomalies are returned as bare strings with no
lifecycle, and nothing is queryable after the fact.

This module is the production build-out the queue's Q9 completion
definition requires: the recovered patrol's semantics as durable,
receipted state on the shared RTSA foundation
(:mod:`core_platform.rtsa_foundation`) — operator-pinned durable
baselines over a workspace root (in place of the construction-time
in-memory pins), recorded patrol cycles, an anomaly lifecycle
(DETECTED, ACKNOWLEDGED, ESCALATED, CLEARED), and clearance
determinations for the Twin-Gate section 8 step 2: a subject is
SAFE_TO_EXECUTE only when every protected target is pinned, the
latest patrol cycle is clean, and no anomaly is open — otherwise the
determination is DENIED with the blocker named, per MASTER
section 10 (no token, no bypass).

MASTER section 5 and AGENTS.md are explicit: RTSA Minotaur and the
Sanders Labyrinth Shield are separate systems and are never merged.
The Minotaur patrols the integrity of the house's own files —
including, as one protected target among five, the Shield's
foundation file — it does not evaluate arriving traffic, and this
module contains no Shield code.

Like every platform on the foundation, the service refuses to exist
without a working Glass-Box audit adapter: no record, no action.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

from minotaur_sentinel import PROTECTED_TARGETS, MinotaurSentinel

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
    platform_id='minotaur_sentinel',
    name='RTSA Minotaur',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

TARGETS = tuple(PROTECTED_TARGETS)
ANOMALY_KINDS = ('MISSING', 'ALTERED')
ANOMALY_STATUSES = ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED', 'CLEARED')
# The anomaly lifecycle: which transitions each action may take.
ANOMALY_TRANSITIONS = {
    'acknowledge': {'DETECTED': 'ACKNOWLEDGED'},
    'escalate': {'DETECTED': 'ESCALATED', 'ACKNOWLEDGED': 'ESCALATED'},
    'clear': {'DETECTED': 'CLEARED', 'ACKNOWLEDGED': 'CLEARED',
              'ESCALATED': 'CLEARED'},
}


class MinotaurDenied(Exception):
    """The requested Minotaur operation is not allowed."""


class MinotaurForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class MinotaurService:
    """Durable, receipted Minotaur patrol over the protected targets."""

    def __init__(self, database_path, workspace_root, operator_verifier,
                 audit, *, sentinel=None, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise MinotaurDenied(
                'RTSA Minotaur requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._root = Path(workspace_root)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._sentinel = sentinel if sentinel is not None else MinotaurSentinel()
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'minotaur_sentinel', {
            'OPERATOR': {'PATROL'},
            'AUDITOR': {'PATROL'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS minotaur_baselines (
                    target TEXT PRIMARY KEY,
                    pinned_hash TEXT NOT NULL,
                    pinned_by TEXT NOT NULL,
                    pinned_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_patrols (
                    patrol_id TEXT PRIMARY KEY,
                    patrolled_at REAL NOT NULL,
                    patrolled_by TEXT NOT NULL,
                    targets_checked INTEGER NOT NULL,
                    unpinned INTEGER NOT NULL,
                    anomalies_found INTEGER NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_anomalies (
                    anomaly_id TEXT PRIMARY KEY,
                    patrol_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS minotaur_anomalies_open_idx
                    ON minotaur_anomalies (target, kind, status);
                CREATE TABLE IF NOT EXISTS minotaur_clearances (
                    clearance_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    determination TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    patrol_id TEXT,
                    open_anomalies INTEGER NOT NULL,
                    issued_by TEXT NOT NULL,
                    issued_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                """
            )

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
            raise MinotaurForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise MinotaurForbidden(
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
            raise MinotaurForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'PATROL', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise MinotaurForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise MinotaurDenied(str(exc)) from exc

    def _current_hash(self, target: str) -> str:
        # The recovered sentinel's own hash engine, over the target
        # resolved against this service's workspace root.
        return self._sentinel.compute_target_hash(
            str(self._root / target))

    @staticmethod
    def _anomaly_view(row):
        return {
            'anomaly_id': row['anomaly_id'],
            'patrol_id': row['patrol_id'],
            'target': row['target'],
            'kind': row['kind'],
            'status': row['status'],
            'detected_at': row['detected_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    @staticmethod
    def _clearance_view(row):
        return {
            'clearance_id': row['clearance_id'],
            'subject': row['subject'],
            'determination': row['determination'],
            'reason': row['reason'],
            'patrol_id': row['patrol_id'],
            'open_anomalies': row['open_anomalies'],
            'issued_by': row['issued_by'],
            'issued_at': row['issued_at'],
            'receipt_id': row['receipt_id'],
        }

    # -- baselines ----------------------------------------------------

    def targets(self, actor, role, *, region=None):
        """Every protected target with its pin and live state."""
        self._geo(region)
        self._guard_access(actor, role, 'targets', 'targets view')
        with self._connect() as db:
            pins = {
                row['target']: row
                for row in db.execute('SELECT * FROM minotaur_baselines')
            }
        result = []
        for target in TARGETS:
            current = self._current_hash(target)
            pin = pins.get(target)
            if pin is None:
                state = 'UNPINNED'
                pinned_hash = None
            else:
                pinned_hash = pin['pinned_hash']
                if current == 'FILE_MISSING':
                    state = 'MISSING'
                elif current == pinned_hash:
                    state = 'MATCH'
                else:
                    state = 'MISMATCH'
            result.append({
                'target': target,
                'state': state,
                'pinned_hash': pinned_hash,
                'current_hash': current,
            })
        return result

    def pin_baseline(self, actor, target, *, region=None):
        """Pin one target's current hash as its baseline (operator)."""
        self._geo(region)
        self._require_operator(actor)
        if target not in TARGETS:
            raise MinotaurDenied(f'Not a protected target: {target!r}')
        current = self._current_hash(target)
        if current == 'FILE_MISSING':
            raise MinotaurDenied(
                f'Cannot pin a missing target: {target}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_BASELINE_PINNED', actor=actor, target=target,
                    pinned_hash=current)
                db.execute(
                    'INSERT INTO minotaur_baselines (target, pinned_hash,'
                    ' pinned_by, pinned_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?)'
                    ' ON CONFLICT(target) DO UPDATE SET'
                    ' pinned_hash = excluded.pinned_hash,'
                    ' pinned_by = excluded.pinned_by,'
                    ' pinned_at = excluded.pinned_at,'
                    ' receipt_id = excluded.receipt_id',
                    (target, current, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'target': target, 'pinned_hash': current,
                'pinned_by': actor, 'pinned_at': now}

    def pin_all_baselines(self, actor, *, region=None):
        """Pin every present protected target (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        pinned = []
        for target in TARGETS:
            if self._current_hash(target) != 'FILE_MISSING':
                pinned.append(self.pin_baseline(actor, target,
                                                region=region))
        return pinned

    # -- patrol ---------------------------------------------------------

    def patrol(self, actor, *, region=None):
        """Run one patrol cycle over the durable baselines (operator).

        The recovered cycle's semantics: a pinned target that is
        missing or whose hash differs from its pin is an anomaly.
        An unpinned target is reported as unpinned, never silently
        treated as patrolled. An anomaly already open for the same
        target and kind is carried, not duplicated.
        """
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        patrol_id = f'mn-patrol-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            pins = {
                row['target']: row['pinned_hash']
                for row in db.execute('SELECT * FROM minotaur_baselines')
            }
        findings = []
        unpinned = 0
        for target in TARGETS:
            pin = pins.get(target)
            if pin is None:
                unpinned += 1
                continue
            current = self._current_hash(target)
            if current == 'FILE_MISSING':
                findings.append((target, 'MISSING'))
            elif current != pin:
                findings.append((target, 'ALTERED'))
        anomalies = []
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_PATROL', actor=actor, patrol_id=patrol_id,
                    targets_checked=len(TARGETS) - unpinned,
                    anomalies_found=len(findings))
                db.execute(
                    'INSERT INTO minotaur_patrols (patrol_id, patrolled_at,'
                    ' patrolled_by, targets_checked, unpinned,'
                    ' anomalies_found, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (patrol_id, now, actor, len(TARGETS) - unpinned,
                     unpinned, len(findings), receipt_id),
                )
                for target, kind in findings:
                    open_row = db.execute(
                        "SELECT * FROM minotaur_anomalies"
                        " WHERE target = ? AND kind = ? AND status IN"
                        " ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED')"
                        ' ORDER BY detected_at LIMIT 1',
                        (target, kind),
                    ).fetchone()
                    if open_row is not None:
                        view = self._anomaly_view(open_row)
                        view['carried'] = True
                        anomalies.append(view)
                        continue
                    anomaly_id = f'mn-anom-{uuid.uuid4().hex[:16]}'
                    a_receipt = self._record(
                        'MINOTAUR_ANOMALY', actor=actor,
                        anomaly_id=anomaly_id, patrol_id=patrol_id,
                        target=target, kind=kind)
                    db.execute(
                        'INSERT INTO minotaur_anomalies (anomaly_id,'
                        ' patrol_id, target, kind, status, detected_at,'
                        ' updated_by, updated_at, receipt_id)'
                        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (anomaly_id, patrol_id, target, kind, 'DETECTED',
                         now, actor, now, a_receipt),
                    )
                    row = db.execute(
                        'SELECT * FROM minotaur_anomalies'
                        ' WHERE anomaly_id = ?',
                        (anomaly_id,),
                    ).fetchone()
                    view = self._anomaly_view(row)
                    view['carried'] = False
                    anomalies.append(view)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'patrol_id': patrol_id,
            'patrolled_at': now,
            'targets_checked': len(TARGETS) - unpinned,
            'unpinned': unpinned,
            'anomalies_found': len(findings),
            'anomalies': anomalies,
        }

    def anomalies_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'anomalies', 'anomalies view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_anomalies ORDER BY detected_at',
            ).fetchall()
        return [self._anomaly_view(row) for row in rows]

    def anomaly_view(self, actor, role, anomaly_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, anomaly_id, 'anomaly view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                (anomaly_id,),
            ).fetchone()
        if row is None:
            raise MinotaurDenied('Anomaly not found')
        return self._anomaly_view(row)

    def anomaly_action(self, actor, anomaly_id, action, *, region=None):
        """Advance one anomaly's lifecycle (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ANOMALY_TRANSITIONS.get(action)
        if transitions is None:
            raise MinotaurDenied(f'Unknown anomaly action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                    (anomaly_id,),
                ).fetchone()
                if row is None:
                    raise MinotaurDenied('Anomaly not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise MinotaurDenied(
                        f"Cannot {action} an anomaly in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'MINOTAUR_ANOMALY_ACTION', actor=actor,
                    anomaly_id=anomaly_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE minotaur_anomalies SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE anomaly_id = ?',
                    (new_status, actor, now, receipt_id, anomaly_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                (anomaly_id,),
            ).fetchone()
        return self._anomaly_view(updated)

    # -- clearances -------------------------------------------------------

    def clearance_issue(self, actor, subject, *, region=None):
        """Issue a clearance determination for one subject (operator).

        SAFE_TO_EXECUTE only when every protected target is pinned,
        the latest patrol cycle is clean, and no anomaly is open;
        otherwise DENIED with the blocker named. The determination is
        recorded either way — a denial is a record, not an absence.
        The returned clearance_id is the reference the Twin-Gate
        section 8 chain records at its step 2.
        """
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(subject, str) or not subject.strip():
            raise MinotaurDenied('A clearance subject is required')
        subject = subject.strip()
        now = self._now()
        with self._connect() as db:
            pinned = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_baselines',
            ).fetchone()['n']
            latest = db.execute(
                'SELECT * FROM minotaur_patrols'
                ' ORDER BY patrolled_at DESC, patrol_id DESC LIMIT 1',
            ).fetchone()
            open_anomalies = db.execute(
                "SELECT COUNT(*) AS n FROM minotaur_anomalies"
                " WHERE status IN ('DETECTED', 'ACKNOWLEDGED',"
                " 'ESCALATED')",
            ).fetchone()['n']
        if pinned < len(TARGETS):
            determination, reason = 'DENIED', 'unpinned_targets'
            patrol_id = latest['patrol_id'] if latest else None
        elif latest is None:
            determination, reason = 'DENIED', 'no_patrol_on_record'
            patrol_id = None
        elif open_anomalies > 0:
            determination, reason = 'DENIED', 'open_anomalies'
            patrol_id = latest['patrol_id']
        elif latest['anomalies_found'] > 0:
            determination, reason = 'DENIED', 'latest_patrol_found_anomalies'
            patrol_id = latest['patrol_id']
        else:
            determination, reason = 'SAFE_TO_EXECUTE', 'patrol_clean'
            patrol_id = latest['patrol_id']
        clearance_id = f'mn-clear-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_CLEARANCE', actor=actor,
                    clearance_id=clearance_id, subject=subject,
                    determination=determination, reason=reason)
                db.execute(
                    'INSERT INTO minotaur_clearances (clearance_id,'
                    ' subject, determination, reason, patrol_id,'
                    ' open_anomalies, issued_by, issued_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (clearance_id, subject, determination, reason,
                     patrol_id, open_anomalies, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM minotaur_clearances WHERE clearance_id = ?',
                (clearance_id,),
            ).fetchone()
        return self._clearance_view(row)

    def clearance_view(self, actor, role, clearance_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, clearance_id, 'clearance view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM minotaur_clearances WHERE clearance_id = ?',
                (clearance_id,),
            ).fetchone()
        if row is None:
            raise MinotaurDenied('Clearance not found')
        return self._clearance_view(row)

    # -- status / check-in --------------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            pinned = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_baselines',
            ).fetchone()['n']
            patrols = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_patrols',
            ).fetchone()['n']
            last_patrol = db.execute(
                'SELECT patrol_id, patrolled_at, anomalies_found'
                ' FROM minotaur_patrols'
                ' ORDER BY patrolled_at DESC, patrol_id DESC LIMIT 1',
            ).fetchone()
            by_status = {s: 0 for s in ANOMALY_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM minotaur_anomalies'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            clearances = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_clearances',
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'sentinel_id': self._sentinel.sentinel_id,
            'targets_total': len(TARGETS),
            'baselines_pinned': pinned,
            'patrols_total': patrols,
            'last_patrol': dict(last_patrol) if last_patrol else None,
            'anomalies_by_status': by_status,
            'clearances_issued': clearances,
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
                    raise MinotaurDenied(str(exc)) from exc
                self._record('MINOTAUR_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
