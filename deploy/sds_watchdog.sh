#!/usr/bin/env bash
# sds_watchdog.sh — automatic recovery for the Sanders Dash & Seal platform
# services on the Oracle instance.
#
# Owner direction (2026-11-23): "set up a way for everything to
# automatically reconnect if the connection is interrupted for any
# reason." This script is the health-check half of that: it runs as root
# every 2 minutes from sds-watchdog.timer, probes every platform service
# on its loopback health endpoint, and restarts a service that has
# stopped answering. The other half is in the units themselves
# (Restart=always with StartLimitIntervalSec=0, so systemd never gives
# up on a crashed service) and in loginctl linger for the opc user
# manager, so the --user services come back after a reboot.
#
# Installed by deploy/deploy_all.sh (step 5c) to
# /usr/local/sbin/sds_watchdog.sh; the repo copy is
# deploy/sds_watchdog.sh. It is deliberately conservative:
#
#   * A service is DOWN only after 2 consecutive failed checks (the
#     timer runs every 2 minutes, so a restart is considered only after
#     roughly 2–4 minutes of continuous failure). A single transient
#     failure is logged, never acted on.
#   * At most one restart per service per 5 minutes (cooldown stamps in
#     the state directory). A service with a hard configuration error —
#     e.g. a missing secret in /etc/sanders-dash-seal/runtime.env —
#     cannot be fixed by restarting; the cooldown keeps the watchdog
#     from spinning it in a tight loop, and the failure stays visible in
#     the journal for the owner.
#   * Every failed check, restart, and recovery is logged through
#     `logger -t sds-watchdog` and echoed to stdout (the watchdog
#     service's journal).
#   * Escalation into repair (full self-repair layer, 2026-11-23):
#     a plain restart is tried first. If the service is still down
#     in a later round of the SAME incident — a plain restart was
#     already attempted without recovery — the watchdog invokes the
#     diagnose-and-repair playbook (/usr/local/sbin/sds_repair.sh
#     <service-key>) instead of restarting again, under the same
#     5-minute cooldown stamp; the playbook applies its own cap of
#     3 repair attempts per incident and escalates (exit 2, no
#     mutation) when no playbook signature matches. The per-incident
#     plain-restart count (restarts-<name> in the state directory)
#     and the playbook's attempt counter are both cleared when the
#     service passes a health check again — that is what ends an
#     incident. If sds_repair.sh is not installed, the watchdog
#     keeps plain-restarting exactly as before.
#
# Service table (unit, owner, health check) — established from the repo:
#   sanders-dash-seal.service              system  http://127.0.0.1:8000/healthz (app /healthz)
#   uncle-nickey-mao                       system  http://127.0.0.1:8000/api/uncle-nickey-mao/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   carehive-os                            system  http://127.0.0.1:8000/api/carehive-os/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   home-healthcare                        system  http://127.0.0.1:8000/api/home-healthcare/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   grantwriter                            system  http://127.0.0.1:8000/api/grantwriter/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   pbd-validation                         system  http://127.0.0.1:8000/api/pbd-validation/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   pbd-manifest-generator                 system  http://127.0.0.1:8000/api/pbd-manifest-generator/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   vault                                  system  http://127.0.0.1:8000/api/vault/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   pbd-sentinel                           system  http://127.0.0.1:8000/api/pbd-sentinel/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   it-ai-manager                          system  http://127.0.0.1:8000/api/it-ai-manager/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   twin-gate                              system  http://127.0.0.1:8000/api/twin-gate/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sharpshooter                           system  http://127.0.0.1:8000/api/sharpshooter/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   labyrinth-shield                       system  http://127.0.0.1:8000/api/labyrinth-shield/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   minotaur                               system  http://127.0.0.1:8000/api/minotaur/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   glass-box-audit                        system  http://127.0.0.1:8000/api/glass-box-audit/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   architect                              system  http://127.0.0.1:8000/api/architect/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   archimedes-43                          system  http://127.0.0.1:8000/api/archimedes-43/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   promethean                             system  http://127.0.0.1:8000/api/promethean/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   hydra-q                                system  http://127.0.0.1:8000/api/hydra-q/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   labyrinth                              system  http://127.0.0.1:8000/api/labyrinth/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   cerberus                               system  http://127.0.0.1:8000/api/cerberus/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   chorus                                 system  http://127.0.0.1:8000/api/chorus/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   cobol-synthetic-ai                     system  http://127.0.0.1:8000/api/cobol-synthetic-ai/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   juggernaut                             system  http://127.0.0.1:8000/api/juggernaut/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   bozly                                  system  http://127.0.0.1:8000/api/bozly/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   fraud-rtsa                             system  http://127.0.0.1:8000/api/fraud-rtsa/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   operations-rtsa                        system  http://127.0.0.1:8000/api/operations-rtsa/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   uptime-agent                           system  http://127.0.0.1:8000/api/uptime-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   application-agent                      system  http://127.0.0.1:8000/api/application-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   database-agent                         system  http://127.0.0.1:8000/api/database-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   deployment-agent                       system  http://127.0.0.1:8000/api/deployment-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   infrastructure-agent                   system  http://127.0.0.1:8000/api/infrastructure-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   integration-agent                      system  http://127.0.0.1:8000/api/integration-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   performance-agent                      system  http://127.0.0.1:8000/api/performance-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   backup-recovery-agent                  system  http://127.0.0.1:8000/api/backup-recovery-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   observability-agent                    system  http://127.0.0.1:8000/api/observability-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   quality-agent                          system  http://127.0.0.1:8000/api/quality-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   configuration-agent                    system  http://127.0.0.1:8000/api/configuration-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   it-support-agent                       system  http://127.0.0.1:8000/api/it-support-agent/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-sentinel                       system  http://127.0.0.1:8000/api/sanders-sentinel/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   lil-mama                               system  http://127.0.0.1:8000/api/lil-mama/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   baby-girl                              system  http://127.0.0.1:8000/api/baby-girl/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-omniconn                       system  http://127.0.0.1:8000/api/sanders-omniconn/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   gia-mind                               system  http://127.0.0.1:8000/api/gia-mind/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   ai-doctor                              system  http://127.0.0.1:8000/api/ai-doctor/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   ai-psychiatrist                        system  http://127.0.0.1:8000/api/ai-psychiatrist/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-recon                          system  http://127.0.0.1:8000/api/sanders-recon/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-senior-living                  system  http://127.0.0.1:8000/api/sanders-senior-living/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-legal-helpers                  system  http://127.0.0.1:8000/api/sanders-legal-helpers/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-education                      system  http://127.0.0.1:8000/api/sanders-education/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-finance                        system  http://127.0.0.1:8000/api/sanders-finance/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-retail                         system  http://127.0.0.1:8000/api/sanders-retail/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-logistics                      system  http://127.0.0.1:8000/api/sanders-logistics/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-security                       system  http://127.0.0.1:8000/api/sanders-security/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-real-estate                    system  http://127.0.0.1:8000/api/sanders-real-estate/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-energy                         system  http://127.0.0.1:8000/api/sanders-energy/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-transportation                 system  http://127.0.0.1:8000/api/sanders-transportation/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-agriculture                    system  http://127.0.0.1:8000/api/sanders-agriculture/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-manufacturing                  system  http://127.0.0.1:8000/api/sanders-manufacturing/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-consulting                     system  http://127.0.0.1:8000/api/sanders-consulting/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-hospitality                    system  http://127.0.0.1:8000/api/sanders-hospitality/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-entertainment                  system  http://127.0.0.1:8000/api/sanders-entertainment/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-sports                         system  http://127.0.0.1:8000/api/sanders-sports/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-wellness                       system  http://127.0.0.1:8000/api/sanders-wellness/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-steward-sentinel               system  http://127.0.0.1:8000/api/sanders-steward-sentinel/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-patriot-saint                  system  http://127.0.0.1:8000/api/sanders-patriot-saint/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-freedom-revolution             system  http://127.0.0.1:8000/api/sanders-freedom-revolution/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-strategy-hub                   system  http://127.0.0.1:8000/api/sanders-strategy-hub/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-global-freedom                 system  http://127.0.0.1:8000/api/sanders-global-freedom/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-coordinator                    system  http://127.0.0.1:8000/api/sanders-coordinator/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-intelligence                   system  http://127.0.0.1:8000/api/sanders-intelligence/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-ai-research                    system  http://127.0.0.1:8000/api/sanders-ai-research/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   sanders-research                       system  http://127.0.0.1:8000/api/sanders-research/healthz (in-process surface of sanders-dash-seal.service, checked over loopback)
#   money-factory-legal.service            system  http://127.0.0.1:8668/health (Money Factory /health)
#   sanders-corporations-secretary.service user    http://127.0.0.1:8791/api/health (app/main.py @app.get("/api/health"))
#   sanders-twostep.service                user    http://127.0.0.1:9400/healthz (sanders_twostep_v2.py)
#   sanders-judge.service                  user    http://127.0.0.1:9405/healthz (the_judge.py)
#   nginx.service                          system  listeners on BOTH port 80 and port 443 (ss -ltn)
#
# The three --user services are owned by the opc user: their deploy
# scripts (sanders-corporations-secretary/deploy/oracle/
# deploy_secretary.sh and sanders-twostep/deploy/oracle/
# deploy_twostep.sh) install the units under opc's ~/.config/systemd/
# user and call `loginctl enable-linger opc`. Restarts therefore go
# through opc's user manager (see restart_user_service below).
#
# State (per-service failure counters and last-restart stamps) lives in
# /var/lib/sds-watchdog/ so the cooldown survives reboots; /run is the
# fallback if /var/lib is unavailable.
#
# Certificate coverage guard (added 2026-11-23, owner directive the
# same day: "ensure they always have the right certification by design
# globally correct"): every cycle also verifies that every name nginx
# serves (the server_name list in the installed server conf) is
# present on the certificate nginx actually serves, and that the
# certificate is not close to expiry. The incident this guards against
# happened 2026-11-23: www.sanderslegalhelpersllc.com went live in DNS
# with no certificate coverage (it had no DNS record when the
# certificate was issued, so it was never on it) and the gap was found
# by the owner on his phone — not by the platform. The guard DETECTS
# and ESCALATES only: it never restarts anything and never touches the
# certificate. Issuing or expanding a certificate is an owner-approved
# action (the 2026-11-23 boundary: secrets, gates, and money stay the
# owner's; certificate issuance is in that class). Escalation is a
# journal record (logger -t sds-watchdog), which the morning briefing
# reads — the same escalation channel the repair layer uses.
#
# Public-face guard (added 2026-11-23, owner standing rule the same
# day: "Everything that has its own domain name should always be the
# public facing RTSA platform"): every cycle also verifies that every
# name nginx serves returns the public Dash & Seal storefront at / —
# the marker is the storefront banner ("dash-seal-banner" in the
# response body, verified live on all 10 served names 2026-11-23) —
# never a backend, a placeholder, or a dead page. The incident class
# this guards against is a backend exposed as a domain's public face
# (the Police Men dashboard, taken off public view 2026-11-23). Like
# the certificate guard, this guard DETECTS and ESCALATES only: it
# never restarts anything and never changes what a name serves.
# Fixing a wrong face is a content/config change through the normal
# deploy path, not a watchdog action.
set -u

