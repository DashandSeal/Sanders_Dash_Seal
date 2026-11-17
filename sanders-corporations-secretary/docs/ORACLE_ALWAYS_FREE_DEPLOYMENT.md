# Sanders Corporations Secretary — Oracle Always Free deployment

**Owner architectural direction:** All live Sanders platforms run on Oracle Always Free; do not deploy this service on Render. This service is separate from Sanders Dash & Seal, even though both publish source in the same public GitHub repository.

## Actual workflow

The public `main` branch activates `.github/workflows/deploy_scs_to_oracle_always_free.yml` on changes to this directory. The workflow uses GitHub-hosted automation only as a delivery control plane; the runtime belongs on the existing Oracle Always Free VM. No GitHub PR, separate release branch, optional authorizer or user approval step is added.

The first remote installation checks out the exact pushed commit in a **separate** directory under the Oracle SSH user's home. It creates a Python virtual environment, saves local data outside source control, creates a private application token if needed, and installs an independent systemd service bound to `127.0.0.1:8791`. It does not alter existing Docker Compose projects, host firewall policies, DNS, root application, or other Sanders platform services.

## GitHub repository secrets (never place values in source)

Under the public repository's Settings → Secrets and variables → Actions, configure:

- `SCS_OCI_HOST`: the current reachable Oracle VM hostname/IP, checked against the live Oracle instance.
- `SCS_OCI_USER`: the SSH account on the Oracle VM (commonly `opc` on Oracle Linux).
- `SCS_OCI_SSH_KEY`: private SSH deploy key for that account; do not paste it into chat or commit it.
- `SCS_OCI_KNOWN_HOSTS`: **verified** SSH host-key line for the Oracle VM, not an unverified `ssh-keyscan` result.

When these values are absent, the workflow reports that no remote deployment occurred. It does not redirect to Render or silently report the Secretary as live. A dedicated least-privilege SSH identity is preferable where practical. The installation requires Python >=3.11, Git, and the SSH user's normal `sudo -n` permissions for adding one systemd unit.

## Public availability

The current Secretary application implements owner-token access for corporate data and was initially authored as a localhost prototype. The Oracle installer deliberately binds to `127.0.0.1:8791`. To make the dashboard accessible via a public domain without exposing its data over cleartext HTTP, route an HTTPS virtual host or an existing TLS reverse proxy to `127.0.0.1:8791`. Configure the chosen DNS name/certificate in the existing Oracle environment, preserving other corporate sites and their mail/DNS records. Do not publish port `8791` directly; the existing authenticated API is not yet a fully hardened multi-user service.

The deployment workflow is the automated *installation/restart* mechanism. A public HTTPS URL, actual Oracle workload use, live connectivity and uptime are not established by committing the workflow alone. The live instance requires a successful authenticated runtime interaction before reporting Core Law 11 operational compliance.

## Scope and data

The current inquiry endpoint is deterministic, not an externally connected generative AI model. The event feed streams local service records, not automatically retrieved news or grant data. Keep actual internal documents, corporate/client records, and all keys off public GitHub and on properly protected Oracle storage.

## Resource posture

GitHub source hosting and Actions orchestration do not substitute for Oracle runtime. Do not provision paid OCI shapes or third-party runtime hosting. The service shares the already chosen Oracle Always Free infrastructure subject to actual free-tier capacity and service limits.