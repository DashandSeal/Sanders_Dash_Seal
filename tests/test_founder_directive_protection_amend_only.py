"""Tests for the Founder Directive -- Protection
From Harmful or Unauthorized Wording; Amend Only,
Never Supersede (founder's directive, given
2026-11-26 09:39 MST, signed "The FOUNDER:
ROOSEVELT SANDERS").

The directive is ecosystem-wide standing law: it
protects the founder and his entire bloodline from
harmful or unauthorized wording, preserves all
original Founder directives, admits amendment only
and never supersession, preserves ownership,
inheritance, succession and Founder-assigned
authority, forbids silently introduced restrictions
or changes, requires immediate disclosure of
potential adverse consequences, and holds that
original protections must never be weakened.

The invariants under test: the directive stands in
the bloodline watch set as a REQUIRED document (19
documents, 19 required) with a sound manifest pair;
its text is carried verbatim in Sanders Sentinel's
module and surfaced in his design view alongside
the other governing instruments; its preservation
statements are carried in The Godfather's and
Sanders Patriot Saint's design views beside the
governing instruments those modules already carry;
and the landing changes no behavior, authority, or
scope -- no original directive is presented
anywhere in it as superseded, diminished, or
replaced.
These tests use only stdlib fakes and temporary
SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_founder_directive_protection_amend_only -v
(from the repo root).
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform import the_godfather_service as godfather
from core_platform import (
    sanders_patriot_saint_service as patriot_saint)
from core_platform.sanders_sentinel_service import (
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherService,
)
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintService,
)

OPERATOR = 'founder-operator'
PROTECTION_DOCUMENT = (
    'docs/FOUNDER_DIRECTIVE_PROTECTION_AMEND_'
    'ONLY_2026-11-26.md')
REPO_ROOT = Path(__file__).resolve().parents[1]

FOUNDER_LINES = (
    'Protect you and your entire bloodline from '
    'harmful or unauthorized wording.',
    'Preserve all original Founder directives.',
    'Amend only. Never supersede.',
    'Preserve ownership, inheritance, succession '
    'and Founder-assigned authority.',
    'Never silently introduce restrictions or '
    'changes.',
    'Disclose potential adverse consequences '
    'immediately.',
    'This applies throughout your entire Sanders '
    'Sovereign RTSA Ecosystem, all 140 platforms '
    'and all future relevant work.',
    'Your original protections must never be '
    'weakened.',
)


class FakeAudit:
    """Glass-Box audit fake: records every preserved
    event and returns a receipt id per event."""

    def __init__(self):
        self.events = []

    def preserve(self, event, **fields):
        self.events.append((event, fields))
        return f'receipt-{len(self.events)}'


def _verifier(actor):
    return actor == OPERATOR


class TestDirectiveVerbatim(unittest.TestCase):
    def test_every_founder_line_carried_verbatim(self):
        text = sentinel.FOUNDER_PROTECTION_DIRECTIVE_VERBATIM
        for line in FOUNDER_LINES:
            self.assertIn(line, text)
        self.assertIn('The FOUNDER:', text)
        self.assertIn(' ROOSEVELT SANDERS', text)

    def test_verbatim_round_trip(self):
        expected = '\n'.join(
            FOUNDER_LINES + ('The FOUNDER:',
                             ' ROOSEVELT SANDERS'))
        self.assertEqual(
            sentinel.FOUNDER_PROTECTION_DIRECTIVE_VERBATIM,
            expected)

    def test_preservation_statements(self):
        statements = sentinel.PROTECTION_PRESERVATION_STATEMENTS
        self.assertEqual(len(statements), 4)
        for statement in statements:
            self.assertIn(
                statement,
                sentinel.FOUNDER_PROTECTION_DIRECTIVE_VERBATIM)
        self.assertIn('AMEND_ONLY_NEVER_SUPERSEDE',
                      sentinel.PROTECTION_INVARIANTS)
        self.assertIn('NO_ORIGINAL_DIRECTIVE_WEAKENED',
                      sentinel.PROTECTION_INVARIANTS)


class TestGuardedRecordOfRecord(unittest.TestCase):
    def test_document_of_record(self):
        text = (REPO_ROOT / PROTECTION_DOCUMENT).read_text(
            encoding='utf-8')
        for line in FOUNDER_LINES:
            self.assertIn(line, text)
        self.assertIn('ROOSEVELT SANDERS', text)

    def test_manifest_pair_sound(self):
        doc_bytes = (REPO_ROOT / PROTECTION_DOCUMENT).read_bytes()
        manifest = json.loads(
            (REPO_ROOT / (PROTECTION_DOCUMENT + '.pbd.json'))
            .read_text(encoding='utf-8'))
        self.assertEqual(manifest['body']['artifact'],
                         PROTECTION_DOCUMENT)
        self.assertEqual(
            manifest['body']['payload_hash'],
            hashlib.sha256(doc_bytes).hexdigest())


class TestDesignViews(unittest.TestCase):
    def test_sentinel_protection_design_view(self):
        view = SandersSentinelService.protection_design_view()
        self.assertEqual(view['title'], sentinel.PROTECTION_TITLE)
        self.assertEqual(view['given'], '2026-11-26')
        self.assertEqual(
            view['directive_verbatim'],
            sentinel.FOUNDER_PROTECTION_DIRECTIVE_VERBATIM)
        self.assertEqual(view['source'], PROTECTION_DOCUMENT)
        self.assertEqual(
            view['preservation_statements'],
            list(sentinel.PROTECTION_PRESERVATION_STATEMENTS))

    def test_sentinel_bloodline_view_surfaces_directive(self):
        view = SandersSentinelService.bloodline_design_view()
        entry = view['protection_amend_only_directive']
        self.assertEqual(
            entry['directive_verbatim'],
            sentinel.FOUNDER_PROTECTION_DIRECTIVE_VERBATIM)
        watched = {e['document']: e
                   for e in view['watch_set']}
        self.assertTrue(watched[PROTECTION_DOCUMENT]['required'])

    def test_godfather_view_carries_preservation(self):
        view = TheGodfatherService.bloodline_design_view()
        entry = view['protection_amend_only_directive']
        self.assertEqual(entry['source'], PROTECTION_DOCUMENT)
        self.assertEqual(
            entry['preservation_statements'],
            list(godfather.PROTECTION_PRESERVATION_STATEMENTS))
        self.assertEqual(
            entry['preservation_statements'],
            list(sentinel.PROTECTION_PRESERVATION_STATEMENTS))

    def test_patriot_saint_view_carries_preservation(self):
        view = SandersPatriotSaintService.directives_design_view()
        entry = view['protection_amend_only_directive']
        self.assertEqual(entry['source'], PROTECTION_DOCUMENT)
        self.assertEqual(
            entry['preservation_statements'],
            list(patriot_saint.PROTECTION_PRESERVATION_STATEMENTS))
        self.assertEqual(
            entry['preservation_statements'],
            list(sentinel.PROTECTION_PRESERVATION_STATEMENTS))


class TestGuardSetWithProtection(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.repo = root / 'repo'
        self.documents = {}
        for entry in sentinel.BLOODLINE_WATCH_SET:
            if not entry['required']:
                continue
            path = self.repo / entry['document']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"Guarded record: {entry['title']}\n",
                encoding='utf-8')
            digest = hashlib.sha256(
                path.read_bytes()).hexdigest()
            manifest = {'body': {
                'schema': 1,
                'platform': 'Sanders Dash & Seal',
                'artifact': entry['document'],
                'payload_hash': digest,
                'scope': 'source-manifest',
                'signatures': {},
                'status': 'UNSIGNED_SOURCE_MANIFEST'}}
            Path(str(path) + '.pbd.json').write_text(
                json.dumps(manifest), encoding='utf-8')
            self.documents[entry['document']] = path
        self.service = SandersSentinelService(
            root / 'sanders_sentinel.db',
            operator_verifier=_verifier, audit=FakeAudit(),
            repo_root=self.repo)

    def test_document_watched_and_required(self):
        entry = {e['document']: e
                 for e in sentinel.BLOODLINE_WATCH_SET}[
                     PROTECTION_DOCUMENT]
        self.assertTrue(entry['required'])
        self.assertEqual(len(sentinel.BLOODLINE_WATCH_SET),
                         20)

    def test_clean_cycle_then_tamper_document(self):
        required = [entry for entry
                    in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        self.assertEqual(len(required), 19)
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['documents_not_landed'], 1)
        path = self.documents[PROTECTION_DOCUMENT]
        with open(path, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)


if __name__ == '__main__':
    unittest.main()