STATE_DIR="/var/lib/sds-watchdog"
FAIL_LIMIT=2
COOLDOWN_SEC=300
USER_SERVICES_OWNER="opc"

log_msg() {
  local msg="$1"
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') sds-watchdog: $msg"
  logger -t sds-watchdog -- "$msg" 2>/dev/null || true
}

counter_file() { printf '%s/fails-%s' "$STATE_DIR" "$1"; }
stamp_file() { printf '%s/last-restart-%s' "$STATE_DIR" "$1"; }
restarts_file() { printf '%s/restarts-%s' "$STATE_DIR" "$1"; }

read_counter() {
  local f v=0
  f="$(counter_file "$1")"
  if [ -f "$f" ]; then
    v="$(cat "$f" 2>/dev/null || echo 0)"
  fi
  case "$v" in ''|*[!0-9]*) v=0 ;; esac
  printf '%s' "$v"
}

# How many plain restarts this incident has already used (cleared
# when the service recovers; see note_result).
read_restarts() {
  local f v=0
  f="$(restarts_file "$1")"
  if [ -f "$f" ]; then
    v="$(cat "$f" 2>/dev/null || echo 0)"
  fi
  case "$v" in ''|*[!0-9]*) v=0 ;; esac
  printf '%s' "$v"
}

