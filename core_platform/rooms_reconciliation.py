"""
Module: core_platform.rooms_reconciliation
Architectural Layer: Commercial Meeting Rooms — Glass-Box Evidence
Reconciliation (read-only)
Description: Cross-checks the Glass-Box audit chain's room receipts
against the committed rooms store and reports where the two records
diverge: receipts whose referenced room, invitation, consent or
transition has no committed counterpart (attempted-but-uncommitted
actions — the orphan class named as Phase B residual #1), and
committed state that lacks its expected receipt.

This routine is READ-ONLY by construction and by rule. Both stores
are opened with SQLite ``mode=ro`` connections, so the reconciler
cannot write even by accident; and per the Glass Box strengthening
program's hard boundary, reconciliation SURFACES discrepancies — it
never repairs them. A receipt that lacks a committed counterpart is
evidence of an attempt, preserved as such; deleting it or inventing
the missing state would destroy exactly the evidence the chain
exists to keep. Every discrepancy is reported with the specific
receipt identifiers (chain sequence and block hash) so an operator
can investigate; nothing is silently reconciled away.
"""

import json
import sqlite3
from collections import Counter

from .security import digest

_ROOM_STAGE_PREFIX = 'ROOM_'
_INVITE_TERMINAL_STAGES = {
    'ACCEPTED': 'ROOM_INVITE_ACCEPTED',
    'EXPIRED': 'ROOM_INVITE_EXPIRED',
    'REVOKED': 'ROOM_INVITE_REVOKED',
    'SUPERSEDED': 'ROOM_INVITE_SUPERSEDED',
}


def _connect_ro(path):
    """A strictly read-only connection: SQLite refuses writes and
    will not create a missing file."""
    return sqlite3.connect('file:%s?mode=ro' % path, uri=True)


def _audit_path(audit):
    """Accept an audit database path or a GlassBoxAudit instance."""
    return str(getattr(audit, 'path', audit))


