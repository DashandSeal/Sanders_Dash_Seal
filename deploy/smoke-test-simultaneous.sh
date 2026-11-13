#!/usr/bin/env bash
# Sanders Dash & Seal — SIMULTANEOUS smoke test (2026-11-13).
#
# Tests the packaged app LOCALLY — against a local gunicorn + nginx run,
# never against the Oracle instance (129.146.111.166). No live Claude,
# no live Stripe, no money, no secrets.
#
# Usage:
#   bash smoke-test-simultaneous.sh [APP_DIR]
# APP_DIR is the app root (contains wsgi.py); default is
# /opt/sanders-dash-seal if it exists, else the staging src next to
# this script (~/workspace/deploy-simultaneous-20261113/staging/src).
# The nginx config tested is the packaged deploy/nginx.conf (tripwires
# REMOVED), adapted only by port: gunicorn 127.0.0.1:18000, nginx :18080.
#
# Checks (each prints PASS/FAIL with the real status code):
#   1. nginx -t PASS
#   2. homepage GET / -> 200 (via nginx)
#   3. /healthz -> 200 (via nginx)
#   4. /api/voice/status -> 200 (via nginx)
#   5. Daedalus chain with fake transport -> source sha256 matches
#      sha256("print('hello')\n") (in-process, mocked urlopen, fake key/model)
#   6. webhook unsigned POST -> 401 (via nginx; gunicorn runs with a
#      TEST-ONLY whsec_ secret generated for this run, never stored)
#   7. webhook signed test event -> 200 LEDGER_SETTLED (via nginx)
#   8. /voice.html -> 200 (via nginx)
#   9. /api/daedalus/describe -> 200, fully_active=false (via nginx)
# Exit 0 only if every check passes.
set -u
APP_DIR="${1:-}"
if [[ -z "$APP_DIR" ]]; then
  if [[ -f /opt/sanders-dash-seal/wsgi.py ]]; then APP_DIR=/opt/sanders-dash-seal;
  elif [[ -f "$(dirname "$0")/staging/src/wsgi.py" ]]; then APP_DIR="$(cd "$(dirname "$0")/staging/src" && pwd)";
  else echo "ERROR: pass APP_DIR (directory containing wsgi.py)." >&2; exit 2; fi
fi
[[ -f "$APP_DIR/wsgi.py" ]] || { echo "ERROR: no wsgi.py in $APP_DIR" >&2; exit 2; }
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
# nginx.conf locations, in order: staging tree (local dev), extracted
# tarball layout (PKG_DIR/deploy), installed app (/opt/.../deploy).
for _cand in "$PKG_DIR/staging/deploy/nginx.conf" "$PKG_DIR/deploy/nginx.conf" "$APP_DIR/deploy/nginx.conf" "$APP_DIR/../deploy/nginx.conf"; do
  if [[ -f "$_cand" ]]; then NGINX_SRC="$_cand"; break; fi
done
[[ -n "${NGINX_SRC:-}" && -f "$NGINX_SRC" ]] || { echo "ERROR: packaged nginx.conf not found." >&2; exit 2; }
echo "nginx config under test: $NGINX_SRC"

GPORT=18000; NPORT=18080
TMP=$(mktemp -d "${TMPDIR:-/tmp}/sds-simultaneous-smoke.XXXXXX")
VENV="$TMP/venv"; LOG="$TMP/smoke.log"
FAILURES=0
check() { # check <name> <expected-code-or-true> <actual>
  local name="$1" want="$2" got="$3"
  if [[ "$got" == "$want" ]]; then echo "PASS $name — $got";
  else echo "FAIL $name — expected $want, got $got"; FAILURES=$((FAILURES+1)); fi
}
cleanup() {
  [[ -n "${GUNICORN_PID:-}" ]] && kill "$GUNICORN_PID" 2>/dev/null || true
  [[ -f "$TMP/nginx.pid" ]] && kill "$(cat "$TMP/nginx.pid" 2>/dev/null)" 2>/dev/null || true
  sleep 1; rm -rf "$TMP"
}
trap cleanup EXIT

