"""Portals — the Sanders Companies' community, workforce, and support
intake platform (headquarters scope).

Built 2026-11-25 under the founder's portals directive (the twelve
portals enumerated 2026-11-25 21:27 MST): independent contractors
portal, HR portals, photo gallery, Veterans Wall of Valor, editorial,
how-we're-doing, customer support, complaints, contractor spotlight
of the month and of the year, community guidelines, independent
contractors handbook, emergency contact.

The interactive portals are systems, not pages. This service is
their record:

- **Submissions are cases.** Every public submission — a Wall of
  Valor tribute, a support request, a complaint, a how-we're-doing
  note, a contractor expression of interest, a spotlight nomination —
  is registered as a tracked case with a reference ID and stands
  ``AWAITING_HUMAN_REVIEW``, the same discipline the appointment
  registry keeps (``core_platform/cases.py``). Nothing a member of
  the public submits is ever published by the submission itself.
- **Publication is a human decision.** Only an operator's recorded
  review moves a case: a tribute is APPROVED into PUBLISHED (and
  only then does the public wall carry it, photograph included), a
  support or complaint case is worked and RESOLVED on the record,
  anything may be REJECTED. The deciding identity and the decision
  stand on the case.
- **Spotlights are selections of record.** A spotlight exists only
  when an operator records the selection — contractor, period,
  citation. The public spotlight is exactly the recorded set; until
  the first selection is recorded it is honestly empty.
- **How-we're-doing counts only what the platform holds.** The
  figures are tallies of this registry's own cases and, where the
  shared ledger is wired, of the appointment case registry — each
  figure labelled with its source. Nothing is estimated, projected,
  or invented; a figure with no source is not published.
- **Glass-Box receipts.** Every state-changing operation preserves
  its receipt on the shared audit chain (``GlassBoxAudit``) inside
  the same flow, and the receipt hash stands on the record it made.
  No record, no action: the service refuses to exist without an
  audit adapter.
- **Photographs are held, not trusted.** A tribute photograph is
  carried by content hash under the media directory, validated by
  its own bytes (JPEG / PNG / WebP magic), size-capped, and served
  publicly only while a PUBLISHED tribute references it. Consent is
  a recorded step of the submission itself: no consent, no case.

Fail-closed throughout, in the family pattern: strict field sets,
closed vocabularies, sanitized lengths, and Denied/Forbidden
exceptions the API layer translates into the family's error shapes.
"""

from __future__ import annotations

import base64
import hashlib
import re
import sqlite3
import time
import uuid
from pathlib import Path


class PortalsDenied(Exception):
    """A submission or action the record refuses on its merits."""


class PortalsForbidden(Exception):
    """An action reserved to the operator, attempted by another."""


IDENT_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
REF_RE = re.compile(r'^[A-Z]{3}-[0-9]{8}-[A-Z0-9]{10}$')
MEDIA_RE = re.compile(r'^[a-f0-9]{64}\.(jpg|png|webp)$')

COMPANIES = frozenset((
    'headquarters', 'home_healthcare', 'senior_living',
    'legal_helpers', 's_and_g_security'))

SUBMISSION_KINDS = frozenset((
    'WALL_OF_VALOR', 'SUPPORT', 'COMPLAINT', 'FEEDBACK',
    'CONTRACTOR_INTEREST', 'SPOTLIGHT_NOMINATION',
    'HANDBOOK_ACKNOWLEDGMENT', 'GRANT_SERVICES', 'OIKOS_PROGRAMS'))

REF_PREFIX = {
    'WALL_OF_VALOR': 'WOV',
    'SUPPORT': 'SUP',
    'COMPLAINT': 'CMP',
    'FEEDBACK': 'FBK',
    'CONTRACTOR_INTEREST': 'INT',
    'SPOTLIGHT_NOMINATION': 'NOM',
    'HANDBOOK_ACKNOWLEDGMENT': 'ACK',
    'GRANT_SERVICES': 'GRS',
    'OIKOS_PROGRAMS': 'OIK',
}

