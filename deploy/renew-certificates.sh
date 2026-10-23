#!/bin/bash
set -Eeuo pipefail
source /opt/sanders-dash-seal/deploy.sh
[[ "$EUID" == 0 ]] || fail 'Renewal requires root access to Docker.'
exec 9>/run/sanders-certbot-renew.lock
flock -n 9 || exit 0
renew_certificates
