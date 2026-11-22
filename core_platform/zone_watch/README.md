# Zone Watch

Zone Watch incorporates the owner's ICANN CZDS zone-file access into
Sanders Dash & Seal. The owner's zone requests are approved for all
requested zones including `com` (requested 23 April 2026).

## What it does

1. **Download** — streams each approved TLD zone file from CZDS over
   HTTPS with basic authentication (`downloader.py`). The TLD list
   comes from `CZDS_TLDS` and defaults to `com,app,global`, the TLDs
   the owner's platforms use.
2. **Filter** — keeps only the names that match the Sanders brands and
   the platform hostnames (`filter.py`): the 35 platform hostnames
   shared by the four ship-it repositories plus the 10 Sanders Dash &
   Seal site names. A matched name not seen before is flagged
   `new_registration`; a known platform hostname seen before is
   `known`; a brand-carrying name that is not a platform hostname is
   `lookalike`. Only matches are stored, in a small SQLite database.
3. **Global DNS check** — verifies every platform and site hostname
   resolves through public DNS-over-HTTPS (`global_dns.py`). That is
   the "function globally" check: a hostname that does not resolve
   anywhere is not reachable on the internet.
4. **Feed** — emits one JSON event per match (`feed.py`) to a JSONL
   events file, and exposes the importable `publish_event` function
   for watchdog and Sentinel modules to receive events directly.

## What it does not do

- It never loads a whole zone file into memory and never stores a
  whole zone file on disk. The `.com` zone alone is gigabytes.
- It does not invent a new wire protocol. The feed is a plain JSON
  events file plus an importable function.
- It is not wired into any watchdog or Sentinel module: no watchdog
  or Sentinel module in this repository exposes an event intake, so
  there is nothing to wire into. Zone Watch is a separate service
  that feeds them events; it does not merge with them.
- It makes no claim about a name beyond what the zone file and public
  DNS say. It never judges intent.

## Always Free limits (Core Laws 10 and 11)

Zone Watch runs on the Oracle Always Free instance (1 OCPU, 6 GB RAM,
47 GB disk) and is built for it: streaming download, a small
line-by-line filter, and a matches-only SQLite store. The daily run
downloads only the configured TLDs. Do not add TLDs the platforms do
not use, and do not store zone files.

## Running it

From the repository root on the instance, with CZDS_USERNAME and
CZDS_PASSWORD set in the environment:

```sh
python3 -m core_platform.zone_watch.run --data-dir /home/opc/zone-watch
```

Data written under the data directory (matches only, never a zone):

- `zone-watch-matches.db` — SQLite match store.
- `zone-watch-events.jsonl` — one JSON event per match.
- `zone-watch-summary.json` — the run summary, including any
  hostnames that failed to resolve.

## Owner steps still needed

1. **CZDS credentials** — the ICANN account username and password go
   into the Secure Vault, and as `CZDS_USERNAME` and
   `CZDS_PASSWORD` secrets in the repository settings for the daily
   workflow. They are never committed to the repository.
2. **Daily workflow** — `.github/workflows/zone-watch-daily.yml` is
   kept out of this push (the GitHub App cannot push workflow
   files). Place it through the GitHub web UI. It runs daily on the
   instance over the existing SSH secrets.
3. **First run needs the code on the instance** — the daily workflow
   pulls `main` on the instance before running; the first run needs
   this commit deployed there (a deploy run waits on the owner's
   Production-Authorization-Gate, which only the owner approves).