# The watchdog's service name -> the repair playbook's service key
# (deploy/sds_repair.sh). All six watchdog services have a key.
repair_key_for() {
  case "$1" in
    sanders-dash-seal) printf '%s' "app" ;;
    money-factory-legal) printf '%s' "money-factory" ;;
    secretary) printf '%s' "secretary" ;;
    twostep) printf '%s' "twostep" ;;
    judge) printf '%s' "judge" ;;
    nginx) printf '%s' "nginx" ;;
    *) printf '%s' "" ;;
  esac
}

# Restart a systemd --user service owned by $2 (opc). Primary form asks
# that user's manager directly; the fallback goes through runuser with
# the user bus address set explicitly, which works on older systemd.
restart_user_service() {
  local unit="$1" user="$2"
  local uid
  uid="$(id -u "$user" 2>/dev/null)" || {
    log_msg "cannot restart $unit: owner user '$user' does not exist on this instance"
    return 1
  }
  if systemctl --machine="${user}@" --user restart "$unit" 2>/dev/null; then
    return 0
  fi
  runuser -u "$user" -- env "XDG_RUNTIME_DIR=/run/user/${uid}" systemctl --user restart "$unit"
}

do_restart() {
  local unit="$1" scope="$2"
  if [ "$scope" = "user" ]; then
    restart_user_service "$unit" "$USER_SERVICES_OWNER"
  else
    systemctl restart "$unit"
  fi
}