echo "== simultaneous smoke test =="
echo "APP_DIR=$APP_DIR  TMP=$TMP"
python3.12 -m venv "$VENV" >/dev/null 2>&1 || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
echo "venv ready: $("$VENV/bin/pip" list 2>/dev/null | grep -i -E 'stripe|gunicorn' | tr '\n' ' ')"

# --- test nginx config: packaged file, ports only ---------------------------
mkdir -p "$TMP/nginx/client_body_temp" "$TMP/nginx/proxy_temp" "$TMP/nginx/fastcgi_temp" "$TMP/nginx/uwsgi_temp" "$TMP/nginx/scgi_temp" "$TMP/logs" "$TMP/nginx/logs"
MIME=/etc/nginx/mime.types
[[ -f "$MIME" ]] || MIME=/usr/share/nginx/mime.types
[[ -f "$MIME" ]] || MIME=/opt/homebrew/etc/nginx/mime.types
sed -e "s/listen 80 default_server;/listen $NPORT default_server;/" \
    -e "s|server 127.0.0.1:8000;|server 127.0.0.1:$GPORT;|" \
    -e "s|include       mime.types;|include $MIME;|" \
    "$NGINX_SRC" > "$TMP/nginx.conf"
sed -i "s|pid .*;|pid $TMP/nginx.pid;|" "$TMP/nginx.conf" 2>/dev/null || true
grep -q "pid " "$TMP/nginx.conf" || sed -i "1i pid $TMP/nginx.pid;" "$TMP/nginx.conf"
# nginx needs an error_log path writable in the temp prefix
sed -i "1i error_log $TMP/logs/error.log;" "$TMP/nginx.conf"

if nginx -t -c "$TMP/nginx.conf" -p "$TMP/nginx/" >"$TMP/nginx-t.log" 2>&1; then
  echo "PASS nginx -t — syntax ok"
else
  echo "FAIL nginx -t"; cat "$TMP/nginx-t.log"; FAILURES=$((FAILURES+1))
fi

# --- start gunicorn with a TEST-ONLY webhook secret --------------------------
# whsec_ value below is a test-only placeholder for this run, never a real secret.
export STRIPE_WEBHOOK_SECRET='whsec_c2ltdWxhdGVkX3Rlc3Rfc2VjcmV0X25vdF9yZWFs'
export STRIPE_LIVEMODE=false
unset ANTHROPIC_API_KEY DAEDALUS_CLAUDE_MODEL
cd "$APP_DIR"
"$VENV/bin/gunicorn" --bind "127.0.0.1:$GPORT" --workers 1 --threads 2 --timeout 30 wsgi:application >"$TMP/gunicorn.log" 2>&1 &
GUNICORN_PID=$!
# wait for gunicorn
for _ in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:$GPORT/healthz" && break; sleep 0.5; done
nginx -c "$TMP/nginx.conf" -p "$TMP/nginx/" -g 'daemon on;' >>"$TMP/nginx-t.log" 2>&1 || { echo "FAIL nginx start"; cat "$TMP/nginx-t.log"; }
sleep 1
code() { curl -s -o /dev/null -w '%{http_code}' "$1" "${@:2}"; }

check "homepage GET / -> 200 (nginx :$NPORT)" 200 "$(code "http://127.0.0.1:$NPORT/")"
check "/healthz -> 200 (nginx)" 200 "$(code "http://127.0.0.1:$NPORT/healthz")"
check "/api/voice/status -> 200 (nginx)" 200 "$(code "http://127.0.0.1:$NPORT/api/voice/status")"
check "/voice.html -> 200 (nginx)" 200 "$(code "http://127.0.0.1:$NPORT/voice.html")"
BODY=$(curl -s "http://127.0.0.1:$NPORT/api/daedalus/describe")
if echo "$BODY" | grep -q '"fully_active":false'; then echo "PASS /api/daedalus/describe -> 200 fully_active=false";
else echo "FAIL /api/daedalus/describe — $BODY"; FAILURES=$((FAILURES+1)); fi
check "webhook unsigned POST -> 401 (nginx)" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:$NPORT/v1/payments/stripe/webhook")"

