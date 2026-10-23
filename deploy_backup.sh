#!/bin/bash
# Online SQLite backup from the owner's existing Compose volume.
set -Eeuo pipefail
exec python3 "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/deploy/ledger_backup.py" "$@"
