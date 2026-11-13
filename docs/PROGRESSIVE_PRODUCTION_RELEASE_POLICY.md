# Owner-directed deployment behavior

> **STATUS 2026-11-13 (C17).** This is the owner's *authorization* for
> automatic installation, startup and GitOps deployment — it is not evidence
> that the automation exists. The workflow it describes
> (`.github/workflows/oci-gitops-deploy.yml`) **does not exist** in this
> repository; see `docs/OCI_GITOPS.md`. Until that workflow is created, there
> is no "active workflow" running tests, building the ZIP or applying the
> stack, and the sentences below describing it must be read as the authorized
> design, not as current fact. See `docs/P3_CORRECTIONS_2026-11-13.md`.

This replaces the assistant-authored progressive promotion policy. Roosevelt
Sanders controls the platform and has authorized automatic installation,
startup and GitOps deployment. No additional artifact-specific approval string,
production-environment approval or assistant-defined promotion ceremony is
required by this repository's deployment process.

The active workflow runs real tests, builds the committed source ZIP, uses the
owner's actual OCI authentication, applies the selected stack and installs the
application. Both original-host and new A1-node profiles are supported. There
is no blanket unsigned-source installation prohibition.

The owner's MASTER design continues to govern privileged application operations:
Humanitarian Core Laws, required human oversight, independent authority roles,
proper cryptographic signatures and protected private data. A source checksum
is not an authority signature. Deployment does not manufacture those services.

The owner's $0/no-unapproved-spending instruction remains controlling. Actual
cloud authentication errors, failed commands and absent provider credentials
are reported as failures; they are not disguised as successful connections.
An unobserved capability is reported as unobserved, not an automatic startup ban.

The live Stripe webhook was registered under the owner's instruction. The
application still needs its protected signing secret and restricted API key on
Oracle. No assistant policy requires registering that webhook to wait for a
separate production-release approval.

See OMISSIONS_AND_RESTRICTIONS_AUDIT.md for current implemented and unfinished
connections. No complete live notarial transaction or independent AI-service
implementation is asserted by installing the runtime.
