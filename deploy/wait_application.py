"""Wait for the installed application, not just Terraform's VM provisioning state."""
import ipaddress
import json
import os
import sys
import time
import urllib.request


def observe(address, commit, opener=None):
    if not ipaddress.IPv4Address(address).is_global:
        raise ValueError('Actual public IPv4 required')
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for path in ('/healthz', '/release-status.json'):
        request = urllib.request.Request('http://' + address + path,
            headers={'Host': 'sandersdashandseal.com'})
        with opener.open(request, timeout=5) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                return False
        record = json.loads(raw)
        if path == '/healthz' and (record.get('platform') != 'Sanders Dash & Seal' or record.get('process_alive') is not True):
            return False
        if path == '/release-status.json' and (record.get('commit') != commit or record.get('application_installed') is not True):
            return False
    return True


def wait(address, commit, *, timeout=5400, check=observe, clock=time.monotonic, pause=time.sleep):
    deadline = clock() + timeout
    while True:
        try:
            if check(address, commit):
                print('APPLICATION_INSTALLED: exact release and public process health verified. Business integrations and TLS have separate readiness states.')
                return 0
        except (OSError, ValueError, TypeError):
            pass
        if clock() >= deadline:
            print('APPLICATION_NOT_INSTALLED: inspect cloud-init output; provisioning alone is not deployment success.', file=sys.stderr)
            return 1
        pause(min(10, max(0, deadline - clock())))


if __name__ == '__main__':
    raise SystemExit(wait(os.environ['SDS_EXPECTED_PUBLIC_IPV4'], os.environ['SDS_EXPECTED_COMMIT']))
