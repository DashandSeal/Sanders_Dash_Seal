#!/usr/bin/env bash
# sds_repair.sh — the diagnose-and-repair playbook for the Sanders
# Dash & Seal platform services on the Oracle instance.
#
# Owner decision (2026-11-23): "Build the full self-repair layer —
# playbook repairs run on their own, secrets, gates, and money
# always stay mine." This script is that layer's hands. The
# sds-watchdog timer (deploy/sds_watchdog.sh) health-checks every
# service every 2 minutes and restarts one that stops answering;
# when a plain restart in an earlier round of the same incident did
# not recover the service, the watchdog invokes this playbook
# instead of restarting again. It can also be run by hand:
#
#   sds_repair.sh <service-key>     diagnose + repair one service
#   sds_repair.sh gitperms          repair checkout .git ownership
#   sds_repair.sh restore-lkg <what>  restore from the newest
#                                   last-known-good snapshot
#                                   (<what>: nginx | app | env | watchdog)
#
# service-key ∈ {app, money-factory, secretary, twostep, judge,
# nginx} — the same services, units, owners, and health endpoints
# as the watchdog's table (see deploy/sds_watchdog.sh).
#
# HARD BOUNDARIES (owner's words, 2026-11-23 — these are encoded
# here and in docs/SPEC_CONFORMANCE.md, and no playbook entry may
# cross them):
#   * NEVER create, rotate, or guess a secret value. The only
#     secret handling allowed is re-fetching the owner's existing
#     OCI Vault secret unchanged (P1, via deploy/sds_env_guard.sh /
#     deploy/refresh_provider_secrets.py) and restoring the
#     byte-for-byte runtime.env copy held in a root-only
#     last-known-good snapshot (restore-lkg env) — a file that was
#     verified working when the snapshot was taken.
#   * NEVER approve any gate (the Production-Authorization-Gate or
#     any other), in GitHub or anywhere else.
#   * NEVER touch Stripe settings, payments, or money.
#   * NEVER edit or push the repository. Repairs act on the
#     instance's installed files and live state only, and P4 copies
#     FROM the checkout, never writes to it (P5's chown of .git
#     metadata ownership is the one exception, and it changes no
#     content).
#   * NEVER delete application data. The only process action
#     allowed is P3's kill of a stale non-unit gunicorn process
#     holding port 8000 — and P3 refuses to kill anything whose
#     command line is not gunicorn.
#
# THE PLAYBOOK (exactly one class per incident round, or UNKNOWN):
#   P1 env      app: /etc/sanders-dash-seal/runtime.env missing, or
#               STRIPE_WEBHOOK_SECRET not whsec_-shaped → run the
#               env guard's Vault refresh path, verify the shape,
#               restart the app.
#   P2 datadir  app: journal shows a PermissionError / permission
#               denied / mkdir failure at data_dir, OR
#               /opt/Sanders_Dash_Seal/data is missing or not owned
#               by sanders → mkdir -p + chown sanders:sanders,
#               restart the app.
#   P3 port     app: port 8000 is held by a gunicorn process that
#               is not the app unit's MainPID (a stale non-systemd
#               copy) → TERM it, KILL after 3s if it still holds
#               the port, restart the app.
#   P4 nginx    nginx: `nginx -t` fails, or nginx is not listening
#               on port 80 or 443 → reinstall the server conf +
#               snippet from the repo checkout (the same sources
#               deploy_all.sh installs), nginx -t, restart nginx.
#               If the checkout copies are unavailable or fail
#               `nginx -t`, restore from the newest last-known-good
#               snapshot instead. If neither source passes
#               `nginx -t`, the previously installed files are put
#               back and nginx is NOT restarted into a bad config.
#   P5 gitperms checkout: deploy evidence of .git permission
#               failure (deploy_all run #100, 2026-11-22). The
#               watchdog never syncs the repo, so this class has no
#               automatic trigger; it is exposed as the manual
#               entry point `sds_repair.sh gitperms` → chown -R
#               opc:opc /opt/Sanders_Dash_Seal/.git.
#   P6 parked   any service: the unit is in a failed state (for the
#               app, only after P1–P3 are excluded) → systemctl
#               reset-failed + restart, through the unit's own
#               manager (system, or opc's user manager for the
#               Secretary, TwoStep, and Judge).
#   UNKNOWN     none of the signatures match → NO mutation. An
#               escalation record with the gathered evidence is
#               appended to the incident log and the script exits 2.
#
# CAPS AND RECORDS:
#   * At most 3 repair attempts per service per incident. Attempt
#     counters live in /var/lib/sds-watchdog/ (shared with the
#     watchdog: repair-attempts-<service-key>). An incident ends
#     when the service passes a health check — the watchdog clears
#     the counter when it sees the service healthy, and this script
#     clears it when its own entry or post-repair check passes.
#     When the cap is reached the script escalates (exit 2) instead
#     of mutating anything.
#   * Every classification, repair action, and outcome is appended
#     as one JSON object per line to
#     /var/lib/sds-repair/incidents.jsonl (directory root-only,
#     0700; file 0600). Fields: ts, service, class, evidence,
#     action, result. The same events are logged through
#     `logger -t sds-repair`.
#   * Bozly witnessing: the repo's Bozly recorder is an in-process
#     component of the WSGI app (core_platform/bozly_wiring.
#     BozlyRecorder) that records VERIFIED STRIPE EVENTS; the repo
#     exposes no machine-event or receipt route a root shell script
#     could submit an incident record to. This script therefore
#     does NOT invent one — incidents.jsonl + the journal are the
#     record until a Bozly machine-event route exists (open item,
#     docs/SPEC_CONFORMANCE.md).
#
# Exit codes: 0 = service healthy, or a repair was attempted (the
# watchdog verifies recovery over the following rounds); 1 = the
# script itself is misconfigured (not root, no usable state
# directory); 2 = escalation (UNKNOWN class, attempt cap reached,
# or a repair refused/failed) — no further mutation this round.
#
# Installed by deploy/deploy_all.sh (step 5c) to
# /usr/local/sbin/sds_repair.sh; the repo copy is
# deploy/sds_repair.sh.
set -u

