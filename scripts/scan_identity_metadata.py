"""Bounded host-local IMDSv2 observation; supplements regional OCI inventory."""
import argparse
import json
import re
import urllib.request


BASE = 'http://169.254.169.254/opc/v2/instance/'
FIELDS = ('id', 'hostname', 'canonicalRegionName', 'state')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Metadata redirect rejected')


def observe_identity(*, opener=None, expected_instance_id=None):
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    result = {}
    for field in FIELDS:
        request = urllib.request.Request(BASE + field, headers={'Authorization': 'Bearer Oracle'})
        with opener.open(request, timeout=5) as response:
            if response.status != 200 or response.geturl() != BASE + field:
                raise ValueError('Unexpected metadata response')
            raw = response.read(4097)
            if len(raw) > 4096:
                raise ValueError('Oversized metadata response')
            value = raw.decode('utf-8').strip()
            if value.startswith('"'):
                value = json.loads(value)
            if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
                raise ValueError('Invalid metadata value')
            result[field] = value
    if not re.fullmatch(r'ocid1\.instance\.oc1\.[a-z0-9-]+\.[A-Za-z0-9]{40,}', result['id']):
        raise ValueError('Invalid local instance identity')
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9.-]{0,252}', result['hostname']):
        raise ValueError('Invalid local hostname')
    if not re.fullmatch('[a-z]{2,}-[a-z0-9-]+-[0-9]+', result['canonicalRegionName']):
        raise ValueError('Invalid canonical region')
    if result['state'].upper() != 'RUNNING':
        raise ValueError('Local instance is not reported as running')
    if expected_instance_id is not None and result['id'] != expected_instance_id:
        raise ValueError('Local instance differs from expected identity')
    return {'status': 'LOCAL_METADATA_OBSERVED', 'instance_id': result['id'],
            'hostname': result['hostname'], 'region': result['canonicalRegionName'],
            'state': result['state'].upper(), 'cryptographic_attestation': False,
            'production_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-instance-id')
    args = parser.parse_args()
    try:
        print(json.dumps(observe_identity(expected_instance_id=args.expected_instance_id)))
    except (OSError, ValueError, TypeError, UnicodeError):
        print(json.dumps({'status': 'LOCAL_METADATA_UNAVAILABLE_OR_MISMATCHED', 'production_ready': False}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
