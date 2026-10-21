# Render deployment review — Sanders Dash & Seal

Prepared October 21, 2026. Review only; no Render service, subscription, domain record or live payment has been created.

## Source and account

Use the owner's confirmed Render My Workspace and the existing private repository DashandSeal/Sanders_Dash_Seal, branch build/domain-deployment-entrypoint (reviewed application commit 2d502367cacaea63172ac676ef46f9018657bc9a). Do not deploy main: it contains only the README in the reviewed inventory. Do not substitute a static brochure.

## Proposed hosting

One Python web service named sanders-dash-seal in Oregon, one instance, automatic deployment disabled during initial setup. Use a compatible production WSGI server with wsgi:application, listening on 0.0.0.0 and Render's PORT. The server dependency must be reviewed and pinned before deployment; the current requirements file does not install a WSGI server.

Preserve SQLite databases under an attached persistent disk (proposed mount /var/data). Production adapters must explicitly use that path; merely mounting a disk does not change database locations. Render free web services cannot attach a persistent disk. The advertised smallest paid web compute starts at $7/month, plus disk and any excess usage. No paid resources are authorized by this review. Confirm the current total before creation.

## Application requirements before public operation

The existing WSGI entry point defaults to diagnostic/static startup with readiness 503 and APIs unavailable. Do not report this as an operational platform. A real administrator-controlled SANDERS_RUNTIME_FACTORY must supply the existing shared appointment/payment store, session authentication and login app, independent release verification and optional signature-verifying Stripe webhook. The current repository does not provide this production factory or its credentials. Preserve required source approvals and genuine artifact signatures; do not replace gates with unconditional success.

The current host allowlist admits the owner's domains, not an arbitrary onrender.com hostname. Resolve health-probe host behavior and verify correct rejection of unknown hosts before service creation. Do not weaken host validation to make a deploy appear healthy. Process liveness /healthz does not prove operational readiness /readyz.

## Domains and acceptance

Canonical sandersdashandseal.com; safe-read aliases www.sandersdashandseal.com, sanderslegalhelpersllc.com and www.sanderslegalhelpersllc.com. Obtain actual Render-issued DNS targets and certificates after service creation. Preserve unrelated DNS records. No DNS changes until the selected deployment and original customer journey are verified.

Acceptance requires durable database paths, restart/recovery checks, genuine authentication and authorization, signed webhook handling without making a live charge, correct host routing, TLS, and operational readiness. Current unit-test and CI success do not satisfy those external requirements.

## References checked

https://render.com/docs/disks
https://render.com/docs/free
https://render.com/pricing
https://render.com/docs/blueprint-spec