# signed test event -> 200 LEDGER_SETTLED (stripe lib in the test venv)
export EVT_ID="evt_smoke_simultaneous_$(date +%s)_$$"
SIGNED=$("$VENV/bin/python" - "$NPORT" <<'PYEOF'
import json, os, sys, time
import hashlib, hmac
payload = json.dumps({"id": os.environ.get("EVT_ID", "evt_smoke_simultaneous_1"), "type": "checkout.session.completed",
                      "livemode": False, "data": {"object": {"id": "cs_test"}}},
                     separators=(",", ":")).encode()
secret = "whsec_c2ltdWxhdGVkX3Rlc3Rfc2VjcmV0X25vdF9yZWFs"
_ts = int(time.time())
sig = hmac.new(secret.encode(), f"{_ts}.".encode() + payload, hashlib.sha256).hexdigest()
import urllib.request
req = urllib.request.Request(f"http://127.0.0.1:{sys.argv[1]}/v1/payments/stripe/webhook",
                             data=payload, method="POST",
                             headers={"Content-Type": "application/json",
                                      "Stripe-Signature": f"t={_ts},v1={sig}"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
PYEOF
)
echo "signed webhook response: $SIGNED"
if echo "$SIGNED" | grep -q "^200 .*LEDGER_SETTLED"; then echo "PASS webhook signed test event -> 200 LEDGER_SETTLED";
else echo "FAIL webhook signed test event — $SIGNED"; FAILURES=$((FAILURES+1)); fi

# --- Daedalus chain with fake transport (in-process, no network) -------------
"$VENV/bin/python" - "$APP_DIR" <<'PYEOF' >"$TMP/daedalus.log" 2>&1
import hashlib, json, sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
from core_platform.daedalus_engine import build_context, build_engine, DaedalusEngineConfig
from core_platform.daedalus_geofence import LocationAttestation

class FakeResp:
    def __init__(self, body): self._b = json.dumps(body).encode(); self.headers = {"request-id": "req-test-1"}
    def read(self, n=-1): return self._b
    def __enter__(self): return self
    def __exit__(self, *e): return False

def fake_open(req, timeout=None, context=None):
    body = {"type": "message", "id": "msg-test-1", "model": "claude-test-model",
            "content": [{"type": "text", "text": "print('"}, {"type": "text", "text": "hello')\n"}],
            "usage": {"input_tokens": 12, "output_tokens": 8}}
    return FakeResp(body)

cfg = DaedalusEngineConfig(signing_key=b"k" * 32,
                           persist_private_evidence=lambda r, s: None,
                           persist_confidential=lambda a, r, s: None,
                           audit=lambda e: None,
                           model="claude-test-model", api_key="test-key-not-real")
eng = build_engine(cfg)
ctx = build_context(operation_id="op-1", platform_id="p", subsystem_id="s",
                    invention_id="inv-1", subject_id="subj-1",
                    location=LocationAttestation(country="US", region="us-az",
                                                 cloud_region="us-phoenix-1",
                                                 source="trusted-attestor", trusted=True))
with mock.patch("urllib.request.urlopen", fake_open):
    out = eng.execute(ctx, "hello", title="t", inventor_assertions=())
want = hashlib.sha256(b"print('hello')\n").hexdigest()
assert out["engine"] == "DAEDALUS", out
assert out["source_sha256"] == want, (out, want)
print("DAEDALUS_CHAIN_OK", out["source_sha256"])
PYEOF
if grep -q DAEDALUS_CHAIN_OK "$TMP/daedalus.log"; then
  echo "PASS Daedalus chain (fake transport) — $(grep DAEDALUS_CHAIN_OK "$TMP/daedalus.log")"
else
  echo "FAIL Daedalus chain (fake transport)"; cat "$TMP/daedalus.log"; FAILURES=$((FAILURES+1))
fi

echo
if [[ "$FAILURES" -gt 0 ]]; then echo "SMOKE TEST: $FAILURES check(s) FAILED"; echo "logs in $TMP (kept on failure path only if trap did not clean — see gunicorn/nginx logs above)"; exit 1; fi
echo "SMOKE TEST: ALL CHECKS PASSED"
