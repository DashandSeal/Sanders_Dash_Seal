#!/bin/bash
# Install the complete bundled application on a fresh OL9 node.
set -Eeuo pipefail
trap 'result=$?; echo "APPLICATION_INSTALL_FAILED exit=$result" >&2; exit "$result"' ERR
[[ "$EUID" == 0 ]]
source /etc/os-release
[[ "$ID" == ol && "$VERSION_ID" == 9* ]]
dnf install -y git python3 curl firewalld tar iproute util-linux dnf-plugins-core oraclelinux-developer-release-el9
dnf install -y python39-oci-cli
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker firewalld
interface=$(ip -4 route show default | awk 'NR==1 {for(i=1;i<=NF;i++)if($i=="dev"){print $(i+1);exit}}')
[[ -n "$interface" ]]
zone=$(firewall-cmd --get-zone-of-interface="$interface" || true)
if [[ -z "$zone" || "$zone" == 'no zone' ]]; then
    zone=$(firewall-cmd --get-default-zone)
    firewall-cmd --zone="$zone" --change-interface="$interface"
    firewall-cmd --permanent --zone="$zone" --change-interface="$interface"
fi
install -d -m 0700 /var/lib/sanders-dash-seal
# OCI IAM propagation can take time; download only the named private object.
python3 /usr/local/sbin/sds-fetch-release /etc/sanders-dash-seal/release.json
source_dir=$(python3 -c 'import json; c=json.load(open("/etc/sanders-dash-seal/release.json")); print("/opt/sds-approved-source-"+c["commit"])')
export SDS_SOURCE_DIR="$source_dir"
commit=$(python3 -c 'import json;print(json.load(open("/etc/sanders-dash-seal/release.json"))["commit"])')
python3 "$source_dir/scripts/verify_release_source.py" "$source_dir" "$commit"
source "$source_dir/deploy.sh"
check_source "$source_dir"
check_host
configure_firewall
stage_authorized_source "$source_dir" "$commit"
# Regressions use an isolated project, no production volumes, ports or secrets.
bash "$source_dir/run_preflight_checks.sh" --commit "$commit"
install -d -m 0755 "$SDS_STATE_DIR/public"
compose config --quiet
compose build pipeline-worker wsgi-backend
if [[ ! -s "$SDS_STATE_DIR/nginx.active.conf" ]]; then
    install -m 0644 "$SDS_PROJECT_DIR/deploy/nginx.http.conf" "$SDS_STATE_DIR/nginx.active.conf"
fi
# Preserve the supplied TLS configuration; active configuration transitions only
# after genuine ACME issuance. HTTP exposes public assets and health, no secrets.
compose up -d pipeline-worker wsgi-backend reverse-proxy
compose exec -T wsgi-backend python -c "import os,sqlite3;from core_platform.pipeline_api import TransactionStore; p=os.environ['SQLITE_DB_PATH'];TransactionStore(p); db=sqlite3.connect(p);assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';db.close()"
for attempt in {1..30}; do
    if compose exec -T wsgi-backend python -c "import urllib.request;urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/healthz',headers={'Host':'sandersdashandseal.com'}),timeout=3)" && compose exec -T pipeline-worker node -e 'require("http").get("http://127.0.0.1:3000/health",r=>{r.resume();process.exitCode=r.statusCode===200?0:1}).on("error",()=>process.exit(1))'; then break; fi
    (( attempt < 30 ))
    sleep 2
done
compose exec -T reverse-proxy nginx -t
python3 - <<'INVENTORY'
import json,urllib.request
from pathlib import Path
cfg=json.loads(Path('/etc/sanders-dash-seal/release.json').read_text())
req=urllib.request.Request('http://169.254.169.254/opc/v2/instance/',headers={'Authorization':'Bearer Oracle'})
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(req,timeout=5) as response: instance=json.loads(response.read(65536))
record={'schema':1,'tenancy_id':cfg['tenancy_id'],'compartment_id':cfg['compartment_id'],
 'home_region':'us-phoenix-1','expected':[{'identifier':instance['id'],'resource_type':'Instance',
 'region':'us-phoenix-1','compartment_id':cfg['compartment_id'],'allowed_states':['RUNNING']}]}
p=Path('/etc/sanders-dash-seal/inventory.json');p.write_text(json.dumps(record));p.chmod(0o600)
INVENTORY
install_monitors
python3 - <<'BIND'
import json,urllib.request
from pathlib import Path
config=json.loads(Path('/etc/sanders-dash-seal/release.json').read_text())
if config.get('resources'):
    resource=config['resources']
    request=urllib.request.Request('http://169.254.169.254/opc/v2/instance/id',headers={'Authorization':'Bearer Oracle'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=5) as response:
        identity=response.read(1024).decode().strip()
    if resource.get('instance_id') and resource['instance_id'] != identity:
        raise SystemExit('Resource binding belongs to a different VM')
    resource['instance_id']=identity
    destination=Path('/etc/sanders-dash-seal/resources.json')
    destination.write_text(json.dumps(resource));destination.chmod(0o600)
BIND
if [[ -f /etc/sanders-dash-seal/resources.json ]]; then
    python3 "$SDS_PROJECT_DIR/deploy/bind_free_resources.py" --install --backup
fi
install -m 0644 "$SDS_PROJECT_DIR/deploy/systemd/sanders-tls-activate.service" /etc/systemd/system/
install -m 0644 "$SDS_PROJECT_DIR/deploy/systemd/sanders-tls-activate.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sanders-tls-activate.timer
# TLS waits for actual DNS ownership/routing. It never substitutes a self-signed certificate.
systemctl start sanders-tls-activate.service || echo 'TLS_PENDING_DNS: see sanders-tls-activate journal.'
python3 - "$SDS_STATE_DIR/public/release-status.json" "$commit" <<'STATUS'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'platform':'Sanders Dash & Seal','commit':sys.argv[2],
    'application_installed':True,'started_services':['nginx','node','python','sqlite'],
    'business_integrations_verified':False})+'\n')
STATUS
echo 'APPLICATION_INSTALLED: Node, Python, SQLite and Nginx started; review /readyz for business integration readiness.'