REPO_DIR="${SDS_REPO_DIR:-/opt/Sanders_Dash_Seal}"
RUNTIME_ENV="/etc/sanders-dash-seal/runtime.env"
DATA_DIR="$REPO_DIR/data"
APP_UNIT="sanders-dash-seal.service"
ENV_SHAPE_RE='^[[:space:]]*STRIPE_WEBHOOK_SECRET=whsec_'
STATE_DIR="/var/lib/sds-watchdog"
REPAIR_DIR="/var/lib/sds-repair"
INCIDENTS="$REPAIR_DIR/incidents.jsonl"
LKG_BASE="/var/lib/sds-lkg"
MAX_ATTEMPTS=3
USER_SERVICES_OWNER="opc"

# ------------------------------------------------------------------
# logging and incident records
# ------------------------------------------------------------------

log_msg() {
  local msg="$1"
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') sds-repair: $msg"
  logger -t sds-repair -- "$msg" 2>/dev/null || true
}

json_escape() {
  printf '%s' "$1" | tr '\n\r\t' '   ' | sed 's/\\/\\\\/g; s/"/\\"/g' | cut -c1-220
}

record_event() {
  local service="$1" class="$2" evidence="$3" action="$4" result="$5"
  local line
  line="$(printf '{"ts":"%s","service":"%s","class":"%s","evidence":"%s","action":"%s","result":"%s"}' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "$(json_escape "$service")" "$(json_escape "$class")" \
    "$(json_escape "$evidence")" "$(json_escape "$action")" \
    "$(json_escape "$result")")"
  printf '%s\n' "$line" >> "$INCIDENTS" 2>/dev/null || \
    log_msg "WARNING: could not append to $INCIDENTS"
  log_msg "[$service/$class] $action -> $result ($evidence)"
}

# ------------------------------------------------------------------
# service table (mirrors deploy/sds_watchdog.sh)
# ------------------------------------------------------------------

unit_for() {
  case "$1" in
    app) printf '%s' "sanders-dash-seal.service" ;;
    money-factory) printf '%s' "money-factory-legal.service" ;;
    secretary) printf '%s' "sanders-corporations-secretary.service" ;;
    twostep) printf '%s' "sanders-twostep.service" ;;
    judge) printf '%s' "sanders-judge.service" ;;
    nginx) printf '%s' "nginx.service" ;;
    *) return 1 ;;
  esac
}

scope_for() {
  case "$1" in
    secretary|twostep|judge) printf '%s' "user" ;;
    *) printf '%s' "system" ;;
  esac
}

url_for() {
  case "$1" in
    app) printf '%s' "http://127.0.0.1:8000/healthz" ;;
    money-factory) printf '%s' "http://127.0.0.1:8668/health" ;;
    secretary) printf '%s' "http://127.0.0.1:8791/api/health" ;;
    twostep) printf '%s' "http://127.0.0.1:9400/healthz" ;;
    judge) printf '%s' "http://127.0.0.1:9405/healthz" ;;
    *) return 1 ;;
  esac
}

nginx_listeners_ok() {
  local ports missing=""
  ports="$(ss -ltn 2>/dev/null | awk 'NR>1 {print $4}' | sed 's/.*://' | sort -u || true)"
  printf '%s\n' "$ports" | grep -qx '80' || missing="${missing} 80"
  printf '%s\n' "$ports" | grep -qx '443' || missing="${missing} 443"
  [ -z "$missing" ]
}

# Health: 0 = healthy (same probes as the watchdog), 1 = down.
svc_health() {
  local key="$1" url code
  if [ "$key" = "nginx" ]; then
    nginx_listeners_ok
    return $?
  fi
  url="$(url_for "$key")" || return 1
  code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || true)"
  [ "$code" = "200" ]
}