# Restart $unit for service $1, unless it was already restarted within
# the cooldown window.
maybe_restart() {
  local name="$1" unit="$2" scope="$3"
  local sf now last=0 elapsed
  sf="$(stamp_file "$name")"
  now="$(date +%s)"
  if [ -f "$sf" ]; then
    last="$(cat "$sf" 2>/dev/null || echo 0)"
  fi
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  elapsed=$(( now - last ))
  if [ "$last" -gt 0 ] && [ "$elapsed" -lt "$COOLDOWN_SEC" ]; then
    log_msg "$name: still down, but in restart cooldown (last restart ${elapsed}s ago, cooldown ${COOLDOWN_SEC}s); not restarting"
    return 0
  fi
  # Escalation: a plain restart was already attempted earlier in
  # this incident and the service did not recover — hand the
  # incident to the repair playbook instead of restarting again.
  # The playbook invocation consumes the same cooldown stamp, and
  # the playbook enforces its own 3-attempts-per-incident cap.
  local key restarts
  key="$(repair_key_for "$name")"
  restarts="$(read_restarts "$name")"
  if [ -n "$key" ] && [ "$restarts" -ge 1 ] && [ -x /usr/local/sbin/sds_repair.sh ]; then
    log_msg "$name: plain restart already attempted this incident without recovery; escalating to the repair playbook (sds_repair.sh $key)"
    local rrc=0
    /usr/local/sbin/sds_repair.sh "$key" || rrc=$?
    if [ "$rrc" = "0" ]; then
      log_msg "$name: repair playbook run for $key finished; recovery is verified by the following health checks"
    else
      log_msg "$name: repair playbook for $key exited $rrc (2 = escalated without mutation, repair refused/failed, or attempt cap reached; see the sds-repair journal and /var/lib/sds-repair/incidents.jsonl)"
    fi
    printf '%s' "$now" > "$sf" 2>/dev/null || true
    printf '0' > "$(counter_file "$name")" 2>/dev/null || true
    return 0
  fi
  log_msg "$name: restarting $unit (scope: $scope)"
  if do_restart "$unit" "$scope"; then
    printf '%s' "$now" > "$sf" 2>/dev/null || true
    printf '0' > "$(counter_file "$name")" 2>/dev/null || true
    printf '%s' $(( restarts + 1 )) > "$(restarts_file "$name")" 2>/dev/null || true
    log_msg "$name: restart of $unit issued; failure counter reset (plain restart $(( restarts + 1 )) this incident)"
  else
    log_msg "$name: ERROR: restart of $unit failed; see the journal for $unit"
  fi
}

