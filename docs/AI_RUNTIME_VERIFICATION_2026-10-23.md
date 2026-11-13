# Operational-runtime verification — October 23, 2026

Source baseline: `d918c08cdb6fa1c57a4dc278ae6eb7d035b6acf6`.

- Python: `python -m unittest discover -s tests -q` — **379 passed**, no skips.
- Node: `npm ci --omit=dev && npm test` — **22 passed**, no skips.
- Shell: `bash -n deploy/install_application.sh` — passed.
- Source integrity: **210 paired payload hashes** matched before this documentation
  record was added; no authority signatures were generated.
- Real worker subprocesses wrote cycles to SQLite, observed an actual local HTTP
  outage and recovery, and preserved records across process boundaries. The
  separate local audit chain verified afterward.
- Concurrent-cycle regression proved a slower old cycle cannot overwrite a newer
  fault. Unknown observations leave open incidents unresolved. Probe errors are
  redacted and do not stop remaining observers.
- Operator API regression verified anonymous/customer denial, operator access,
  host validation and read-only behavior. Application readiness remains available
  without a configured inference service.
- Both Terraform release-object replacement orders were tested. Changed bucket,
  namespace, object prefix, unknown destination, unrelated resource name,
  module address and deletion-only operations remained rejected.

The initial local regression run found the test environment lacked Gunicorn;
installing the repository-pinned `gunicorn==26.2.0` enabled the real HTTP/SIGTERM
test. The final full regression above passed. No application check was removed
to obtain that result.

Live deployment observation: GitHub Actions run
[40010092156](https://github.com/DashandSeal/Sanders_Dash_Seal/actions/runs/40010092156)
completed authentication and a real Oracle Plan, then rejected versioned installer
replacement before Apply. That false rejection is corrected in this increment.
No new Oracle Apply, VM installation, recurring timer execution, live inference,
independent authority service or autonomous repair was verified in this workspace.
Local test output mentioning agent/install success belongs to test doubles and
must not be presented as cloud deployment evidence.