# ------------------------------------------------------------------
# systemd helpers (the user-manager forms mirror the watchdog)
# ------------------------------------------------------------------

user_uid() { id -u "$USER_SERVICES_OWNER" 2>/dev/null; }

# Run a systemctl verb against an opc --user unit.
user_systemctl() {
  local verb="$1" unit="$2" uid
  uid="$(user_uid)" || return 1
  if timeout 15 systemctl --machine="${USER_SERVICES_OWNER}@" --user "$verb" "$unit" 2>/dev/null; then
    return 0
  fi
  timeout 15 runuser -u "$USER_SERVICES_OWNER" -- env "XDG_RUNTIME_DIR=/run/user/${uid}" systemctl --user "$verb" "$unit" 2>/dev/null
}

# Print a unit's ActiveState-equivalent one-word state
# (active|failed|inactive|activating|unknown).
unit_state() {
  local key="$1" unit scope out
  unit="$(unit_for "$key")"; scope="$(scope_for "$key")"
  if [ "$scope" = "user" ]; then
    out="$(user_systemctl is-active "$unit")" || out="unknown"
  else
    out="$(timeout 10 systemctl is-active "$unit" 2>/dev/null)" || out="unknown"
  fi
  case "$out" in
    active|failed|inactive|activating) printf '%s' "$out" ;;
    *) printf '%s' "unknown" ;;
  esac
}

do_restart() {
  local key="$1" unit scope
  unit="$(unit_for "$key")"; scope="$(scope_for "$key")"
  if [ "$scope" = "user" ]; then
    user_systemctl restart "$unit"
  else
    timeout 30 systemctl restart "$unit" 2>/dev/null
  fi
}

do_reset_failed() {
  local key="$1" unit scope
  unit="$(unit_for "$key")"; scope="$(scope_for "$key")"
  if [ "$scope" = "user" ]; then
    user_systemctl reset-failed "$unit" || true
  else
    timeout 15 systemctl reset-failed "$unit" 2>/dev/null || true
  fi
}

# Recent journal for the unit (bounded; empty when unavailable).
unit_journal() {
  local key="$1" unit scope uid out
  unit="$(unit_for "$key")"; scope="$(scope_for "$key")"
  if [ "$scope" = "user" ]; then
    uid="$(user_uid)" || { printf ''; return 0; }
    out="$(timeout 15 runuser -u "$USER_SERVICES_OWNER" -- env "XDG_RUNTIME_DIR=/run/user/${uid}" journalctl --user -u "$unit" -o cat -n 150 --no-pager 2>/dev/null || true)"
    if [ -z "$out" ]; then
      out="$(timeout 15 journalctl "_SYSTEMD_USER_UNIT=$unit" -o cat -n 150 --no-pager 2>/dev/null || true)"
    fi
  else
    out="$(timeout 15 journalctl -u "$unit" -o cat -n 150 --no-pager 2>/dev/null || true)"
  fi
  printf '%s' "$out"
}

journal_exceptions() {
  printf '%s\n' "$1" | grep -Ei 'error|exception|traceback|denied|failed' | tail -n 5 | tr '\n' ';'
}

# ------------------------------------------------------------------
# attempt counters (shared with the watchdog)
# ------------------------------------------------------------------

attempts_file() { printf '%s/repair-attempts-%s' "$STATE_DIR" "$1"; }

read_attempts() {
  local f v=0
  f="$(attempts_file "$1")"
  if [ -f "$f" ]; then v="$(cat "$f" 2>/dev/null || echo 0)"; fi
  case "$v" in ''|*[!0-9]*) v=0 ;; esac
  printf '%s' "$v"
}

bump_attempts() {
  local key="$1" n
  n="$(read_attempts "$key")"; n=$(( n + 1 ))
  printf '%s' "$n" > "$(attempts_file "$key")" 2>/dev/null || true
  printf '%s' "$n"
}

clear_attempts() {
  rm -f "$(attempts_file "$1")" 2>/dev/null || true
}

# ------------------------------------------------------------------
# playbook repairs. Each takes the service key and the evidence
# string, performs its mutation, records its own action records,
# and returns 0 when the repair was applied, 2 when it was refused
# or failed (escalation).
# ------------------------------------------------------------------

repair_p1_env() {
  local key="$1" evidence="$2"
  local guard=""
  if [ -x /usr/local/sbin/sds_env_guard.sh ]; then
    guard="/usr/local/sbin/sds_env_guard.sh"
  elif [ -f "$REPO_DIR/deploy/sds_env_guard.sh" ]; then
    guard="$REPO_DIR/deploy/sds_env_guard.sh"
  fi
  if [ -z "$guard" ]; then
    record_event "$key" "P1" "$evidence" "run env guard (Vault refresh path)" "refused: sds_env_guard.sh not found installed or in the checkout"
    return 2
  fi
  bash "$guard" >/dev/null 2>&1 || true
  if [ -f "$RUNTIME_ENV" ] && grep -Eq "$ENV_SHAPE_RE" "$RUNTIME_ENV" 2>/dev/null; then
    record_event "$key" "P1" "$evidence" "env guard refresh; runtime.env shape re-verified whsec_" "ok"
    if do_restart "$key"; then
      record_event "$key" "P1" "$evidence" "restart $(unit_for "$key")" "ok"
      return 0
    fi
    record_event "$key" "P1" "$evidence" "restart $(unit_for "$key")" "failed"
    return 2
  fi
  record_event "$key" "P1" "$evidence" "env guard refresh" "failed: runtime.env still missing or not whsec_-shaped after the Vault refresh; existing file left untouched; owner step (Vault secret content) — escalating"
  return 2
}

