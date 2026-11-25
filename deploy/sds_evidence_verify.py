#!/usr/bin/env python3
"""Read-only evidence-integrity verifier for the watchdog.

Part of the Glass-Box Audit platform (MASTER §19 strengthening
design, Priority 4): between the platform's own verification runs,
the watchdog invokes this verifier on its two-minute cadence to
detect — never repair — a broken, gapped, or diverged evidence
chain. It opens the Glass-Box Audit platform's store, the GlassBox
receipts chain, and the Native Notary Journal chain read-only and
recomputes, independently of the application process and with the
standard library only:

- full hash-chain integrity of both evidence stores, recomputed
  link by link under the substrates' own chain rules (canonical-
  JSON SHA-256 digest plus previous-hash linkage — the rules
  ``GlassBoxAudit.verify_audit()`` and
  ``NativeNotaryJournal.verify_chain()`` enforce);
- sequence contiguity of both chains;
- the prefix property against the platform's last anchor bundle;
- anchor freshness against the design's threshold;
- restore-drill currency against the design's quarterly threshold.

Exit codes: 0 = every check passed (or no evidence stores exist
yet — nothing recorded is nothing broken); 1 = a check failed;
2 = the verifier itself could not run (missing store, unreadable
input). Output is a single line the watchdog logs verbatim. This
script writes nothing: detection and escalation only, exactly the
watchdog's charter — evidence is never repaired by automation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

GENESIS = '0' * 64
ANCHOR_FRESH_SECONDS = 26 * 60 * 60
DRILL_CURRENT_SECONDS = 92 * 24 * 60 * 60


def _canonical_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _chain_state(path, table, seq_col, hash_col):
    """Recompute one chain over a read-only connection. Returns
    (count, head, integrity, gaps, head_at_seq) where integrity is
    OK / EMPTY / BROKEN / UNREADABLE / ABSENT."""
    state = {'count': 0, 'head': GENESIS, 'integrity': 'ABSENT',
             'gaps': [], 'by_seq': {}}
    if not path.exists():
        return state
    try:
        db = sqlite3.connect(f'file:{path}?mode=ro', uri=True,
                             timeout=10)
        try:
            rows = db.execute(
                f'SELECT {seq_col}, body, {hash_col} FROM {table}'
                f' ORDER BY {seq_col} ASC').fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        state['integrity'] = 'UNREADABLE'
        return state
    state['count'] = len(rows)
    if not rows:
        state['integrity'] = 'EMPTY'
        return state
    seqs = [r[0] for r in rows]
    seen = set(seqs)
    state['gaps'] = [s for s in range(seqs[0], seqs[-1] + 1)
                     if s not in seen]
    state['by_seq'] = {r[0]: r[2] for r in rows}
    previous = GENESIS
    integrity = 'OK'
    for _seq, body_text, stored_hash in rows:
        try:
            body = json.loads(body_text)
        except (ValueError, TypeError):
            integrity = 'BROKEN'
            break
        if body.get('previous_hash') != previous:
            integrity = 'BROKEN'
            break
        if _canonical_hash(body) != stored_hash:
            integrity = 'BROKEN'
            break
        previous = stored_hash
    state['integrity'] = integrity
    state['head'] = previous if integrity == 'OK' else rows[-1][2]
    return state


def main(argv):
    if len(argv) != 2:
        print('evidence-verify: usage: sds_evidence_verify.py'
              ' <data-dir>')
        return 2
    data = Path(argv[1])
    store_path = data / 'glass_box_audit.db'
    if not store_path.exists():
        print('evidence-verify: glass-box-audit store missing —'
              ' the platform has not run here')
        return 2
    problems = []
    try:
        gb = _chain_state(data / 'audit.db', 'receipts', 'seq', 'hash')
        jn = _chain_state(data / 'native_notary.db',
                          'native_notarial_journal', 'entry_seq',
                          'entry_hash')
        for name, st in (('glassbox', gb), ('journal', jn)):
            if st['integrity'] == 'BROKEN':
                problems.append(f'{name} chain BROKEN')
            elif st['integrity'] == 'UNREADABLE':
                problems.append(f'{name} store UNREADABLE')
            if st['gaps']:
                problems.append(
                    f"{name} sequence gaps: {st['gaps'][:5]}")
        db = sqlite3.connect(f'file:{store_path}?mode=ro', uri=True,
                             timeout=10)
        try:
            anchor = db.execute(
                'SELECT anchored_at, bundle_json FROM gba_anchors'
                ' ORDER BY anchored_at DESC, anchor_id DESC LIMIT 1',
            ).fetchone()
            drill = db.execute(
                'SELECT drilled_at, outcome FROM gba_drills'
                ' ORDER BY drilled_at DESC, drill_id DESC LIMIT 1',
            ).fetchone()
        finally:
            db.close()
        now = time.time()
        if anchor is None:
            problems.append('no anchor bundle produced yet')
        else:
            bundle = json.loads(anchor[1])
            for name, st in (('glassbox', gb), ('journal', jn)):
                anchored = bundle['chains'][name]
                if st['count'] < anchored['count']:
                    problems.append(
                        f'{name} count regressed below the last'
                        f" anchor ({st['count']} <"
                        f" {anchored['count']})")
                elif anchored['count'] > 0:
                    at = st['by_seq'].get(anchored['highest_seq'])
                    if at != anchored['head']:
                        problems.append(
                            f'{name} anchored prefix diverged at'
                            f" seq {anchored['highest_seq']}")
            age = now - anchor[0]
            if age > ANCHOR_FRESH_SECONDS:
                problems.append(
                    f'last anchor is stale ({int(age)}s > '
                    f'{ANCHOR_FRESH_SECONDS}s)')
        if drill is None:
            problems.append('no restore drill recorded yet')
        else:
            age = now - drill[0]
            if age > DRILL_CURRENT_SECONDS:
                problems.append(
                    f'last restore drill is stale ({int(age)}s > '
                    f'{DRILL_CURRENT_SECONDS}s)')
            elif drill[1] != 'PASSED':
                problems.append(
                    f'last restore drill outcome: {drill[1]}')
    except Exception as exc:  # verifier failure is its own signal
        print(f'evidence-verify: could not run: {exc}')
        return 2
    if problems:
        print('evidence-verify: FAILED — ' + '; '.join(problems))
        return 1
    print('evidence-verify: OK — both chains verify, sequences'
          ' contiguous, anchored prefixes intact, anchor fresh,'
          ' restore drill current')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
