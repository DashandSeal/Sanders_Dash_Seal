"""Administrator provisions distinct observation identities; never authority keys."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from core_platform.ai_role_workers import ROLES, protected_identity, public_keys
from core_platform.security import public_hex


def atomic_json(path,value,mode,uid=0,gid=10001):
    if path.is_symlink():raise ValueError('Refusing symlink observation configuration')
    fd,temporary=tempfile.mkstemp(prefix='.sds-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as handle:
            json.dump(value,handle,sort_keys=True);handle.write('\n')
            handle.flush();os.fsync(handle.fileno())
            os.fchmod(handle.fileno(),mode);os.fchown(handle.fileno(),uid,gid)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def initialize(folder):
    if os.geteuid()!=0:raise PermissionError('Administrator observation-identity setup required')
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('Invalid observation configuration directory')
    folder.mkdir(mode=0o750,parents=True,exist_ok=True)
    if folder.stat().st_uid!=0 or folder.stat().st_mode & 0o022:
        raise ValueError('Observation configuration must be administrator-owned')
    os.chown(folder,0,10001)
    with (folder/'.initialize.lock').open('a') as lock:
        os.chmod(folder/'.initialize.lock',0o600)
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name in ('identities','public','public/results'):
            path=folder/name
            if path.is_symlink():raise ValueError('Invalid observation subdirectory')
            path.mkdir(mode=0o750,exist_ok=True);os.chown(path,0,10001);path.chmod(0o750)
        keys={}
        for role in ROLES:
            identity=folder/'identities'/(role+'.json')
            if identity.exists():key=protected_identity(identity,role)
            else:
                key=Ed25519PrivateKey.generate()
                atomic_json(identity,{'role':role,'private_key':key.private_bytes(
                    Encoding.Raw,PrivateFormat.Raw,NoEncryption()).hex()},0o640)
            keys[role]=public_hex(key.public_key())
            output=folder/'public/results'/role
            if output.is_symlink():raise ValueError('Invalid observation result directory')
            output.mkdir(mode=0o750,exist_ok=True);output.chmod(0o750);os.chown(output,10001,10001)
        registry=folder/'public/public-keys.json'
        if registry.exists():
            if public_keys(registry)!=keys:raise ValueError('Observation keys changed; refusing silent rotation')
        else:atomic_json(registry,keys,0o640)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('/etc/sanders-dash-seal/ai-roles'))
    args=parser.parse_args()
    initialize(args.directory)
    print('Distinct read-only observation identities initialized; no authority credentials created.')