class RoomEvidenceReconciler:
    """Read-only reconciliation of room receipts vs committed state.

    ``rooms_database`` is the rooms store path; ``audit_database``
    is the Glass-Box audit store path (or a GlassBoxAudit instance,
    whose ``path`` is used). Neither store is ever written to.
    """

    def __init__(self, rooms_database, audit_database):
        self.rooms_database = str(rooms_database)
        self.audit_database = _audit_path(audit_database)

    # -- loading (read-only) ----------------------------------------

    def _load_receipts(self):
        receipts = []
        chain_valid = True
        previous = '0' * 64
        with _connect_ro(self.audit_database) as db:
            rows = db.execute(
                "SELECT seq, body, hash FROM receipts "
                "ORDER BY seq ASC;").fetchall()
        for seq, raw_body, stored_hash in rows:
            body = json.loads(raw_body)
            if body.get('previous_hash') != previous:
                chain_valid = False
            encoded = json.dumps(body, sort_keys=True,
                                 separators=(',', ':'),
                                 ensure_ascii=False)
            if digest(encoded.encode('utf-8')) != stored_hash:
                chain_valid = False
            previous = stored_hash
            event = body.get('event')
            if not isinstance(event, dict):
                continue
            stage = event.get('stage')
            if not isinstance(stage, str) \
                    or not stage.startswith(_ROOM_STAGE_PREFIX):
                continue
            receipts.append({'seq': seq, 'hash': stored_hash,
                             'stage': stage, 'event': event})
        return receipts, chain_valid

    def _load_committed(self):
        with _connect_ro(self.rooms_database) as db:
            db.row_factory = sqlite3.Row
            rooms = {row['room_id']: dict(row) for row in db.execute(
                "SELECT room_id, state, recording_state, host "
                "FROM rooms;").fetchall()}
            participants = {(row['room_id'], row['identity'])
                            for row in db.execute(
                                "SELECT room_id, identity "
                                "FROM room_participants;").fetchall()}
            invites = {row['invite_id']: dict(row) for row in
                       db.execute(
                           "SELECT invite_id, room_id, invitee, status "
                           "FROM room_invites;").fetchall()}
            consents = Counter(
                (row['room_id'], row['identity'], row['decision'],
                 row['notice_version']) for row in db.execute(
                     "SELECT room_id, identity, decision, "
                     "notice_version FROM room_consents;").fetchall())
        return rooms, participants, invites, consents

    # -- reconciliation ----------------------------------------------

    def reconcile(self):
        """Cross-check receipts against committed state. Returns a
        structured report; performs no writes and no repairs."""
        receipts, chain_valid = self._load_receipts()
        rooms, participants, invites, consents = self._load_committed()
        orphaned = []
        missing = []
        divergences = []

        def orphan(receipt, reason):
            orphaned.append({
                'seq': receipt['seq'], 'hash': receipt['hash'],
                'stage': receipt['stage'],
                'room_id': receipt['event'].get('room_id'),
                'reason': reason})

        by_room = {}
        for receipt in receipts:
            by_room.setdefault(
                receipt['event'].get('room_id'), []).append(receipt)

        # Creations: a ROOM_CREATED receipt for a room that was never
        # committed is the residual-#1 orphan in its purest form; a
        # committed room with no creation receipt is missing evidence.
        created_ids = set()
        for receipt in receipts:
            if receipt['stage'] != 'ROOM_CREATED':
                continue
            room_id = receipt['event'].get('room_id')
            created_ids.add(room_id)
            if room_id not in rooms:
                orphan(receipt, 'creation receipt has no committed room')
        for room_id in rooms:
            if room_id not in created_ids:
                missing.append({
                    'room_id': room_id, 'expected_stage': 'ROOM_CREATED',
                    'detail': 'committed room has no creation receipt'})

        # Any other receipt naming a room that does not exist in the
        # committed store is an orphan of the same class.
        for receipt in receipts:
            room_id = receipt['event'].get('room_id')
            if receipt['stage'] == 'ROOM_CREATED':
                continue
            if room_id not in rooms:
                orphan(receipt,
                       'receipt references a room with no committed '
                       'counterpart')

        # Transitions: replay each committed room's transition
        # receipts from DRAFT. Receipts after the last point where
        # the replayed state equals the committed state have no
        # committed counterpart; a from_state that breaks the replay
        # chain is a divergence.
        for room_id, room in rooms.items():
            transitions = [r for r in by_room.get(room_id, [])
                           if r['stage'] == 'ROOM_TRANSITION']
            if not transitions:
                if room['state'] != 'DRAFT':
                    divergences.append({
                        'room_id': room_id, 'kind': 'state_divergence',
                        'detail': 'committed state %s with no '
                                  'transition receipts' % room['state']})
                continue
            running = 'DRAFT'
            states_after = []
            for receipt in transitions:
                event = receipt['event']
                if event.get('from_state') != running:
                    divergences.append({
                        'room_id': room_id, 'kind': 'state_divergence',
                        'seq': receipt['seq'],
                        'detail': 'transition from_state %s does not '
                                  'continue replayed state %s'
                                  % (event.get('from_state'), running)})
                running = event.get('to_state')
                states_after.append(running)
            committed = room['state']
            last_match = -1
            if committed == 'DRAFT':
                last_match = -1
            for index, state in enumerate(states_after):
                if state == committed:
                    last_match = index
            if states_after[-1] != committed:
                for receipt in transitions[last_match + 1:]:
                    orphan(receipt,
                           'transition receipt has no committed '
                           'counterpart (committed state is %s)'
                           % committed)

        # Recording state: the last recording receipt and the
        # committed recording_state must agree.
        for room_id, room in rooms.items():
            recording = [r for r in by_room.get(room_id, [])
                         if r['stage'] in ('ROOM_RECORDING_AUTHORIZED',
                                           'ROOM_RECORDING_REVOKED')]
            if room['recording_state'] == 'AUTHORIZED':
                if not recording or recording[-1]['stage'] \
                        != 'ROOM_RECORDING_AUTHORIZED':
                    missing.append({
                        'room_id': room_id,
                        'expected_stage': 'ROOM_RECORDING_AUTHORIZED',
                        'detail': 'recording is AUTHORIZED in committed '
                                  'state without a standing '
                                  'authorization receipt'})
            elif recording and recording[-1]['stage'] \
                    == 'ROOM_RECORDING_AUTHORIZED':
                orphan(recording[-1],
                       'authorization receipt has no committed '
                       'counterpart (committed recording_state is %s)'
                       % room['recording_state'])

        # Participants: an add receipt for a participant row that was
        # never committed is an orphan.
        for receipt in receipts:
            if receipt['stage'] != 'ROOM_PARTICIPANT_ADDED':
                continue
            key = (receipt['event'].get('room_id'),
                   receipt['event'].get('identity'))
            if key not in participants:
                orphan(receipt,
                       'participant receipt has no committed '
                       'participant row')

        # Invitations: receipts name the invite_id exactly, so both
        # directions are checked exactly.
        invite_receipt_stages = {}
        for receipt in receipts:
            invite_id = receipt['event'].get('invite_id')
            if invite_id is None:
                continue
            invite_receipt_stages.setdefault(invite_id, set()).add(
                receipt['stage'])
            if receipt['stage'].startswith('ROOM_INVITE_') \
                    and invite_id not in invites:
                orphan(receipt,
                       'invitation receipt has no committed invitation')
        for invite_id, invite in invites.items():
            stages = invite_receipt_stages.get(invite_id, set())
            if 'ROOM_INVITE_ISSUED' not in stages:
                missing.append({
                    'room_id': invite['room_id'],
                    'expected_stage': 'ROOM_INVITE_ISSUED',
                    'invite_id': invite_id,
                    'detail': 'committed invitation has no issuance '
                              'receipt'})
            expected = _INVITE_TERMINAL_STAGES.get(invite['status'])
            if expected is not None and expected not in stages:
                missing.append({
                    'room_id': invite['room_id'],
                    'expected_stage': expected,
                    'invite_id': invite_id,
                    'detail': 'committed invitation status %s has no '
                              'matching receipt' % invite['status']})

        # Consent: receipts and rows are matched as multisets on
        # (room, identity, decision, notice_version), paired in chain
        # order; receipts beyond the committed count are orphans, a
        # committed surplus is missing evidence.
        consent_receipts = {}
        for receipt in receipts:
            if receipt['stage'] != 'ROOM_CONSENT_RECORDED':
                continue
            event = receipt['event']
            key = (event.get('room_id'), event.get('identity'),
                   event.get('decision'), event.get('notice_version'))
            consent_receipts.setdefault(key, []).append(receipt)
        for key, group in consent_receipts.items():
            surplus = len(group) - consents.get(key, 0)
            if surplus > 0:
                for receipt in group[len(group) - surplus:]:
                    orphan(receipt,
                           'consent receipt has no committed consent '
                           'row')
        for key, count in consents.items():
            deficit = count - len(consent_receipts.get(key, []))
            if deficit > 0:
                missing.append({
                    'room_id': key[0],
                    'expected_stage': 'ROOM_CONSENT_RECORDED',
                    'detail': '%d committed consent row(s) for %s '
                              '(%s, %s) lack receipts'
                              % (deficit, key[1], key[2], key[3])})

        orphaned.sort(key=lambda entry: entry['seq'])
        report = {
            'chain_valid': chain_valid,
            'rooms_examined': len(rooms),
            'receipts_examined': len(receipts),
            'orphaned_receipts': orphaned,
            'missing_receipts': missing,
            'divergences': divergences,
            'counts': {
                'orphaned_receipts': len(orphaned),
                'missing_receipts': len(missing),
                'divergences': len(divergences),
            },
        }
        report['ok'] = bool(chain_valid and not orphaned
                            and not missing and not divergences)
        return report


def reconcile_room_evidence(rooms_database, audit_database):
    """One-call form: reconcile and return the structured report."""
    return RoomEvidenceReconciler(rooms_database, audit_database).reconcile()