# Record one check outcome for a service: $4 is 1 (healthy) or 0 (down),
# $5 is a human-readable detail for the log.
note_result() {
  local name="$1" unit="$2" scope="$3" ok="$4" detail="$5"
  local cf prev count
  cf="$(counter_file "$name")"
  if [ "$ok" = "1" ]; then
    prev="$(read_counter "$name")"
    if [ "$prev" != "0" ]; then
      log_msg "$name: recovered — $detail"
    fi
    printf '0' > "$cf" 2>/dev/null || true
    # A passing health check ends the incident: clear the
    # plain-restart count and the repair playbook's attempt counter
    # for this service, so the next incident starts fresh.
    rm -f "$(restarts_file "$name")" 2>/dev/null || true
    local key
    key="$(repair_key_for "$name")"
    if [ -n "$key" ]; then
      rm -f "$STATE_DIR/repair-attempts-$key" 2>/dev/null || true
    fi
    return 0
  fi
  count="$(read_counter "$name")"
  count=$(( count + 1 ))
  printf '%s' "$count" > "$cf" 2>/dev/null || true
  log_msg "$name: health check FAILED ($count/$FAIL_LIMIT) — $detail"
  if [ "$count" -ge "$FAIL_LIMIT" ]; then
    maybe_restart "$name" "$unit" "$scope"
  fi
}

# HTTP health check: healthy only on an exact HTTP 200.
check_http() {
  local name="$1" unit="$2" scope="$3" url="$4"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || true)"
  if [ "$code" = "200" ]; then
    note_result "$name" "$unit" "$scope" 1 "$url answered HTTP 200"
  else
    note_result "$name" "$unit" "$scope" 0 "$url answered HTTP ${code:-000} (expected 200)"
  fi
}

# nginx is healthy only while it listens on BOTH 80 and 443. The
# 2026-11-23 outage had nginx running with no 443 listener at all, so
# process state alone is not a sufficient check. Ports are matched
# exactly (8000/8668 must not count as 80).
check_nginx() {
  local ports missing=""
  ports="$(ss -ltn 2>/dev/null | awk 'NR>1 {print $4}' | sed 's/.*://' | sort -u || true)"
  printf '%s\n' "$ports" | grep -qx '80' || missing="${missing} 80"
  printf '%s\n' "$ports" | grep -qx '443' || missing="${missing} 443"
  if [ -z "$missing" ]; then
    note_result "nginx" "nginx.service" "system" 1 "nginx listening on ports 80 and 443"
  else
    note_result "nginx" "nginx.service" "system" 0 "nginx NOT listening on port(s):$missing"
  fi
}

CERT_CONF="/etc/nginx/conf.d/money_factory_legal_server.conf"
CERT_FILE="/etc/letsencrypt/live/sandersdashandseal.com/cert.pem"
CERT_MIN_DAYS=21

# Names nginx serves, from the installed server conf (bare IPs and the
# "_" catch-all are not certificate names).
cert_served_names() {
  grep -h '^[[:space:]]*server_name' "$CERT_CONF" 2>/dev/null \
    | tr ';' ' ' \
    | awk '{for (i=2; i<=NF; i++) print $i}' \
    | grep -v '^_$' \
    | grep -vE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' \
    | sort -u
}

# Names on the certificate nginx actually serves (asked over loopback
# TLS, so the answer is the live served cert, not just a file on disk).
cert_cert_names() {
  echo | openssl s_client -connect 127.0.0.1:443 -servername sandersdashandseal.com 2>/dev/null \
    | openssl x509 -noout -ext subjectAltName 2>/dev/null \
    | grep -o 'DNS:[^,]*' | sed 's/^DNS://' | sort -u
}

# Record a cert-coverage outcome. Unlike note_result this NEVER
# restarts anything: a coverage gap is escalated once per incident
# (cert-escalated stamp) and stays visible in the journal until a
# check passes again.
note_cert_result() {
  local ok="$1" detail="$2"
  local cf ef count
  cf="$(counter_file "cert-coverage")"
  ef="$STATE_DIR/cert-escalated"
  if [ "$ok" = "1" ]; then
    if [ "$(read_counter "cert-coverage")" != "0" ] || [ -f "$ef" ]; then
      log_msg "cert-coverage: recovered — $detail"
    fi
    printf '0' > "$cf" 2>/dev/null || true
    rm -f "$ef" 2>/dev/null || true
    return 0
  fi
  count="$(read_counter "cert-coverage")"
  count=$(( count + 1 ))
  printf '%s' "$count" > "$cf" 2>/dev/null || true
  log_msg "cert-coverage: check FAILED ($count/$FAIL_LIMIT) — $detail"
  if [ "$count" -ge "$FAIL_LIMIT" ] && [ ! -f "$ef" ]; then
    printf '%s' "$(date +%s)" > "$ef" 2>/dev/null || true
    log_msg "cert-coverage: ESCALATED — a certificate coverage gap needs the owner (issuing/expanding a certificate is owner-approved; the watchdog does not touch certificates): $detail"
  fi
}

