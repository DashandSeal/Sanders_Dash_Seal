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
  check_http "money-factory-legal" "money-factory-legal.service" "system" "http://127.0.0.1:8668/health"
  check_http "secretary" "sanders-corporations-secretary.service" "user" "http://127.0.0.1:8791/api/health"
  check_http "twostep" "sanders-twostep.service" "user" "http://127.0.0.1:9400/healthz"
  check_http "judge" "sanders-judge.service" "user" "http://127.0.0.1:9405/healthz"
  check_nginx

  exit 0
}

main "$@"
