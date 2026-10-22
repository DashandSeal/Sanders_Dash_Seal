"""Generate private initial owner access on the host; never emit secrets to logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import time


def initialize(folder,*,clock=time.time,chown=os.chown):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True,mode=0o750)
    chown(folder,0,10001);folder.chmod(0o750)
    settings=folder/'runtime.json'
    existing={}
    if settings.exists():
        if settings.is_symlink():raise ValueError('Secret file must not be a symlink')
        existing=json.loads(settings.read_text())
        if existing.get('owner_setup_digest'):return
    token=secrets.token_urlsafe(32)
    owner=folder.parent/'owner-setup.txt'
    expires=int(clock())+86400
    if owner.exists():
        import re
        info=owner.stat()
        if owner.is_symlink() or info.st_uid!=0 or info.st_mode & 0o077:
            raise ValueError('Invalid existing owner bootstrap protection')
        text=owner.read_text()
        found=re.search(r'^Single-use setup secret: ([A-Za-z0-9_-]{43})$',text,re.M)
        expiration=re.search(r'^Expires at Unix UTC: ([0-9]+)$',text,re.M)
        if not found or not expiration:raise ValueError('Invalid existing owner bootstrap')
        token=found.group(1);expires=int(expiration.group(1))
    else:
        with owner.open('x') as output:
            os.chmod(owner,0o600)
            output.write('Sanders Dash & Seal owner setup\nOpen https://sandersdashandseal.com/auth/setup\n'
                         'Single-use setup secret: '+token+'\nExpires at Unix UTC: '+str(expires)+'\n')
    with settings.open('w') as output:
        os.chmod(settings,0o640);chown(settings,0,10001)
        existing.update({'owner_setup_digest':hashlib.sha256(token.encode()).hexdigest(),
                         'owner_setup_expires':expires})
        existing.setdefault('stripe_livemode',True)
        json.dump(existing,output)
        output.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('/etc/sanders-dash-seal/runtime'))
    args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('Host initialization requires root')
    initialize(args.directory)
    print('Private runtime initialized; no credentials printed.')
