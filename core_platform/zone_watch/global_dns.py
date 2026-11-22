"""Sanders Dash & Seal — Zone Watch: global DNS check.

Verifies every platform and site hostname resolves through public
DNS (Google DNS-over-HTTPS). This is the "function globally" check:
a platform hostname that does not resolve anywhere is not reachable
on the internet, whatever the instance itself reports.

The local resolver is never used: the build VM's resolver returns
synthetic 198.18.x.x addresses and is unreliable. Only the public
DNS-over-HTTPS answer counts.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

DOH_URL = "https://dns.google/resolve"


def resolves(name: str, timeout: int = 10) -> dict:
    """Check one hostname against public DNS.

    Returns a dict with the name, whether it resolves, the DNS
    response status, and the answers returned (if any). A failure to
    reach the DNS service is reported as not resolving, with the
    reason recorded — it is never silently treated as resolving.
    """
    query = urllib.parse.urlencode({"name": name, "type": "A"})
    request = urllib.request.Request("%s?%s" % (DOH_URL, query))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError) as exc:
        return {"name": name, "resolves": False, "status": None,
                "answers": [], "error": str(exc)}
    status = payload.get("Status")
    answers = [item.get("data") for item in payload.get("Answer", [])
               if isinstance(item, dict) and item.get("data")]
    return {"name": name, "resolves": status == 0 and bool(answers),
            "status": status, "answers": answers, "error": None}


def check_all(names, timeout: int = 10) -> list[dict]:
    """Check every hostname in ``names`` and return one result per
    name, in the order given."""
    return [resolves(name, timeout=timeout) for name in names]


def failures(results: list[dict]) -> list[dict]:
    """Return only the results that did not resolve."""
    return [result for result in results if not result["resolves"]]
