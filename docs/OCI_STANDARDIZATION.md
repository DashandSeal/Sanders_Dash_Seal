# Repeatable OCI instances for Sanders Dash & Seal

The owner's golden image → instance configuration → cloud-init design is
implemented as reviewable source. `deploy/standardize.py` generates requests;
it does not call OCI, capture the production VM, launch another instance or
change IAM. The original submitted cloud-config is preserved separately in
`docs/owner-submitted/standardization.proposed.cloud-config.txt`.

## Image selection and the $0 requirement

Use a compatible Oracle Linux 9 ARM64 platform image to avoid adding stored
custom-image charges. A custom golden image remains supported as an explicit
option. Oracle documents that capturing a running instance shuts it down for
several minutes and that stored images are charged. Capturing
`sanders-dash-seal` therefore cannot be described as free or nondisruptive.
An image captures the boot disk, not attached block-volume contents.

If choosing the golden-image option, prepare a separate sanitized builder:

- Install compatible locked dependencies, Git, Python 3, active firewalld with
  verified SSH access, and optionally prebuilt container images.
- Include no customer ledger, document payloads, credentials, TLS private keys,
  signing keys, Git deploy credentials, or production runtime authorization.
  Docker named volumes on the boot disk are captured too; inspect them.
- Do not clone production machine identity, SSH host private keys, user SSH
  access configuration or cloud-init completion state. On the dedicated builder,
  review the image's cloud-init cleanup procedure before its final shutdown;
  this package deliberately does not clean the running production VM.
- Confirm image/shape architecture compatibility and sufficient boot disk size.
  This template selects A1 with 1 OCPU, 6 GB RAM and 50 GB boot storage. An image
  requiring more disk needs a reviewed template change.

## Render an instance configuration

Run from a clean approved checkout containing this standardization extension.
The selected commit must include `stage_authorized_source`,
`install_integrity_monitor`, and the new bootstrap/profile files. Earlier
commits do not contain those entry points. Supply actual OCI identifiers;
syntactic validation is not proof of resource existence or capacity.

```bash
python3 deploy/standardize.py \
  --commit "$APPROVED_COMMIT" \
  --compartment-id "$OCI_COMPARTMENT_OCID" \
  --image-id "$OCI_IMAGE_OCID" \
  --subnet-id "$OCI_SUBNET_OCID" \
  --nsg-id "$OCI_NSG_OCID" \
  --availability-domain "$OCI_AVAILABILITY_DOMAIN" \
  --ssh-public-key-file "$SSH_PUBLIC_KEY_FILE" \
  --output /tmp/sds-standardization-review
```

The output contains `cloud-init.yaml` and `instance-configuration.json`.
To render the optional image capture request, add
`--sanitized-builder-instance-id "$OCI_BUILDER_INSTANCE_OCID"`. This assertion
does not verify sanitization and the request is not submitted automatically.
Review the output before a separately authorized OCI resource creation action.
The JSON configuration is an OCI CreateInstanceConfigurationDetails request;
its `instanceDetails` object can be supplied to the CLI's `--instance-details`
file parameter, with compartment and display name supplied separately.

Public-IP assignment is off by default; `--assign-public-ip` enables it for an
edge node. Private nodes still need a working route to their source and image
registries, or preseeded source/images. This does not create a NAT gateway,
alter the verified Internet Gateway route, or grant an IAM policy.

## First boot and production activation

Cloud-init writes a root-owned driver and invokes one argv command once per
instance in its final stage. It does not run at the exact instant of boot.
It also writes the root-owned system audit outside the managed source directory
and runs it first, saving/printing a private first-boot observation. Missing
initial tools or directories are labeled as gaps; the subsequent bootstrap
retains the actual deployment gates. See `docs/SYSTEM_PREFLIGHT_AUDIT.md`.
The driver checks out a full immutable commit, disables interactive Git prompts,
rejects a different origin or dirty checkout, and stops on failures. It uses
the active interface's firewalld zone without flushing rules or removing SSH.
The original independent release authorizer and protected runtime factory are
required before host setup; unsigned development pairs do not grant authority.

Private-repository access must be provisioned independently or a clean checkout
preseeded at `/opt/sds-approved-source`. Do not place deploy tokens in user data
or bake reusable credentials into an image. User data is not a secret store.
Independently supply `/etc/sanders-dash-seal/authorize-release` and root-private
`runtime.env`, as described in the existing deployment documentation.

Default **stage** mode builds the worker/backend and installs the source
integrity timer, but starts no application containers. It refuses existing SDS
containers or an existing integrity baseline instead of blessing host drift.
It does not enable certificate issuance or backup timers on a staged node.
It also installs the six-hour read-only OCI inventory timer. Configure actual
expected identities and Instance Principals inspection access as described in
`docs/OCI_AUTOMATED_INVENTORY.md`; missing configuration yields a failed report.

Optional `--tune-kernel` preserves the owner's exact three values persistently
in `/etc/sysctl.d/90-sanders-dash-seal.conf`. Application is verified and kernel
values restored if it fails. These are an explicit tuning profile, not a measured
throughput improvement. Linux cautions against changing `tcp_tw_reuse` without
understanding its effects; staging/load testing should establish suitability.

**activate** mode delegates to `deploy.sh --apply`, retaining certificate, DNS,
runtime authority and readiness gates. It requires `--assign-public-ip` and
`--public-ipv4` for this particular node; it never silently inherits
129.146.111.166. A newly assigned ephemeral address is not known before launch:
use staged provisioning and a reviewed per-node invocation after the address is
verified. Do not put a reusable activate configuration into an instance pool.
The current four-domain primary deployment must not be activated on multiple
nodes without reviewed traffic routing and authoritative database roles.

## Limits that templates do not solve

Instance configurations are regional templates, not a retroactive policy for
every existing server. Availability domain, subnet, image compatibility,
capacity, and the shared tenancy's remaining Always Free allocation must be
checked before any launch. This package does not assert that 100 instances,
custom images, Streaming or Functions cost $0.

The current one-instance Dynamic Group rule does not authorize clones. Select
an independently reviewed narrowly scoped membership strategy and permissions;
do not replace it with tenancy-wide access. Never clone the authoritative SQLite
ledger into independent writable production copies. New instances are staged
until their role and durable state topology are defined.

Sources:

- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/managingcustomimages.htm
- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/creatinginstanceconfig.htm
- https://docs.cloud-init.io/en/latest/reference/modules.html#runcmd
- https://kernel.org/doc/html/latest/networking/ip-sysctl.html

Development tests establish the renderer and failure behavior only. They do not
certify a zero-vulnerability image or confirm an OCI launch, cloud-init execution,
live throughput, production signatures, TLS issuance or runtime connectivity.