repair_p2_datadir() {
  local key="$1" evidence="$2" f
  mkdir -p "$DATA_DIR" 2>/dev/null || {
    record_event "$key" "P2" "$evidence" "mkdir -p $DATA_DIR" "failed"
    return 2
  }
  chown sanders:sanders "$DATA_DIR" 2>/dev/null || {
    record_event "$key" "P2" "$evidence" "chown sanders:sanders $DATA_DIR" "failed"
    return 2
  }
  # The ledgers the app writes at startup (wsgi.py: data/ledger.db,
  # data/bozly_ledger.db): if one exists owned by someone else (e.g.
  # a root test run), hand it to the runtime user too. Ownership
  # only — data is never deleted or altered.
  for f in ledger.db bozly_ledger.db; do
    if [ -e "$DATA_DIR/$f" ]; then
      chown sanders:sanders "$DATA_DIR/$f" 2>/dev/null || true
    fi
  done
  record_event "$key" "P2" "$evidence" "mkdir -p + chown sanders:sanders $DATA_DIR (and ledger files if present)" "ok"
  if do_restart "$key"; then
    record_event "$key" "P2" "$evidence" "restart $(unit_for "$key")" "ok"
    return 0
  fi
  record_event "$key" "P2" "$evidence" "restart $(unit_for "$key")" "failed"
  return 2
}

port8000_holders() {
  ss -ltnp 2>/dev/null | grep -E ':8000[[:space:]]' | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true
}

repair_p3_port() {
  local key="$1" evidence="$2"
  local mainpid holders stale="" pid cmd
  mainpid="$(timeout 10 systemctl show -p MainPID --value "$APP_UNIT" 2>/dev/null || echo 0)"
  case "$mainpid" in ''|*[!0-9]*) mainpid=0 ;; esac
  holders="$(port8000_holders)"
  for pid in $holders; do
    if [ "$pid" != "$mainpid" ]; then stale="${stale} $pid"; fi
  done
  if [ -z "$stale" ]; then
    record_event "$key" "P3" "$evidence" "identify stale :8000 holders" "no stale holder found at repair time"
    return 2
  fi
  # Safety gate: kill ONLY gunicorn processes (see hard boundaries).
  for pid in $stale; do
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || echo '')"
    case "$cmd" in
      *gunicorn*) ;;
      *)
        record_event "$key" "P3" "$evidence" "kill stale holder pid $pid" "refused: holder is not a gunicorn process (cmdline: ${cmd:-unreadable}); escalating without touching it"
        return 2
        ;;
    esac
  done
  for pid in $stale; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  record_event "$key" "P3" "$evidence" "TERM stale gunicorn pid(s):$stale (unit MainPID $mainpid kept)" "sent"
  sleep 3
  local remaining=""
  for pid in $(port8000_holders); do
    if [ "$pid" != "$mainpid" ]; then remaining="${remaining} $pid"; fi
  done
  if [ -n "$remaining" ]; then
    for pid in $remaining; do
      kill -KILL "$pid" 2>/dev/null || true
    done
    record_event "$key" "P3" "$evidence" "KILL stale gunicorn pid(s) still holding :8000 after 3s:$remaining" "sent"
    sleep 1
  fi
  if do_restart "$key"; then
    record_event "$key" "P3" "$evidence" "restart $(unit_for "$key")" "ok"
    return 0
  fi
  record_event "$key" "P3" "$evidence" "restart $(unit_for "$key")" "failed"
  return 2
}

NGINX_SERVER_DST="/etc/nginx/conf.d/money_factory_legal_server.conf"
NGINX_SNIPPET_DST="/etc/nginx/snippets/money_factory_legal.conf"
NGINX_SRC_SERVER="money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal_server.conf"
NGINX_SRC_SNIPPET="money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal.conf"

