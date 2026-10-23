# Platinum forensic integrity and receipt verification

The owner-requested pipeline is .github/workflows/forensic-audit.yml. It keeps
main/release push, main PR and six-hour scheduled audit events, with an added
manual trigger. It does not merge, deploy, repair files or rotate credentials.
The original submitted workflow/function are preserved under owner-submitted/.
The existing Node/Python service design and selected dependency pin are unchanged.

## Repository audit

The scanner inventories Git-tracked files, including dot-directories such as
.github, computes SHA-256, compares expected PBD artifact/hash pairs, checks
permissions and rejects missing files, symlinks, unexpected exact duplicates and
uncommitted/untracked drift. The owner-approved identical compose.yaml and
docker-compose.yml pair is explicit in security/forensic-policy.json. Untracked
files are drift rather than an approved inventory. Ignored dependencies/build
outputs are outside the tracked inventory; npm audit remains a separate check.

Reports and forensic_manifest.sha256 are written under RUNNER_TEMP outside the
checkout, preventing the proposed generated file_list/drift/manifest files from
triggering their own alert. Detected anomalies fail the job. Evidence is uploaded
with the run for 30 days. The timestamp is the scan time, not repository metadata.
Checkout, artifact upload and the requested v3 mail action use resolved commit
hashes; checkout does not persist credentials and GITHUB_TOKEN is read-only.

SHA-256 digests are checksums, not digital signatures. A successful consistency
scan does not prove the commit was authorized or verify production PBD signatures.
An attacker able to change code, expected manifests, policy and workflow together
can defeat an in-repository baseline. Independent production signers, protected
branches/workflows and externally retained evidence remain separate controls.
No signing identity, branch protection or external immutable store was invented.
This workflow does not scan a running Oracle filesystem or prove absence of all
semantic duplication, vulnerabilities or unauthorized access.

## Conditional SMTP notification

A separate job sends to rooseveltsanders381@gmail.com only after a failed audit
on a non-PR event. It never checks out or executes repository code. PRs retain
failed checks/evidence but do not receive SMTP credentials. Incidents are review
signals, not automatic proof of a breach. Missing SMTP configuration is reported
as notification unavailable; it is never silently reported as delivered.

Required existing repository Actions secrets:

- SDS_SMTP_SERVER
- SDS_SMTP_USERNAME
- SDS_SMTP_PASSWORD (provider-issued app password, not a primary account password)

TLS port 465 and certificate validation are enabled. The From address uses the
authenticated SMTP username rather than asserting ownership of the sample
security@sandersdashseal.app sender. The recipient remains exactly as supplied.
No secret value is committed, printed, requested in chat or used in local tests.
The available GitHub connector cannot inspect/configure Actions secrets, so
presence, sender authorization and actual delivery remain unverified.

The schedule becomes available on the default branch; the workflow is presently
in draft PR #3. Source verification also runs the scanner on the review branch,
without any SMTP job. No test email has been sent. The action schedule is not a
promise of exact six-hour delivery or an independently active monitoring service.
No new paid service or account has been provisioned.

## SQLite signed receipts

core_platform/receipt_verification.py retains the requested
verify_and_log_receipt(db_path, transaction_id, payload_bytes, consumer_signature)
interface and adds an explicitly supplied ReceiptSignatureVerifier. Its public
key must come from independently trusted configuration, never the request body.
Missing verification returns False and creates no VERIFIED ledger entry.

Consumer signatures are base64 Ed25519 signatures over receipt_signing_material:
canonical JSON binding SDS_LEDGER_RECEIPT_V1, transaction_id and the SHA-256 of
the exact payload bytes. The domain separates these receipts from other signing
protocols. A checksum or arbitrary signature string alone is rejected. Only
successful verification permits status VERIFIED in sds_ledger_receipts.

The function creates the receipt schema if needed, makes repeat identical writes
idempotent and rejects conflicting reuse/corrupt stored values. SQLite errors
return False without labeling every database error a security breach or exposing
raw diagnostics to a client. The producer signs; this code never creates a
production private key. Local tests use ephemeral test keys only.

For the existing generic transaction processor, pass connection=sqlite_connection
and verifier=trusted_verifier. The connection must already be in a transaction.
The function neither commits nor closes it; raise TransactionRejected when it
returns False, so business state and signed receipt roll back together. Without
a supplied connection the function owns its SQLite transaction. It is available
in the backend source snapshot but is not silently imposed on all existing
transactions or substituted for jurisdiction/human authority checks. Real
consumer signers and production adapter wiring remain external requirements.

Tests cover clean and altered repositories, committed hash mismatch, permissions,
duplicates, symlinks, report self-noise, forged/replayed signatures, changed
payload/transaction ID, concurrent duplicate writes and rollback integration.
The existing ws 8.16.0 dependency audit remains a separate failed check; this
pipeline does not make its advisories disappear.
