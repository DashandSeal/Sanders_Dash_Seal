#!/bin/bash
# Sanders Dash & Seal ledger backup wrapper.
#
# The systemd timer (deploy/systemd/sanders-ledger-backup.service) runs
# deploy/bind_free_resources.py --backup, which calls
# /opt/sanders-dash-seal/deploy_backup.sh --database <db>. This file was
# missing, so that path could never execute. This wrapper does nothing
# except forward to the real backup implementation,
# deploy/ledger_backup.py (SQLite snapshot -> private OCI Object Storage
# bucket sds-ledger-backups, restore-verified). No backup destination,
# bucket, or config is invented here: deploy/ledger_backup.py reads
# /etc/sanders-dash-seal/backup.json (0600, created by the owner on the
# host) and refuses to run without it. Usage:
#   sudo bash deploy_backup.sh --check
#   sudo bash deploy_backup.sh [--database sds_production.db|sds_audit.db]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/deploy/ledger_backup.py" "$@"