# Install the two nginx files from a directory holding them under
# the repo-relative names (checkout) or the snapshot basenames
# (LKG). $2 is "checkout" or "lkg".
install_nginx_from() {
  local src_dir="$1" mode="$2"
  local server_src snippet_src
  if [ "$mode" = "lkg" ]; then
    server_src="$src_dir/money_factory_legal_server.conf"
    snippet_src="$src_dir/money_factory_legal.conf"
  else
    server_src="$src_dir/$NGINX_SRC_SERVER"
    snippet_src="$src_dir/$NGINX_SRC_SNIPPET"
  fi
  [ -f "$server_src" ] && [ -f "$snippet_src" ] || return 1
  mkdir -p /etc/nginx/conf.d /etc/nginx/snippets || return 1
  cp "$server_src" "$NGINX_SERVER_DST" || return 1
  cp "$snippet_src" "$NGINX_SNIPPET_DST" || return 1
  # Mirror deploy_all.sh: the /rtsa/status location must be present
  # in the installed snippet (deploy appends it when missing).
  if ! grep -q "/rtsa/status" "$NGINX_SNIPPET_DST"; then
    tee -a "$NGINX_SNIPPET_DST" >/dev/null <<'RTSA_LOC'

location = /rtsa/status {
    default_type application/json;
    alias /var/www/rtsa/status.json;
}
RTSA_LOC
  fi
  return 0
}

newest_lkg() {
  ls -1dt "$LKG_BASE"/*/ 2>/dev/null | head -n 1 | sed 's:/$::'
}

# Verify one snapshot file against the snapshot's MANIFEST.txt.
lkg_verify() {
  local dir="$1" name="$2" expected actual
  [ -f "$dir/$name" ] && [ -f "$dir/MANIFEST.txt" ] || return 1
  expected="$(awk -v n="$name" '{f=$2; sub(/^\*/,"",f); if (f==n) print $1}' "$dir/MANIFEST.txt" | head -n 1)"
  [ -n "$expected" ] || return 1
  actual="$(sha256sum "$dir/$name" 2>/dev/null | awk '{print $1}')"
  [ "$expected" = "$actual" ]
}

repair_p4_nginx() {
  local key="$1" evidence="$2"
  local backup_dir lkg
  backup_dir="$(mktemp -d /tmp/sds-repair-nginx.XXXXXX)" || return 2
  [ -f "$NGINX_SERVER_DST" ] && cp "$NGINX_SERVER_DST" "$backup_dir/server.conf" 2>/dev/null || true
  [ -f "$NGINX_SNIPPET_DST" ] && cp "$NGINX_SNIPPET_DST" "$backup_dir/snippet.conf" 2>/dev/null || true

  # Source 1: the repo checkout (what deploy_all.sh installs).
  if install_nginx_from "$REPO_DIR" "checkout"; then
    if nginx -t >/dev/null 2>&1; then
      record_event "$key" "P4" "$evidence" "reinstall nginx server conf + snippet from repo checkout; nginx -t" "ok"
      if do_restart "$key"; then
        record_event "$key" "P4" "$evidence" "restart nginx.service" "ok"
        rm -rf "$backup_dir" 2>/dev/null || true
        return 0
      fi
      record_event "$key" "P4" "$evidence" "restart nginx.service" "failed"
      rm -rf "$backup_dir" 2>/dev/null || true
      return 2
    fi
    record_event "$key" "P4" "$evidence" "reinstall nginx conf from repo checkout; nginx -t" "failed: checkout config does not pass nginx -t; trying last-known-good"
  else
    record_event "$key" "P4" "$evidence" "reinstall nginx conf from repo checkout" "unavailable: checkout copies missing; trying last-known-good"
  fi

  # Source 2: the newest last-known-good snapshot (hash-verified).
  lkg="$(newest_lkg)"
  if [ -n "$lkg" ] && lkg_verify "$lkg" "money_factory_legal_server.conf" && lkg_verify "$lkg" "money_factory_legal.conf"; then
    if install_nginx_from "$lkg" "lkg" && nginx -t >/dev/null 2>&1; then
      record_event "$key" "P4" "$evidence" "restore nginx server conf + snippet from LKG snapshot $lkg (sha256 verified); nginx -t" "ok"
      if do_restart "$key"; then
        record_event "$key" "P4" "$evidence" "restart nginx.service" "ok"
        rm -rf "$backup_dir" 2>/dev/null || true
        return 0
      fi
      record_event "$key" "P4" "$evidence" "restart nginx.service" "failed"
      rm -rf "$backup_dir" 2>/dev/null || true
      return 2
    fi
    record_event "$key" "P4" "$evidence" "restore nginx conf from LKG snapshot $lkg; nginx -t" "failed"
  else
    record_event "$key" "P4" "$evidence" "restore nginx conf from LKG snapshot" "unavailable: no snapshot, or snapshot files missing/hash mismatch"
  fi

  # Neither source produced a valid config: put the previously
  # installed files back and do NOT restart nginx into a bad config.
  [ -f "$backup_dir/server.conf" ] && cp "$backup_dir/server.conf" "$NGINX_SERVER_DST" 2>/dev/null || true
  [ -f "$backup_dir/snippet.conf" ] && cp "$backup_dir/snippet.conf" "$NGINX_SNIPPET_DST" 2>/dev/null || true
  rm -rf "$backup_dir" 2>/dev/null || true
  record_event "$key" "P4" "$evidence" "restore previously installed nginx files; no restart" "escalated: neither checkout nor LKG config passes nginx -t"
  return 2
}

