#!/bin/bash
# Read-only host checks. No environment dumps, key reads or service restarts.
set -u
printf 'Architecture: '; uname -m
printf 'OS: '; sed -n 's/^PRETTY_NAME=//p' /etc/os-release
printf 'Execution UID: '; id -u
for binary in python3 docker nginx firewall-cmd; do
    command -v "$binary" || printf '%s: unavailable\n' "$binary"
done
df -h /
if command -v firewall-cmd >/dev/null 2>&1; then
    sudo -n firewall-cmd --state 2>/dev/null || true
    sudo -n firewall-cmd --get-active-zones 2>/dev/null || true
fi
if command -v curl >/dev/null 2>&1; then
    printf 'IMDSv2 HTTP status: '
    curl --noproxy '*' --silent --show-error --connect-timeout 3 --max-time 5 \
        -H 'Authorization: Bearer Oracle' -o /dev/null -w '%{http_code}\n' \
        http://169.254.169.254/opc/v2/instance/ || true
    printf 'OCI Auth HTTPS status (any HTTP response proves TLS reachability): '
    curl --silent --show-error --connect-timeout 3 --max-time 5 \
        -o /dev/null -w '%{http_code}\n' https://auth.us-phoenix-1.oraclecloud.com/ || true
fi
printf 'Inspection complete; this is not an application-readiness verdict.\n'
