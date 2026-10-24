"""Separate read-only role processes and verifiable operational observations.

Observation signatures never authorize execution or substitute for Twin-Gate,
Quality attestations, Vault leases, model inference or the complete MASTER AI.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import tempfile
import threading
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .security import canonical, public_hex, sign, verify, Denied
from .operational_runtime import AGENTS, observation, validated, readonly_database
from .operational_probes import configured_probes, source_probe
from .glass_box_audit import GlassBoxAudit
from .upgrade_sidecar import CORE_LAWS
from .rtsa_registry import RTSA_ROLES
from .rtsa_assessments import assess
from .local_inference import strict_json


DOMAIN = 'sds-readonly-role-observation-v1'
ROLE_PROBES = dict(AGENTS)
SHIELD = 'Sanders Labyrinth Shield 🛡️'
CONDUCTOR = 'MICHAEL ANGELO #49'
ROLES = tuple(ROLE_PROBES) + ('IT_AI_Manager_v15.0',) + tuple(RTSA_ROLES) + (
    'GlobalPBDSentinel', 'SandersSyntheticAISidecar', CONDUCTOR)
LAW_HASH = hashlib.sha256(canonical(list(CORE_LAWS))).hexdigest()


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise ValueError('Bounded regular role record required')
    return strict_json(path.read_text())


def check_record(record, role, key, now, *, freshness=90):
    if role not in ROLES or not isinstance(record, dict) or set(record) != {'body','signature'}:
        raise ValueError('Invalid role observation')
    body = record['body']
    if (not isinstance(body,dict) or set(body) != {'schema','platform','role','sequence',
            'observed_at','observation','laws_sha256','mode'}
            or body['schema'] != 1 or body['platform'] != 'Sanders Dash & Seal'
            or body['role'] != role or body['mode'] != 'READ_ONLY_OBSERVATION'
            or body['laws_sha256'] != LAW_HASH
            or type(body['sequence']) is not int or body['sequence'] < 1
            or type(body['observed_at']) not in (int,float)
            or not math.isfinite(body['observed_at'])
            or body['observed_at'] > now or now-body['observed_at'] > freshness):
        raise ValueError('Invalid, future or stale role observation')
    validated(body['observation'])
    verify(key,record['signature'],DOMAIN,body)
    return body


def protected_identity(path, role):
    path=Path(path);info=path.stat()
    if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o027:
        raise ValueError('Private administrator-owned observation identity required')
    value=read_json(path)
    if set(value) != {'role','private_key'} or value['role'] != role or role not in ROLES:
        raise ValueError('Observation identity mismatch')
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value['private_key']))


def public_keys(path):
    path=Path(path);info=path.stat()
    if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Administrator-owned public observation registry required')
    value=read_json(path)
    if set(value) != set(ROLES) or len(set(value.values())) != len(ROLES):
        raise ValueError('Distinct role observation keys required')
    # Verify key encoding before any record is trusted.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    for key in value.values():Ed25519PublicKey.from_public_bytes(bytes.fromhex(key))
    return value


def role_snapshot(folder, keys, *, now=None):
    now=time.time() if now is None else now
    result=[]
    for role in ROLES:
        try:
            record=read_json(Path(folder)/role/'latest.json')
            body=check_record(record,role,keys[role],now)
            result.append({'role':role,'record_status':'VERIFIED_RECENT_OBSERVATION',**body['observation'],
                'sequence':body['sequence'],'observed_at':body['observed_at']})
        except (OSError,ValueError,TypeError,KeyError,Denied):
            result.append({'role':role,'record_status':'NOT_VERIFIED',
                **observation('UNKNOWN','ROLE_OBSERVATION_NOT_VERIFIED')})
    return result


class AuditReader(GlassBoxAudit):
    def __init__(self,path):self.path=str(path)
    def connect(self):return readonly_database(self.path)


def shield_observation(status_file=Path('/proc/self/status')):
    fields=dict(line.split(':',1) for line in status_file.read_text().splitlines() if ':' in line)
    unprivileged=os.geteuid()!=0
    no_caps=int(fields['CapEff'].strip(),16)==0
    no_new=fields['NoNewPrivs'].strip()=='1'
    safe=unprivileged and no_caps and no_new
    return observation('HEALTHY' if safe else 'FAULT','PROCESS_BOUNDS_OBSERVED',
        nonroot=int(unprivileged),capabilities_dropped=int(no_caps),no_new_privileges=int(no_new))


def measure(role, database, root, results, keys):
    if role not in ROLES:raise ValueError('Unknown MASTER role')
    if role in ROLE_PROBES:
        probes=configured_probes(database,AuditReader(Path(database).with_name('sds_audit.db')),root=root)
        return probes[ROLE_PROBES[role]]()
    if role=='GlobalPBDSentinel':return source_probe(root)
    if role==SHIELD:return shield_observation()
    snapshots=role_snapshot(results,keys)
    if role=='MINOTAUR':
        # Independently authenticate the defensive process observation; never sign clearance.
        shield=next(value for value in snapshots if value['role']==SHIELD)
        return observation(shield['state'],'SHIELD_PATROL_OBSERVATION',
            verified_shield=int(shield['record_status']=='VERIFIED_RECENT_OBSERVATION'))
    if role=='IT_AI_Manager_v15.0':
        agents=[value for value in snapshots if value['role'] in ROLE_PROBES]
        missing=sum(value['record_status']!='VERIFIED_RECENT_OBSERVATION' for value in agents)
        faults=sum(value['state']=='FAULT' for value in agents)
        return observation('FAULT' if faults else 'UNKNOWN' if missing else 'HEALTHY',
            'AGENT_MATRIX_OBSERVED',verified_agents=len(agents)-missing,faulted_agents=faults)
    if role==CONDUCTOR:
        from .michael_angelo import conductor_observation
        return conductor_observation(snapshots)
    if role in RTSA_ROLES:
        data={}
        if role=='ARCHITECT':
            data={'components':list(ROLES),'interfaces':['SIGNED_READ_ONLY_OBSERVATION'],
                  'trust_boundaries':['DISTINCT_ROLE_KEYS','NO_EXECUTION_AUTHORITY']}
        elif role=='CERBERUS':
            AuditReader(Path(database).with_name('sds_audit.db')).verify_audit()
            data={'hash_chain_verified':True}
        elif role=='Operations RTSA 📊':
            with readonly_database(database) as db:
                count=db.execute("SELECT COUNT(*) FROM ai_operational_incidents WHERE state='OPEN'").fetchone()[0]
            data={'active_incidents':count}
        result=assess(role,data)
        # Original advisory findings are explicit input/evidence gaps, not claims
        # that a model, post-quantum engine or external verifier actually ran.
        return observation('UNKNOWN',result.findings[0],advisory_findings=len(result.findings))
    # A running Sidecar observer is not a functioning L15 repair engine.
    return observation('UNKNOWN','L15_EXECUTION_NOT_CONNECTED',
        verified_role_observations=sum(v['record_status']=='VERIFIED_RECENT_OBSERVATION' for v in snapshots))


def publish(role, key, folder, probe, *, clock=time.time):
    if role not in ROLES:raise ValueError('Unknown MASTER role')
    folder=Path(folder)
    with (folder/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        sequence=1;latest=folder/'latest.json'
        if latest.exists():
            # Restart cannot reset sequence or silently accept changed local evidence.
            previous=read_json(latest)
            body=check_record(previous,role,public_hex(key.public_key()),clock(),freshness=float('inf'))
            sequence=body['sequence']+1
        try:sample=validated(probe())
        except Exception:sample=observation('UNKNOWN','ROLE_PROBE_FAILED')
        body={'schema':1,'platform':'Sanders Dash & Seal','role':role,'sequence':sequence,
            'observed_at':clock(),'observation':sample,'laws_sha256':LAW_HASH,'mode':'READ_ONLY_OBSERVATION'}
        record={'body':body,'signature':sign(key,DOMAIN,body)}
        fd,temporary=tempfile.mkstemp(prefix='.observation-',dir=folder)
        try:
            with os.fdopen(fd,'wb') as output:
                output.write(canonical(record));output.flush();os.fsync(output.fileno())
                os.fchmod(output.fileno(),0o640)
            os.replace(temporary,latest)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)
    return record


class RoleObservationStore:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS ai_role_watermarks (
                role TEXT PRIMARY KEY, sequence INTEGER NOT NULL, observed REAL NOT NULL, hash TEXT NOT NULL)''')

    def status(self,folder=Path('/run/sds-ai/results'),registry=Path('/run/sds-ai/public-keys.json')):
        try:keys=public_keys(registry)
        except (OSError,ValueError,TypeError,KeyError):keys={}
        snapshots=role_snapshot(folder,keys)
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            for item in snapshots:
                if item['record_status']!='VERIFIED_RECENT_OBSERVATION':continue
                # Retain a watermark across API/worker restarts. Same snapshot is idempotent.
                body_hash=hashlib.sha256(canonical(item)).hexdigest()
                row=db.execute('SELECT sequence,observed,hash FROM ai_role_watermarks WHERE role=?',(item['role'],)).fetchone()
                if row and (item['sequence']<row[0] or item['observed_at']<row[1]
                        or (item['sequence']==row[0] and body_hash!=row[2])):
                    item.update(record_status='NOT_VERIFIED',**observation('UNKNOWN','ROLE_REPLAY_REJECTED'))
                    continue
                db.execute('INSERT OR REPLACE INTO ai_role_watermarks VALUES (?,?,?,?)',
                    (item['role'],item['sequence'],item['observed_at'],body_hash))
        return {'mode':'READ_ONLY_ROLE_OBSERVATION','authority_granted':False,
            'model_inference_verified':False,'roles':snapshots}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=ROLES,required=True)
    parser.add_argument('--key',type=Path,default=Path('/run/sds-role/identity.json'))
    parser.add_argument('--output',type=Path,default=Path('/run/sds-role/output'))
    parser.add_argument('--results',type=Path,default=Path('/run/sds-ai/results'))
    parser.add_argument('--registry',type=Path,default=Path('/run/sds-ai/public-keys.json'))
    parser.add_argument('--database',type=Path,default=Path('/app/data/sds_production.db'))
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    key=protected_identity(args.key,args.role);keys=public_keys(args.registry)
    if public_hex(key.public_key())!=keys[args.role]:raise ValueError('Observation trust anchor mismatch')
    stop=threading.Event()
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:stop.set())
    while not stop.is_set():
        publish(args.role,key,args.output,lambda:measure(args.role,args.database,args.root,args.results,keys))
        if args.once:break
        stop.wait(30)


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('AI_ROLE_WORKER_NOT_COMPLETED') from None
