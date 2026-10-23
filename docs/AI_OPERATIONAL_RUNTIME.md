# Operational runtime and remaining synthetic-AI integration

Source: MASTER §§3–8, 15, 19–20 and the October 23 owner request.

The native application now initializes durable operational state separately from
the Glass-Box Audit database. The existing backend can execute an observation
cycle with:

```bash
python -m core_platform.operational_worker
```

The Oracle installer installs `sanders-ai-observe.timer`. Every minute its service
executes this module in the existing backend container. It creates no new OCI
resources and introduces no inference dependency into application startup.
The timer must run on the actual VM before a live-cycle claim is made.

The authenticated operator can inspect `GET /api/operator/ai/status`. Other users
cannot retrieve this operational history. The response includes observation age,
open incidents, observed recoveries, and the distinct status of each of the twelve
IT-agent roles. Failures in one probe do not stop the remaining probes. Missing
observations stay UNKNOWN. UNKNOWN does not resolve an open fault. A later
explicit healthy observation records OBSERVED_RECOVERY, never an asserted repair.
Slower older cycles cannot overwrite newer evidence. State survives process restart.

| Role | Actual observation |
| --- | --- |
| Uptime Agent | Local HTTP process-health response |
| Application Agent | Local readiness response |
| Database Agent | Read-only SQLite quick check |
| Deployment Agent | Source/paired-manifest hash consistency |
| Infrastructure Agent | Actual filesystem capacity |
| Integration Agent | Persisted provider requests needing reconciliation |
| Performance Agent | Measured local health-response latency |
| Backup & Recovery Agent | Timestamp of two genuinely verified backup restores |
| Observability Agent | Separate local audit-chain verification |
| Quality Agent | Independent database connection checking supervision schema |
| Configuration Agent | Runtime ten-law/catalog consistency |
| IT Support Agent | Durable open-incident inventory |

The backup service publishes only timestamp and verified-database count into the
existing read-only runtime mount after both restore checks succeed. The worker
does not access customer document contents or provider credentials. Arbitrary
probe exceptions and free text are not stored as telemetry. Source hashes alone
are not authority signatures; a local audit chain is not externally immutable.

These twelve functions are operational observers, not a claim that twelve
independent synthetic intelligences have been completed. Model inference,
independently operated Manager/MINOTAUR/Quality authority services, protected key
custody, signed bounded repair execution, model learning and immutable external
anchoring remain unfinished. The endpoint reports those connections explicitly
as NOT_CONNECTED rather than generating approvals or claiming inference.

## Building directly on Oracle

The existing `deploy/install_application.sh` runs `compose build` and `compose up`
on the Oracle VM. GitHub transports versioned source and triggers the existing
Resource Manager/Agent path; the application container build happens on Oracle.
Oracle Cloud Shell provides an authenticated OCI CLI, so the existing activation
module can also be invoked there from the complete source checkout:

```bash
python3 -m deploy.activate_on_oracle --stack-id "$SDS_STACK_OCID"
```

`SDS_STACK_OCID` must identify the owner's actual Resource Manager stack with the
intended source archive already uploaded. This command performs Plan, validates
the actual plan, applies it and dispatches the existing private installer. It
does not upload the new local source automatically. The complete source must
first be incorporated in that stack through the existing release/upload path.
No private signing key needs to be pasted into the command or committed to source.

Cloud Shell is a development/control environment; recurring services execute on
the existing Always Free compute instance. No new paid resource is provisioned
by this runtime increment.