repair_p6_parked() {
  local key="$1" evidence="$2"
  do_reset_failed "$key"
  record_event "$key" "P6" "$evidence" "reset-failed $(unit_for "$key")" "ok"
  if do_restart "$key"; then
    record_event "$key" "P6" "$evidence" "restart $(unit_for "$key")" "ok"
    return 0
  fi
  record_event "$key" "P6" "$evidence" "restart $(unit_for "$key")" "failed"
  return 2
}

# ------------------------------------------------------------------
# classification
# ------------------------------------------------------------------

# Prints "<class>|<evidence>" for the service, or "UNKNOWN|<evidence>".
classify() {
  local key="$1"
  local state journal exceptions
  state="$(unit_state "$key")"
  journal="$(unit_journal "$key")"
  exceptions="$(journal_exceptions "$journal")"

  case "$key" in
    app)
      # P1 env
      if [ ! -f "$RUNTIME_ENV" ]; then
        printf 'P1|%s' "runtime.env missing; unit state $state; journal: $exceptions"
        return 0
      fi
      if ! grep -Eq "$ENV_SHAPE_RE" "$RUNTIME_ENV" 2>/dev/null; then
        printf 'P1|%s' "runtime.env present but STRIPE_WEBHOOK_SECRET not whsec_-shaped; unit state $state; journal: $exceptions"
        return 0
      fi
      # P2 datadir
      local owner=""
      if [ -d "$DATA_DIR" ]; then owner="$(stat -c '%U' "$DATA_DIR" 2>/dev/null || echo '?')"; fi
      if printf '%s' "$journal" | grep -Eiq 'permissionerror|permission denied|mkdir'; then
        printf 'P2|%s' "journal shows a permission/mkdir failure at data_dir; journal: $exceptions"
        return 0
      fi
      if [ ! -d "$DATA_DIR" ]; then
        printf 'P2|%s' "$DATA_DIR missing; unit state $state; journal: $exceptions"
        return 0
      fi
      if [ "$owner" != "sanders" ]; then
        printf 'P2|%s' "$DATA_DIR owned by '$owner', not sanders; unit state $state; journal: $exceptions"
        return 0
      fi
      # P3 port
      local mainpid holders stale="" pid
      mainpid="$(timeout 10 systemctl show -p MainPID --value "$APP_UNIT" 2>/dev/null || echo 0)"
      case "$mainpid" in ''|*[!0-9]*) mainpid=0 ;; esac
      holders="$(port8000_holders)"
      for pid in $holders; do
        if [ "$pid" != "$mainpid" ]; then stale="${stale} $pid"; fi
      done
      if [ -n "$stale" ]; then
        printf 'P3|%s' "port 8000 held by non-unit pid(s):$stale (unit MainPID $mainpid); unit state $state"
        return 0
      fi
      # P6 parked (only after P1–P3 are excluded)
      if [ "$state" = "failed" ]; then
        printf 'P6|%s' "app unit in failed state; journal: $exceptions"
        return 0
      fi
      printf 'UNKNOWN|%s' "unit state $state; env shape ok; data dir ok; no stale :8000 holder; journal: $exceptions"
      ;;
    nginx)
      local t_out=""
      t_out="$(nginx -t 2>&1 | tr '\n' ';' | cut -c1-160 || true)"
      if ! nginx -t >/dev/null 2>&1; then
        printf 'P4|%s' "nginx -t fails: $t_out; unit state $state"
        return 0
      fi
      if ! nginx_listeners_ok; then
        printf 'P4|%s' "nginx not listening on 80 and/or 443; unit state $state; journal: $exceptions"
        return 0
      fi
      if [ "$state" = "failed" ]; then
        printf 'P6|%s' "nginx unit in failed state; journal: $exceptions"
        return 0
      fi
      printf 'UNKNOWN|%s' "unit state $state; nginx -t ok; listeners ok; journal: $exceptions"
      ;;
    *)
      # money-factory, secretary, twostep, judge: the generic entry
      # is P6. The start-limit signature is recorded when the
      # journal is observable; for the opc --user units the journal
      # is the flakiest evidence source, so a failed state alone is
      # sufficient — reset-failed is the precise recovery for a
      # parked unit and a no-op for a merely failed one.
      if [ "$state" = "failed" ]; then
        local sig="no start-limit signature observed"
        if printf '%s' "$journal" | grep -Eiq 'start request repeated too quickly|start-limit'; then
          sig="start-limit signature in journal"
        fi
        printf 'P6|%s' "unit in failed state ($sig); journal: $exceptions"
        return 0
      fi
      printf 'UNKNOWN|%s' "unit state $state (not failed); journal: $exceptions"
      ;;
  esac
}

# ------------------------------------------------------------------
# manual entry points
# ------------------------------------------------------------------