# Record an evidence-integrity outcome. Mirrors note_cert_result:
# this NEVER restarts or repairs anything — a broken, gapped, or
# diverged evidence chain is escalated once per incident
# (evidence-escalated stamp) and stays visible in the journal until
# a check passes again. Evidence is never repaired by automation.
note_evidence_result() {
  local ok="$1" detail="$2"
  local cf ef count
  cf="$(counter_file "evidence-integrity")"
  ef="$STATE_DIR/evidence-escalated"
  if [ "$ok" = "1" ]; then
    if [ "$(read_counter "evidence-integrity")" != "0" ] || [ -f "$ef" ]; then
      log_msg "evidence-integrity: recovered — $detail"
    fi
    printf '0' > "$cf" 2>/dev/null || true
    rm -f "$ef" 2>/dev/null || true
    return 0
  fi
  count="$(read_counter "evidence-integrity")"
  count=$(( count + 1 ))
  printf '%s' "$count" > "$cf" 2>/dev/null || true
  log_msg "evidence-integrity: check FAILED ($count/$FAIL_LIMIT) — $detail"
  if [ "$count" -ge "$FAIL_LIMIT" ] && [ ! -f "$ef" ]; then
    printf '%s' "$(date +%s)" > "$ef" 2>/dev/null || true
    log_msg "evidence-integrity: ESCALATED — an evidence-integrity failure needs the owner (the watchdog detects and escalates only; it never repairs evidence): $detail"
  fi
}

# Independent evidence-integrity detection between the Glass-Box
# Audit platform's own verification runs (strengthening design,
# Priority 4): the read-only verifier recomputes both evidence
# chains, their sequence contiguity, the prefix property against
# the last anchor, anchor freshness, and drill currency.
EVIDENCE_VERIFY="/opt/Sanders_Dash_Seal/deploy/sds_evidence_verify.py"
EVIDENCE_DATA_DIR="/opt/Sanders_Dash_Seal/data"
check_evidence_integrity() {
  local py out rc
  py="/opt/Sanders_Dash_Seal/venv/bin/python"
  [ -x "$py" ] || py="python3"
  if [ ! -f "$EVIDENCE_VERIFY" ]; then
    note_evidence_result 0 "evidence verifier missing ($EVIDENCE_VERIFY)"
    return 0
  fi
  out="$("$py" "$EVIDENCE_VERIFY" "$EVIDENCE_DATA_DIR" 2>&1)"
  rc=$?
  if [ "$rc" = "0" ]; then
    note_evidence_result 1 "$out"
  else
    note_evidence_result 0 "$out"
  fi
}

check_cert_coverage() {
  local served certnames missing="" n
  served="$(cert_served_names)"
  certnames="$(cert_cert_names)"
  if [ -z "$served" ] || [ -z "$certnames" ]; then
    note_cert_result 0 "cannot read the served names ($CERT_CONF) or the served certificate"
    return 0
  fi
  for n in $served; do
    printf '%s\n' "$certnames" | grep -qx "$n" || missing="${missing} $n"
  done
  # Expiry: automatic renewal should keep the cert far from expiry;
  # under CERT_MIN_DAYS means renewal is not doing its job.
  local expiry_note=""
  if [ -f "$CERT_FILE" ]; then
    local end_epoch now_epoch days
    end_epoch="$(date -d "$(openssl x509 -noout -enddate -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)" +%s 2>/dev/null || echo 0)"
    now_epoch="$(date +%s)"
    if [ "$end_epoch" -gt 0 ]; then
      days=$(( (end_epoch - now_epoch) / 86400 ))
      if [ "$days" -lt "$CERT_MIN_DAYS" ]; then
        expiry_note=" certificate expires in ${days}d (< ${CERT_MIN_DAYS}d)"
      fi
    fi
  fi
  if [ -z "$missing" ] && [ -z "$expiry_note" ]; then
    note_cert_result 1 "every served name is on the certificate"
  else
    note_cert_result 0 "missing from certificate:${missing:- none};${expiry_note}"
  fi
}