# A case is born AWAITING_HUMAN_REVIEW. The operator's review is the
# only road out, and publication is a further, separate state that
# only a Wall of Valor tribute can reach (by approval).
STATUSES = frozenset((
    'AWAITING_HUMAN_REVIEW', 'APPROVED', 'REJECTED',
    'PUBLISHED', 'RESOLVED', 'RECORDED'))

CONSENT_VERSION = 'wall-of-valor-consent-2026-11-25'
HANDBOOK_VERSION = 'contractor-handbook-2026-11-25'

MAX_PHOTO_BYTES = 6 * 1024 * 1024
_PHOTO_MAGIC = (
    (b'\xff\xd8\xff', 'jpg'),
    (b'\x89PNG\r\n\x1a\n', 'png'),
    (b'RIFF', 'webp'),  # + 'WEBP' at offset 8, checked below
)


def _text(value, field, limit, *, required=True, minimum=1):
    if not isinstance(value, str):
        raise PortalsDenied('%s must be text.' % field)
    value = value.strip()
    if required and len(value) < minimum:
        raise PortalsDenied('%s is required.' % field)
    if len(value) > limit:
        raise PortalsDenied('%s is too long.' % field)
    return value


class PortalsService:
    """The portals registry: submissions, review, publication, record."""

    def __init__(self, db_path, media_dir, operator_verifier, audit,
                 ledger_db=None, clock=time.time, approval_hook=None):
        if audit is None:
            raise PortalsDenied('Portals require the Glass-Box audit.')
        if not callable(operator_verifier):
            raise PortalsDenied('Portals require an operator verifier.')
        if approval_hook is not None and not callable(approval_hook):
            raise PortalsDenied('An approval hook must be callable.')
        self.approval_hook = approval_hook
        self.db_path = str(db_path)
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.ledger_db = str(ledger_db) if ledger_db else None
        self.clock = clock
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS portal_submissions (
                ref TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                company TEXT NOT NULL,
                status TEXT NOT NULL,
                submitter_name TEXT NOT NULL,
                submitter_contact TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                honoree TEXT NOT NULL DEFAULT '',
                relationship TEXT NOT NULL DEFAULT '',
                consent INTEGER NOT NULL DEFAULT 0,
                consent_version TEXT NOT NULL DEFAULT '',
                photo_ref TEXT NOT NULL DEFAULT '',
                identity TEXT NOT NULL DEFAULT '',
                receipt_hash TEXT NOT NULL DEFAULT '',
                decided_by TEXT NOT NULL DEFAULT '',
                decision_note TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS portal_spotlights (
                ref TEXT PRIMARY KEY,
                contractor_name TEXT NOT NULL,
                period_type TEXT NOT NULL,
                period_label TEXT NOT NULL,
                citation TEXT NOT NULL,
                company TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                receipt_hash TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL
            );""")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _receipt(self, event, **context):
        return self.audit.preserve(event, **context)

    def _require_operator(self, identity):
        if not isinstance(identity, str) or not IDENT_RE.fullmatch(identity):
            raise PortalsForbidden('Operator sign-in required.')
        try:
            verified = self.operator_verifier(identity) is True
        except Exception:
            verified = False
        if not verified:
            raise PortalsForbidden('Operator authority required.')

    # -- submissions -------------------------------------------------

    def submit(self, kind, company, *, name, contact, subject, body,
               honoree='', relationship='', consent=False,
               consent_version='', photo_b64=None, identity=''):
        """Register a public submission as a case AWAITING_HUMAN_REVIEW.

        Returns the case record, including its reference ID and the
        Glass-Box receipt hash. Publication is never a side effect of
        submission: the case stands in the review queue until an
        operator's recorded decision moves it.
        """
        if kind not in SUBMISSION_KINDS:
            raise PortalsDenied('Unsupported portal submission kind.')
        if company not in COMPANIES:
            raise PortalsDenied('Unknown company.')
        name = _text(name, 'name', 120)
        contact = _text(contact, 'contact', 160)
        subject = _text(subject, 'subject', 200, required=(kind != 'WALL_OF_VALOR'))
        body = _text(body, 'body', 8000)
        honoree = _text(honoree, 'honoree', 160,
                        required=(kind == 'WALL_OF_VALOR'))
        relationship = _text(relationship, 'relationship', 120,
                             required=False)
        if identity and not IDENT_RE.fullmatch(identity):
            raise PortalsDenied('Invalid session identity.')
        photo_ref = ''
        if kind == 'WALL_OF_VALOR':
            if consent is not True or consent_version != CONSENT_VERSION:
                raise PortalsDenied(
                    'A tribute stands only with its recorded consent.')
            if photo_b64 is not None:
                photo_ref = self._store_photo(photo_b64)
        elif photo_b64 is not None:
            raise PortalsDenied('Photographs belong to the Wall of Valor.')
        now = int(self.clock())
        ref = '%s-%s-%s' % (
            REF_PREFIX[kind],
            time.strftime('%Y%m%d', time.gmtime(now)),
            uuid.uuid4().hex[:10].upper())
        receipt = self._receipt(
            'portals.submission_received', ref=ref, kind=kind,
            company=company)
        record = {
            'ref': ref, 'kind': kind, 'company': company,
            'status': 'AWAITING_HUMAN_REVIEW',
            'submitter_name': name, 'submitter_contact': contact,
            'subject': subject, 'body': body, 'honoree': honoree,
            'relationship': relationship,
            'consent': 1 if consent is True else 0,
            'consent_version': consent_version if consent is True else '',
            'photo_ref': photo_ref, 'identity': identity,
            'receipt_hash': receipt, 'decided_by': '',
            'decision_note': '', 'created_at': now, 'updated_at': now,
        }
        with self._connect() as db:
            db.execute(
                """INSERT INTO portal_submissions (
                    ref, kind, company, status, submitter_name,
                    submitter_contact, subject, body, honoree,
                    relationship, consent, consent_version, photo_ref,
                    identity, receipt_hash, decided_by, decision_note,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           '', '', ?, ?);""",
                (ref, kind, company, record['status'], name, contact,
                 subject, body, honoree, relationship, record['consent'],
                 record['consent_version'], photo_ref, identity, receipt,
                 now, now))
        return self._public_case(record)

    def _store_photo(self, photo_b64):
        if not isinstance(photo_b64, str) or not photo_b64:
            raise PortalsDenied('Photograph must be image data.')
        try:
            raw = base64.b64decode(photo_b64, validate=True)
        except Exception as exc:
            raise PortalsDenied('Photograph is not valid image data.') from exc
        if not raw or len(raw) > MAX_PHOTO_BYTES:
            raise PortalsDenied('Photograph exceeds the size the wall accepts.')
        ext = None
        for magic, candidate in _PHOTO_MAGIC:
            if raw.startswith(magic):
                ext = candidate
                break
        if ext == 'webp' and raw[8:12] != b'WEBP':
            ext = None
        if ext is None:
            raise PortalsDenied('Photograph must be a JPEG, PNG, or WebP image.')
        name = '%s.%s' % (hashlib.sha256(raw).hexdigest(), ext)
        target = self.media_dir / name
        if not target.exists():
            target.write_bytes(raw)
        return name

    @staticmethod
    def _public_case(row):
        record = dict(row)
        record['consent'] = bool(record.get('consent'))
        record.pop('submitter_contact', None)
        return record

    def get_case(self, ref):
        if not isinstance(ref, str) or not REF_RE.fullmatch(ref):
            raise PortalsDenied('Invalid reference ID.')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM portal_submissions WHERE ref = ?;',
                (ref,)).fetchone()
        if not row:
            raise PortalsDenied('Unknown reference ID.')
        return dict(row)

    def case_status(self, ref):
        """The public standing of a case, by its reference ID: the
        status and its dates — never another person's record, never
        the review's internals."""
        record = self.get_case(ref)
        return {
            'ref': record['ref'], 'kind': record['kind'],
            'company': record['company'], 'status': record['status'],
            'created_at': record['created_at'],
            'updated_at': record['updated_at'],
        }

    # -- operator review ----------------------------------------------

    def review_queue(self, identity):
        self._require_operator(identity)
        with self._connect() as db:
            rows = db.execute(
                """SELECT * FROM portal_submissions
                   WHERE status = 'AWAITING_HUMAN_REVIEW'
                   ORDER BY created_at ASC;""").fetchall()
        return [dict(row) for row in rows]

    def review(self, identity, ref, decision, note=''):
        """The operator's recorded decision on a queued case.

        APPROVE publishes a Wall of Valor tribute (PUBLISHED) and
        acknowledges any other case (APPROVED). REJECT closes the
        case as REJECTED. Nothing else moves a case out of the queue.
        """
        self._require_operator(identity)
        if decision not in ('APPROVE', 'REJECT'):
            raise PortalsDenied('A review decision is APPROVE or REJECT.')
        note = _text(note, 'note', 500, required=False)
        record = self.get_case(ref)
        if record['status'] != 'AWAITING_HUMAN_REVIEW':
            raise PortalsDenied('Case is not awaiting review.')
        if decision == 'APPROVE':
            new_status = ('PUBLISHED' if record['kind'] == 'WALL_OF_VALOR'
                          else 'APPROVED')
        else:
            new_status = 'REJECTED'
        now = int(self.clock())
        receipt = self._receipt(
            'portals.review_decision', ref=ref, decision=decision,
            new_status=new_status, decided_by=identity)
        with self._connect() as db:
            db.execute(
                """UPDATE portal_submissions
                   SET status = ?, decided_by = ?, decision_note = ?,
                       receipt_hash = ?, updated_at = ?
                   WHERE ref = ?;""",
                (new_status, identity, note, receipt, now, ref))
        result = self.case_status(ref) | {
            'decision': decision, 'receipt_hash': receipt}
        if decision == 'APPROVE' and self.approval_hook is not None:
            # The decision stands on its own record. The hook opens
            # whatever the approval engages downstream (a service
            # intake, for a commercial kind); its outcome is carried
            # on this result and receipted either way — never
            # silent, and never able to un-decide the review.
            try:
                opened = self.approval_hook(identity, self.get_case(ref))
            except Exception as exc:
                self._receipt(
                    'portals.approval_hook_failed', ref=ref,
                    decided_by=identity, error=str(exc))
                result['intake_error'] = str(exc)
            else:
                if isinstance(opened, dict):
                    result['intake'] = opened
        return result

    def resolve(self, identity, ref, note=''):
        """Close a worked support or complaint case as RESOLVED, on
        the record."""
        self._require_operator(identity)
        note = _text(note, 'note', 500, required=False)
        record = self.get_case(ref)
        if record['kind'] not in ('SUPPORT', 'COMPLAINT'):
            raise PortalsDenied('Only support and complaint cases resolve.')
        if record['status'] not in ('AWAITING_HUMAN_REVIEW', 'APPROVED'):
            raise PortalsDenied('Case cannot be resolved from its status.')
        now = int(self.clock())
        receipt = self._receipt(
            'portals.case_resolved', ref=ref, decided_by=identity)
        with self._connect() as db:
            db.execute(
                """UPDATE portal_submissions
                   SET status = 'RESOLVED', decided_by = ?,
                       decision_note = ?, receipt_hash = ?, updated_at = ?
                   WHERE ref = ?;""",
                (identity, note, receipt, now, ref))
        return self.case_status(ref) | {'receipt_hash': receipt}

    # -- spotlights -----------------------------------------------------

    def record_spotlight(self, identity, *, contractor_name, period_type,
                         period_label, citation, company):
        """Record a spotlight selection. A selection exists only as
        this record; there is no other road onto the public wall."""
        self._require_operator(identity)
        contractor_name = _text(contractor_name, 'contractor_name', 120)
        period_label = _text(period_label, 'period_label', 60)
        citation = _text(citation, 'citation', 2000)
        if period_type not in ('MONTH', 'YEAR'):
            raise PortalsDenied('A spotlight period is MONTH or YEAR.')
        if company not in COMPANIES:
            raise PortalsDenied('Unknown company.')
        now = int(self.clock())
        ref = 'SPT-%s-%s' % (
            time.strftime('%Y%m%d', time.gmtime(now)),
            uuid.uuid4().hex[:10].upper())
        receipt = self._receipt(
            'portals.spotlight_recorded', ref=ref,
            period_type=period_type, period_label=period_label,
            company=company, recorded_by=identity)
        with self._connect() as db:
            db.execute(
                """INSERT INTO portal_spotlights (
                    ref, contractor_name, period_type, period_label,
                    citation, company, recorded_by, receipt_hash,
                    created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (ref, contractor_name, period_type, period_label,
                 citation, company, identity, receipt, now))
        return {
            'ref': ref, 'contractor_name': contractor_name,
            'period_type': period_type, 'period_label': period_label,
            'citation': citation, 'company': company,
            'recorded_by': identity, 'receipt_hash': receipt,
            'created_at': now,
        }

    def spotlights(self):
        with self._connect() as db:
            rows = db.execute(
                """SELECT ref, contractor_name, period_type, period_label,
                          citation, company, created_at
                   FROM portal_spotlights ORDER BY created_at DESC;"""
                ).fetchall()
        return [dict(row) for row in rows]

    # -- public wall ----------------------------------------------------

    def wall(self):
        """The public Wall of Valor: PUBLISHED tributes only. A case
        the operator has not approved is not here, in any field."""
        with self._connect() as db:
            rows = db.execute(
                """SELECT ref, honoree, relationship, body, photo_ref,
                          created_at, updated_at
                   FROM portal_submissions
                   WHERE kind = 'WALL_OF_VALOR' AND status = 'PUBLISHED'
                   ORDER BY updated_at DESC;""").fetchall()
        wall = []
        for row in rows:
            entry = dict(row)
            entry['story'] = entry.pop('body')
            entry['photo_url'] = (
                '/api/portals/media/' + entry['photo_ref']
                if entry['photo_ref'] else None)
            wall.append(entry)
        return wall

    def media_path(self, name):
        """Serve a tribute photograph only while a PUBLISHED tribute
        references it. Held photographs are never public."""
        if not isinstance(name, str) or not MEDIA_RE.fullmatch(name):
            raise PortalsDenied('Unknown photograph.')
        with self._connect() as db:
            row = db.execute(
                """SELECT photo_ref FROM portal_submissions
                   WHERE kind = 'WALL_OF_VALOR' AND status = 'PUBLISHED'
                     AND photo_ref = ?;""", (name,)).fetchone()
        if not row:
            raise PortalsDenied('Photograph is not on the public wall.')
        target = self.media_dir / name
        if not target.is_file():
            raise PortalsDenied('Photograph is not held.')
        return target

    # -- contractor surface ----------------------------------------------

    def contractor_home(self, identity):
        """A signed-in contractor's own record: their cases (interest,
        handbook acknowledgment, nominations they made) and the
        handbook standing. Another identity's records are never here."""
        if not isinstance(identity, str) or not IDENT_RE.fullmatch(identity):
            raise PortalsForbidden('Sign-in required.')
        with self._connect() as db:
            rows = db.execute(
                """SELECT ref, kind, company, status, subject,
                          created_at, updated_at
                   FROM portal_submissions WHERE identity = ?
                   ORDER BY created_at DESC;""", (identity,)).fetchall()
        records = [dict(row) for row in rows]
        handbook = [r for r in records
                    if r['kind'] == 'HANDBOOK_ACKNOWLEDGMENT'
                    and r['status'] == 'RECORDED']
        return {
            'identity': identity,
            'records': records,
            'handbook_version': HANDBOOK_VERSION,
            'handbook_acknowledged': bool(handbook),
        }

    def acknowledge_handbook(self, identity):
        """Record a contractor's acknowledgment of the handbook of
        record, with its Glass-Box receipt."""
        if not isinstance(identity, str) or not IDENT_RE.fullmatch(identity):
            raise PortalsForbidden('Sign-in required.')
        record = self.submit(
            'HANDBOOK_ACKNOWLEDGMENT', 'headquarters',
            name=identity, contact='platform sign-in',
            subject='Independent Contractors Handbook acknowledgment',
            body='Handbook version %s acknowledged by the signed-in '
                 'contractor.' % HANDBOOK_VERSION,
            identity=identity)
        with self._connect() as db:
            db.execute(
                """UPDATE portal_submissions SET status = 'RECORDED'
                   WHERE ref = ?;""", (record['ref'],))
        return self.case_status(record['ref'])

    # -- how-we're-doing ---------------------------------------------------

    def metrics(self):
        """Figures the platform can source from its own records, each
        labelled with its source. Nothing estimated; nothing with no
        source."""
        figures = []
        with self._connect() as db:
            rows = db.execute(
                """SELECT kind, status, COUNT(*) AS n
                   FROM portal_submissions GROUP BY kind, status;"""
                ).fetchall()
            spotlights = db.execute(
                'SELECT COUNT(*) AS n FROM portal_spotlights;'
                ).fetchone()['n']
        tallies = {}
        for row in rows:
            tallies.setdefault(row['kind'], {})[row['status']] = row['n']

        def total(kind):
            return sum(tallies.get(kind, {}).values())

        figures.append({
            'label': 'Portal cases received',
            'value': sum(total(k) for k in tallies),
            'source': 'The portals registry — every submission since '
                      'the portals opened is a tracked case.'})
        figures.append({
            'label': 'Cases awaiting human review',
            'value': sum(v.get('AWAITING_HUMAN_REVIEW', 0)
                         for v in tallies.values()),
            'source': 'The portals registry review queue.'})
        figures.append({
            'label': 'Support and complaint cases resolved',
            'value': sum(tallies.get(k, {}).get('RESOLVED', 0)
                         for k in ('SUPPORT', 'COMPLAINT')),
            'source': 'The portals registry — resolutions recorded by '
                      'the reviewing operator.'})
        figures.append({
            'label': 'Wall of Valor tributes published',
            'value': tallies.get('WALL_OF_VALOR', {}).get('PUBLISHED', 0),
            'source': 'The portals registry — tributes an operator '
                      'approved onto the public wall.'})
        figures.append({
            'label': 'Contractor spotlights recorded',
            'value': spotlights,
            'source': 'The portals registry — selections recorded by '
                      'the operator; there are no others.'})
        if self.ledger_db:
            try:
                ledger = sqlite3.connect(
                    'file:%s?mode=ro' % self.ledger_db, uri=True, timeout=5)
                try:
                    rows = ledger.execute(
                        'SELECT status, COUNT(*) FROM cases GROUP BY status;'
                        ).fetchall()
                finally:
                    ledger.close()
                by_status = dict(rows)
                figures.append({
                    'label': 'Appointment cases received',
                    'value': sum(by_status.values()),
                    'source': 'The Sanders Dash & Seal case registry.'})
                figures.append({
                    'label': 'Appointment cases awaiting human review',
                    'value': by_status.get('AWAITING_HUMAN_REVIEW', 0),
                    'source': 'The Sanders Dash & Seal case registry.'})
            except sqlite3.Error:
                pass
        return {'figures': figures, 'tallies': tallies}

    def status(self):
        with self._connect() as db:
            queued = db.execute(
                """SELECT COUNT(*) AS n FROM portal_submissions
                   WHERE status = 'AWAITING_HUMAN_REVIEW';"""
                ).fetchone()['n']
            published = db.execute(
                """SELECT COUNT(*) AS n FROM portal_submissions
                   WHERE status = 'PUBLISHED';""").fetchone()['n']
        return {
            'service': 'portals',
            'review_queue': queued,
            'wall_published': published,
            'consent_version': CONSENT_VERSION,
            'handbook_version': HANDBOOK_VERSION,
        }