run_gitperms() {
  local gitdir="$REPO_DIR/.git"
  if [ ! -d "$gitdir" ]; then
    record_event "checkout" "P5" "$gitdir not present" "chown -R opc:opc $gitdir" "escalated: nothing to repair"
    exit 2
  fi
  local bad=""
  bad="$(find "$gitdir" -not -user "$USER_SERVICES_OWNER" -print -quit 2>/dev/null || true)"
  if [ -z "$bad" ]; then
    record_event "checkout" "P5" "$gitdir already fully owned by $USER_SERVICES_OWNER" "none" "already-ok"
    exit 0
  fi
  record_event "checkout" "P5" "entries under $gitdir not owned by $USER_SERVICES_OWNER (first: $bad) — the deploy sync failure signature (deploy_all run #100)" "chown -R ${USER_SERVICES_OWNER}:${USER_SERVICES_OWNER} $gitdir" "started"
  if chown -R "${USER_SERVICES_OWNER}:${USER_SERVICES_OWNER}" "$gitdir" 2>/dev/null; then
    bad="$(find "$gitdir" -not -user "$USER_SERVICES_OWNER" -print -quit 2>/dev/null || true)"
    if [ -z "$bad" ]; then
      record_event "checkout" "P5" "ownership re-verified" "chown -R ${USER_SERVICES_OWNER}:${USER_SERVICES_OWNER} $gitdir" "ok"
      exit 0
    fi
  fi
  record_event "checkout" "P5" "ownership still wrong after chown (first bad: ${bad:-unknown})" "chown -R ${USER_SERVICES_OWNER}:${USER_SERVICES_OWNER} $gitdir" "failed; escalating"
  exit 2
}

run_restore_lkg() {
  local what="${1:-}"
  local lkg
  lkg="$(newest_lkg)"
  if [ -z "$lkg" ]; then
    record_event "lkg" "LKG" "no snapshot under $LKG_BASE" "restore-lkg $what" "escalated: no last-known-good snapshot exists yet (snapshots are taken by deploy_all.sh after a passing health check)"
    exit 2
  fi
  case "$what" in
    nginx)
      if lkg_verify "$lkg" "money_factory_legal_server.conf" && lkg_verify "$lkg" "money_factory_legal.conf" && install_nginx_from "$lkg" "lkg" && nginx -t >/dev/null 2>&1; then
        record_event "nginx" "LKG" "snapshot $lkg (sha256 verified against MANIFEST.txt)" "restore nginx server conf + snippet from LKG; nginx -t ok" "ok"
        if do_restart "nginx"; then
          record_event "nginx" "LKG" "snapshot $lkg" "restart nginx.service" "ok"
          exit 0
        fi
        record_event "nginx" "LKG" "snapshot $lkg" "restart nginx.service" "failed"
        exit 2
      fi
      record_event "nginx" "LKG" "snapshot $lkg" "restore nginx conf from LKG" "failed: hash mismatch, missing files, or nginx -t failed; escalating"
      exit 2
      ;;
    app)
      if lkg_verify "$lkg" "sanders-dash-seal.service" && cp "$lkg/sanders-dash-seal.service" /etc/systemd/system/sanders-dash-seal.service 2>/dev/null; then
        timeout 15 systemctl daemon-reload 2>/dev/null || true
        record_event "app" "LKG" "snapshot $lkg (sha256 verified)" "restore app unit file from LKG; daemon-reload" "ok"
        if do_restart "app"; then
          record_event "app" "LKG" "snapshot $lkg" "restart sanders-dash-seal.service" "ok"
          exit 0
        fi
        record_event "app" "LKG" "snapshot $lkg" "restart sanders-dash-seal.service" "failed"
        exit 2
      fi
      record_event "app" "LKG" "snapshot $lkg" "restore app unit file from LKG" "failed: hash mismatch or copy failed; escalating"
      exit 2
      ;;
    env)
      # Restores the byte-for-byte runtime.env that a passing deploy
      # verified working. This is not creating, rotating, or
      # guessing a secret — it is putting back the owner's own file
      # from a root-only snapshot (see hard boundaries).
      if lkg_verify "$lkg" "runtime.env" && install -m 0600 -o root -g root "$lkg/runtime.env" "$RUNTIME_ENV" 2>/dev/null; then
        record_event "app" "LKG" "snapshot $lkg (sha256 verified); runtime.env restored root:root 0600; value never read or printed" "restore runtime.env from LKG" "ok"
        if do_restart "app"; then
          record_event "app" "LKG" "snapshot $lkg" "restart sanders-dash-seal.service" "ok"
          exit 0
        fi
        record_event "app" "LKG" "snapshot $lkg" "restart sanders-dash-seal.service" "failed"
        exit 2
      fi
      record_event "app" "LKG" "snapshot $lkg" "restore runtime.env from LKG" "failed: no runtime.env in snapshot or hash mismatch; escalating"
      exit 2
      ;;
    watchdog)
      local f ok=1
      for f in sds_watchdog.sh sds_repair.sh sds_env_guard.sh; do
        if lkg_verify "$lkg" "$f"; then
          install -m 0755 "$lkg/$f" "/usr/local/sbin/$f" 2>/dev/null || ok=0
        fi
      done
      if [ "$ok" = "1" ]; then
        record_event "watchdog" "LKG" "snapshot $lkg (sha256 verified per file)" "restore watchdog/repair/env-guard scripts to /usr/local/sbin (0755)" "ok"
        exit 0
      fi
      record_event "watchdog" "LKG" "snapshot $lkg" "restore watchdog scripts from LKG" "failed; escalating"
      exit 2
      ;;
    *)
      log_msg "usage: sds_repair.sh restore-lkg <nginx|app|env|watchdog>"
      exit 1
      ;;
  esac
}