FACE_MARKER="dash-seal-banner"

# Record a public-face outcome. Mirrors note_cert_result: this NEVER
# restarts or changes anything — a wrong public face is escalated
# once per incident (public-face-escalated stamp) and stays visible
# in the journal until a check passes again.
note_face_result() {
  local ok="$1" detail="$2"
  local cf ef count
  cf="$(counter_file "public-face")"
  ef="$STATE_DIR/public-face-escalated"
  if [ "$ok" = "1" ]; then
    if [ "$(read_counter "public-face")" != "0" ] || [ -f "$ef" ]; then
      log_msg "public-face: recovered — $detail"
    fi
    printf '0' > "$cf" 2>/dev/null || true
    rm -f "$ef" 2>/dev/null || true
    return 0
  fi
  count="$(read_counter "public-face")"
  count=$(( count + 1 ))
  printf '%s' "$count" > "$cf" 2>/dev/null || true
  log_msg "public-face: check FAILED ($count/$FAIL_LIMIT) — $detail"
  if [ "$count" -ge "$FAIL_LIMIT" ] && [ ! -f "$ef" ]; then
    printf '%s' "$(date +%s)" > "$ef" 2>/dev/null || true
    log_msg "public-face: ESCALATED — a served name is not returning the public Dash & Seal storefront (owner standing rule 2026-11-23: every domain serves its public-facing RTSA platform, never a backend or placeholder; the watchdog does not change what a name serves): $detail"
  fi
}

