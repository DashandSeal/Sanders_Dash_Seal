"""Check this host's Oracle Cloud instance identity metadata.

Usage:
    python3 scripts/scan_identity_metadata.py

This is the script called by deploy/sds-bootstrap.sh (verify_instance_context)
before an activate-mode bootstrap. It did not exist in the repository, so
that step always failed.

It queries the OCI instance metadata service exactly as the installer's
inline resource-binding step does -- http://169.254.169.254/opc/v2/instance/
with an "Authorization: Bearer Oracle" header, no proxy, short timeout --
and requires a JSON document with an instance OCID in it. It reads identity
only: it writes nothing, sends no credentials, and performs no cloud
changes. Exit status is 0 only when the metadata service answers with a
usable instance identity; otherwise a reason is printed to stderr and the
exit status is 1, so the bootstrap fails closed instead of activating a
node whose identity was never confirmed.
"""

import json
import re
import sys
import urllib.error
import urllib.request

METADATA_URL = "http://169.254.169.254/opc/v2/instance/"
INSTANCE_ID = re.compile(r"ocid1\.instance\.[A-Za-z0-9.]+", re.ASCII)


def fail(message):
    print("IDENTITY_METADATA_NOT_CONFIRMED: " + message, file=sys.stderr)
    raise SystemExit(1)


def main():
    request = urllib.request.Request(
        METADATA_URL, headers={"Authorization": "Bearer Oracle"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            raw = response.read(65536)
            if response.status != 200:
                fail("metadata service returned HTTP %s" % response.status)
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        fail("metadata service unreachable: " + str(error))
    try:
        record = json.loads(raw)
    except ValueError as error:
        fail("metadata service returned invalid JSON: " + str(error))
    if not isinstance(record, dict):
        fail("metadata service returned a non-object document")
    instance_id = record.get("id")
    if not isinstance(instance_id, str) or INSTANCE_ID.fullmatch(instance_id) is None:
        fail("metadata service returned no instance OCID")
    region = record.get("region")
    print("INSTANCE_IDENTITY_CONFIRMED %s%s"
          % (instance_id, (" region=" + region) if isinstance(region, str) else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