# ------------------------------------------------------------------
# main repair flow
# ------------------------------------------------------------------

run_repair() {
  local key="$1"
  unit_for "$key" >/dev/null || { log_msg "unknown service key: $key"; exit 1; }

  # Incident already over? (The watchdog normally clears the
  # counter; this also makes manual runs safe.)
  if svc_health "$key"; then
    clear_attempts "$key"
    record_event "$key" "NONE" "health check passes at repair entry" "none" "already-healthy; incident closed, attempt counter cleared"
    exit 0
  fi

  local attempts
  attempts="$(read_attempts "$key")"
  if [ "$attempts" -ge "$MAX_ATTEMPTS" ]; then
    record_event "$key" "CAP" "repair attempt cap reached ($attempts/$MAX_ATTEMPTS this incident) and the service is still down" "none" "escalated: no further automatic repair this incident; owner attention required"
    exit 2
  fi

  local classified class evidence
  classified="$(classify "$key")"
  class="${classified%%|*}"
  evidence="${classified#*|}"

  if [ "$class" = "UNKNOWN" ]; then
    record_event "$key" "UNKNOWN" "$evidence" "none" "escalated: no playbook signature matched; no mutation made"
    exit 2
  fi

  # The attempt is counted BEFORE any mutation (see header).
  local n
  n="$(bump_attempts "$key")"
  record_event "$key" "$class" "$evidence" "classify (repair attempt $n/$MAX_ATTEMPTS this incident)" "classified"

  local rc=0
  case "$class" in
    P1) repair_p1_env "$key" "$evidence" || rc=$? ;;
    P2) repair_p2_datadir "$key" "$evidence" || rc=$? ;;
    P3) repair_p3_port "$key" "$evidence" || rc=$? ;;
    P4) repair_p4_nginx "$key" "$evidence" || rc=$? ;;
    P6) repair_p6_parked "$key" "$evidence" || rc=$? ;;
    *) record_event "$key" "$class" "$evidence" "dispatch" "escalated: class has no repair implementation"; rc=2 ;;
  esac

  # Post-repair verification (bounded): give the service a moment,
  # then check once. The watchdog keeps verifying over its rounds.
  sleep 5
  if svc_health "$key"; then
    clear_attempts "$key"
    record_event "$key" "$class" "$evidence" "post-repair health check" "recovered; incident closed, attempt counter cleared"
    exit 0
  fi
  record_event "$key" "$class" "$evidence" "post-repair health check" "still down after repair attempt $n/$MAX_ATTEMPTS"
  if [ "$rc" != "0" ]; then
    exit 2
  fi
  exit 0
}

main() {
  if [ "$(id -u)" != "0" ]; then
    log_msg "ERROR: sds_repair.sh must run as root (it restarts services and repairs root-owned files)"
    exit 1
  fi
  if ! mkdir -p "$STATE_DIR" 2>/dev/null; then
    STATE_DIR="/run/sds-watchdog"
    if ! mkdir -p "$STATE_DIR" 2>/dev/null; then
      log_msg "ERROR: cannot create a state directory (/var/lib/sds-watchdog or /run/sds-watchdog); repair misconfigured"
      exit 1
    fi
  fi
  if ! mkdir -p "$REPAIR_DIR" 2>/dev/null; then
    log_msg "ERROR: cannot create $REPAIR_DIR for the incident log; repair misconfigured"
    exit 1
  fi
  chmod 0700 "$REPAIR_DIR" 2>/dev/null || true
  if [ ! -f "$INCIDENTS" ]; then
    touch "$INCIDENTS" 2>/dev/null || true
  fi
  chmod 0600 "$INCIDENTS" 2>/dev/null || true
  if ! command -v curl >/dev/null 2>&1; then
    log_msg "ERROR: curl not found; the repair playbook cannot health-check (misconfigured)"
    exit 1
  fi

  case "${1:-}" in
    gitperms) run_gitperms ;;
    restore-lkg) run_restore_lkg "${2:-}" ;;
    app|money-factory|secretary|twostep|judge|nginx) run_repair "$1" ;;
    *)
      log_msg "usage: sds_repair.sh <app|money-factory|secretary|twostep|judge|nginx|gitperms|restore-lkg <nginx|app|env|watchdog>>"
      exit 1
      ;;
  esac
}

main "$@"