# Every served name must return the public storefront at /. Each name
# is asked over loopback TLS with --resolve, so the answer is what
# THIS nginx serves for that name (the www name's public path goes
# through the Cloudflare proxy; what the origin serves is the part
# this platform controls and the part that can silently regress).
check_public_face() {
  local served bad="" n body
  served="$(cert_served_names)"
  if [ -z "$served" ]; then
    note_face_result 0 "cannot read the served names ($CERT_CONF)"
    return 0
  fi
  for n in $served; do
    body="$(curl -sk --max-time 15 --resolve "${n}:443:127.0.0.1" "https://${n}/" 2>/dev/null || true)"
    case "$body" in
      *"$FACE_MARKER"*) : ;;
      *) bad="${bad} $n" ;;
    esac
  done
  if [ -z "$bad" ]; then
    note_face_result 1 "every served name returns the public storefront"
  else
    note_face_result 0 "served name(s) NOT returning the public storefront:${bad}"
  fi
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    log_msg "ERROR: curl not found; the watchdog cannot health-check (misconfigured)"
    exit 1
  fi
  if ! mkdir -p "$STATE_DIR" 2>/dev/null; then
    STATE_DIR="/run/sds-watchdog"
    if ! mkdir -p "$STATE_DIR" 2>/dev/null; then
      log_msg "ERROR: cannot create a state directory (/var/lib/sds-watchdog or /run/sds-watchdog); watchdog misconfigured"
      exit 1
    fi
  fi

  check_http "sanders-dash-seal" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/healthz"
  check_http "uncle-nickey-mao" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/uncle-nickey-mao/healthz"
  check_http "carehive-os" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/carehive-os/healthz"
  check_http "home-healthcare" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/home-healthcare/healthz"
  check_http "grantwriter" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/grantwriter/healthz"
  check_http "pbd-validation" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/pbd-validation/healthz"
  check_http "pbd-manifest-generator" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/pbd-manifest-generator/healthz"
  check_http "vault" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/vault/healthz"
  check_http "pbd-sentinel" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/pbd-sentinel/healthz"
  check_http "it-ai-manager" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/it-ai-manager/healthz"
  check_http "twin-gate" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/twin-gate/healthz"
  check_http "sharpshooter" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sharpshooter/healthz"
  check_http "labyrinth-shield" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/labyrinth-shield/healthz"
  check_http "minotaur" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/minotaur/healthz"
  check_http "glass-box-audit" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/glass-box-audit/healthz"
  check_http "architect" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/architect/healthz"
  check_http "archimedes-43" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/archimedes-43/healthz"
  check_http "promethean" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/promethean/healthz"
  check_http "hydra-q" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/hydra-q/healthz"
  check_http "labyrinth" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/labyrinth/healthz"
  check_http "cerberus" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/cerberus/healthz"
  check_http "chorus" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/chorus/healthz"
  check_http "cobol-synthetic-ai" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/cobol-synthetic-ai/healthz"
  check_http "juggernaut" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/juggernaut/healthz"
  check_http "bozly" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/bozly/healthz"
  check_http "fraud-rtsa" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/fraud-rtsa/healthz"
  check_http "operations-rtsa" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/operations-rtsa/healthz"
  check_http "uptime-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/uptime-agent/healthz"
  check_http "application-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/application-agent/healthz"
  check_http "database-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/database-agent/healthz"
  check_http "deployment-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/deployment-agent/healthz"
  check_http "infrastructure-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/infrastructure-agent/healthz"
  check_http "integration-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/integration-agent/healthz"
  check_http "performance-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/performance-agent/healthz"
  check_http "backup-recovery-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/backup-recovery-agent/healthz"
  check_http "observability-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/observability-agent/healthz"
  check_http "quality-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/quality-agent/healthz"
  check_http "configuration-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/configuration-agent/healthz"
  check_http "it-support-agent" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/it-support-agent/healthz"
  check_http "sanders-sentinel" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-sentinel/healthz"
  check_http "lil-mama" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/lil-mama/healthz"
  check_http "baby-girl" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/baby-girl/healthz"
  check_http "sanders-omniconn" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-omniconn/healthz"
  check_http "gia-mind" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/gia-mind/healthz"
  check_http "ai-doctor" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/ai-doctor/healthz"
  check_http "ai-psychiatrist" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/ai-psychiatrist/healthz"
  check_http "sanders-recon" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-recon/healthz"
  check_http "sanders-senior-living" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-senior-living/healthz"
  check_http "sanders-legal-helpers" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-legal-helpers/healthz"
  check_http "sanders-education" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-education/healthz"
  check_http "sanders-finance" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-finance/healthz"
  check_http "sanders-retail" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-retail/healthz"
  check_http "sanders-logistics" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-logistics/healthz"
  check_http "sanders-security" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-security/healthz"
  check_http "sanders-real-estate" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-real-estate/healthz"
  check_http "sanders-energy" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-energy/healthz"
  check_http "sanders-transportation" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-transportation/healthz"
  check_http "sanders-agriculture" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-agriculture/healthz"
  check_http "sanders-manufacturing" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-manufacturing/healthz"
  check_http "sanders-consulting" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-consulting/healthz"
  check_http "sanders-hospitality" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-hospitality/healthz"
  check_http "sanders-entertainment" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-entertainment/healthz"
  check_http "sanders-sports" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-sports/healthz"
  check_http "sanders-wellness" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-wellness/healthz"
  check_http "sanders-steward-sentinel" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-steward-sentinel/healthz"
  check_http "sanders-patriot-saint" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-patriot-saint/healthz"
  check_http "sanders-freedom-revolution" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-freedom-revolution/healthz"
  check_http "sanders-strategy-hub" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-strategy-hub/healthz"
  check_http "sanders-global-freedom" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-global-freedom/healthz"
  check_http "sanders-coordinator" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-coordinator/healthz"
  check_http "sanders-intelligence" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-intelligence/healthz"
  check_http "sanders-ai-research" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-ai-research/healthz"
  check_http "sanders-research" "sanders-dash-seal.service" "system" "http://127.0.0.1:8000/api/sanders-research/healthz"
  check_http "money-factory-legal" "money-factory-legal.service" "system" "http://127.0.0.1:8668/health"
  check_http "secretary" "sanders-corporations-secretary.service" "user" "http://127.0.0.1:8791/api/health"
  check_http "twostep" "sanders-twostep.service" "user" "http://127.0.0.1:9400/healthz"
  check_http "judge" "sanders-judge.service" "user" "http://127.0.0.1:9405/healthz"
  check_nginx
  check_cert_coverage
  check_evidence_integrity
  check_public_face

  exit 0
}

main "$@"
