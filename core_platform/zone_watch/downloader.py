"""Sanders Dash & Seal — Zone Watch: streaming CZDS zone-file download.

Downloads an approved TLD zone file from the ICANN Centralized Zone
Data Service (CZDS) over HTTPS with HTTP basic authentication and
yields it one line at a time. The caller processes each line as it
arrives; a whole zone file is never loaded into memory and never
written to disk.

Credentials come only from the environment (CZDS_USERNAME and
CZDS_PASSWORD). They are never hardcoded, never written to a file,
and never appear in any log or error message.

The CZDS download address is ``https://czds.icann.org/download/<tld>.zone``.
Set CZDS_DOWNLOAD_BASE_URL to point at a different base only if ICANN
changes that address.
"""

from __future__ import annotations

import base64
import gzip
import io
import os
import urllib.error
import urllib.request

DEFAULT_TLDS = ("com", "app", "global")
DEFAULT_DOWNLOAD_BASE_URL = "https://czds.icann.org/download"

_GZIP_MAGIC = b"\x1f\x8b"


class ZoneWatchConfigError(ValueError):
    """CZDS credentials or TLD configuration is missing."""


class ZoneWatchDownloadError(RuntimeError):
    """A CZDS zone-file download failed."""


def tlds_from_env(env: dict | None = None) -> tuple[str, ...]:
    """Return the TLD list from CZDS_TLDS, defaulting to the TLDs the
    owner's platforms use (com, app, global)."""
    source = os.environ if env is None else env
    raw = source.get("CZDS_TLDS", "")
    tlds = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    return tlds or DEFAULT_TLDS


def zone_download_url(tld: str, base_url: str | None = None) -> str:
    """Return the CZDS download address for one TLD."""
    base = (base_url or os.environ.get("CZDS_DOWNLOAD_BASE_URL")
            or DEFAULT_DOWNLOAD_BASE_URL).rstrip("/")
    return "%s/%s.zone" % (base, tld.strip().lower())


def iter_zone_lines(tld: str, *, username: str | None = None,
                    password: str | None = None, base_url: str | None = None,
                    timeout: int = 300):
    """Yield one decoded zone-file line at a time for ``tld``.

    The download is streamed: lines are yielded as they arrive and
    nothing is buffered beyond a small read window. A gzip-compressed
    zone file is transparently decompressed while streaming.

    Raises ZoneWatchConfigError when CZDS_USERNAME or CZDS_PASSWORD is
    not set, and ZoneWatchDownloadError when the download fails. The
    credentials are never included in any raised message.
    """
    user = username if username is not None else os.environ.get("CZDS_USERNAME")
    secret = password if password is not None else os.environ.get("CZDS_PASSWORD")
    if not user or not secret:
        raise ZoneWatchConfigError(
            "CZDS_USERNAME and CZDS_PASSWORD must both be set in the "
            "environment before a zone file can be downloaded.")
    url = zone_download_url(tld, base_url)
    token = base64.b64encode(
        ("%s:%s" % (user, secret)).encode("utf-8")).decode("ascii")
    request = urllib.request.Request(url)
    request.add_header("Authorization", "Basic " + token)
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise ZoneWatchDownloadError(
            "CZDS download for .%s failed with HTTP %s." % (tld, exc.code)
        ) from exc
    except urllib.error.URLError as exc:
        raise ZoneWatchDownloadError(
            "CZDS download for .%s failed: %s." % (tld, exc.reason)
        ) from exc
    stream: io.RawIOBase = io.BufferedReader(response)  # type: ignore[assignment]
    if stream.peek(2)[:2] == _GZIP_MAGIC:
        stream = gzip.GzipFile(fileobj=stream)  # type: ignore[assignment]
    for raw_line in stream:
        yield raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
