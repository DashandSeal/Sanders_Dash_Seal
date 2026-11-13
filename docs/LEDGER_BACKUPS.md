# Private ledger backups on the existing Oracle host

The owner's selected architecture remains Nginx → Node ingestion / authoritative
Python WSGI → SQLite. `deploy_backup.sh` adds Object Storage recovery copies without
restarting any service or moving the transactional database. Source acceptance is
recorded in SPEC_CONFORMANCE.md. This code has not run on the Oracle instance.

## Host and account prerequisites

Create **sds-ledger-backups**, private access, Standard tier, in the home region
Phoenix and root compartment. Leave versioning and auto-tiering disabled. Do not
create public access links or retention rules without reviewing recovery and
capacity needs. Creating a bucket does not establish Instance Principals access.
Install the OCI CLI from its official instructions in a host location on root's
PATH; use a version supporting the checksum options below. This change does not
install a downloaded script as root or alter IAM automatically.

An administrator must verify a dynamic group matching only the actual instance:

```text
instance.id = 'ocid1.instance.oc1.phx.anyhqljrftib4xqcn3nk7tzuyteftz65vngafs5ww72uwuoeihel57urzhha'
```

If the existing group is SandersSyncGroup, bucket-scoped policy examples are:

```text
Allow dynamic-group SandersSyncGroup to read buckets in tenancy where target.bucket.name = 'sds-ledger-backups'
Allow dynamic-group SandersSyncGroup to manage objects in tenancy where all {target.bucket.name = 'sds-ledger-backups', any {request.permission = 'OBJECT_CREATE', request.permission = 'OBJECT_INSPECT', request.permission = 'OBJECT_READ'}}
```

These grant create/list/read for upload and restore testing; not object overwrite
or deletion. Verify the group name/identity domain and effective policies in this
tenancy. Run Command needs separate permissions and is not a prerequisite for
running the backup through SSH/systemd. No API private key is required by this
routine. Network access to OCI authentication and Object Storage must work.

## Consistency and cost limits

The actual database lives in **sqlite_storage:/app/data/sds_production.db** in
`wsgi-backend`. `/opt/sanders-dash-seal/backend/data` is not its host mount. The
routine uses Python's SQLite online backup API inside that container, so committed
WAL transactions are included. It refuses a missing source rather than creating
an empty database. Snapshot duration is bounded; each snapshot is capped at 1 GB
or a smaller configured maximum. Container and host temporary files use private
directories and are removed on normal success/failure. Abrupt machine shutdown
or SIGKILL can leave temporary files; do not put sensitive recovery files in a
public directory.

Each upload gets a UTC timestamp plus random identifier, no overwrite, explicit
Instance Principals authentication, SHA-256 server-side checksum validation and
CLI checksum verification. It is single-part to avoid abandoned multipart storage.
The object is then downloaded, integrity-checked and compared to the local hash.
A failed restore check fails the run and retains the remote object for review.
SHA-256 detects corruption; it is not a signed receipt or independent authorization.
HTTPS transport and OCI encryption at rest do not mean client-side encryption.

Oracle documents 20 GB combined Always Free Object Storage and 50,000 monthly API
requests. Allocate this bucket **only from remaining tenancy-wide free headroom**,
including other buckets/tiers and request usage. Budget is explicit in configuration;
it is not a billing cap. Preflight checks the whole current bucket inventory and
reserves room for the maximum snapshot. With a dedicated bucket and one writer,
the routine stops when allocation is exhausted; it does not delete past backups,
buy capacity, auto-tier or enable paid services. Concurrent writers, other buckets,
request consumption and later account changes require account-level monitoring.
Backups cannot accumulate forever for free. Log a failed scheduled run as an
operational incident and review retention before deleting any recovery history.

## Configure and verify once before scheduling

Use the already approved deployment source on the host, preserving the existing
Compose project **sanders-dash-seal** and its volume. Follow ORACLE_BOOTSTRAP.md's
release-authority requirements. As root create
`/etc/sanders-dash-seal/backup.json` with permissions 0600:

```json
{
  "namespace": "REPLACE_WITH_ACTUAL_OBJECT_STORAGE_NAMESPACE",
  "region": "us-phoenix-1",
  "bucket": "sds-ledger-backups",
  "budget_bytes": 500000000,
  "max_snapshot_bytes": 10000000
}
```

The 500 MB allocation / 10 MB snapshot numbers are examples, not measurements or
a statement that the tenancy has that much free space. Set them from real free
headroom and database size. The namespace is not necessarily the tenancy name.

```bash
cd /opt/sanders-dash-seal
sudo bash deploy_backup.sh --check
sudo bash deploy_backup.sh
```

`--check` makes read-only OCI calls; it does not upload or prove a backup exists.
The second invocation must report `BACKUP_RESTORE_VERIFIED` and exit zero before
enabling the timer. Its output identifies the object, digest and byte size, never
transaction contents. Source/IAM/OCI availability is unverified in this session.

After a successful real run, install the supplied units if bootstrap did not
already copy them, then enable the timer:

```bash
sudo install -m 0644 deploy/systemd/sanders-ledger-backup.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/sanders-ledger-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sanders-ledger-backup.timer
sudo systemctl list-timers sanders-ledger-backup.timer
sudo journalctl -u sanders-ledger-backup.service
```

The timer runs midnight UTC, catches up once after downtime and uses a lock to
prevent overlapping host invocations. Bootstrap does not enable this timer.
Do not also add the proposed cron line: that would schedule duplicate backups.
The timer adds no paid scheduler. Journald holds execution logs; no external email
alert was configured or sent by this extension.

## Recovery drill

Download a chosen object into a protected separate path using Instance Principals;
compare its SHA-256 against an independently retained successful-run record, then
run `PRAGMA integrity_check` on a read-only SQLite connection. The routine already
does this immediately after upload. A full disaster-recovery drill must also start
an isolated application with the recovered database and verify business receipts,
schema and real authority bindings. No automated production database replacement
is included: swapping a live database without draining writers risks lost changes.

## Primary documentation, checked October 21, 2026

- https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/object/put.html
- https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/objectstoragepolicyreference.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
