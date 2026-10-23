# One-time Oracle agent installer setup

Observed evidence: diagnostic workflow 40016589134 queried the existing VM and
reported `ocarun`, uid 988, Oracle Linux 9.8, and failed passwordless sudo for
both id and bash. Ordinary Resource Manager Apply succeeded; the installer
exited immediately when requesting root. No live application installation or
inference success is inferred from Apply.

From an authenticated administrator session on that VM, use the reviewed source
of this PR and the existing `application_install_command` output's namespace and
bucket values (identifiers, not credentials):

```bash
sudo /usr/bin/python3 deploy/bootstrap_agent_installer.py \
  --namespace YOUR_EXISTING_NAMESPACE --bucket sds-release-YOUR_EXISTING_12_HEX_ID
```

The command installs the Oracle CLI if needed, writes a root-owned helper and
validates the specific sudoers entry with `visudo` before installing it. This
initial OS administrator action has not been performed by our unprivileged
agent. It grants no general bash or root access to `ocarun`. New root installs
configure it automatically from the actual release config.

After setup, the existing GitOps installer invokes the helper with its exact
40-character release commit. The helper accepts no caller paths or bucket
selection, uses a clean environment, downloads only that commit's installer
from the bound private bucket through Instance Principals, and executes it in a
private root directory with serialized execution. Bucket write access is the
existing trusted release-publisher boundary; possession of agent command access
permits activation of versions stored by that publisher. Do not share this
bucket with untrusted writers. Existing archive/source hashes remain checked by
the installation path; source manifests are not fabricated authority signatures.

The helper's source-controlled behavior and failure paths are tested locally.
Live administrator bootstrap, installation, model inference and independent
AI authority services remain unverified until actually observed.
