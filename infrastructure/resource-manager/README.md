# Sanders Dash & Seal Resource Manager stack

This package provisions infrastructure through OCI Console without an SSH
terminal. It does not modify or adopt the existing sanders-dash-seal instance.
Use Terraform 1.5.x in Resource Manager (Oracle currently documents CLI 1.5.7).
The OCI provider is pinned to 9.11.0. Resource Manager supplies job authentication;
the provider deliberately does not request InstancePrincipal from its job host.
VM Instance Principals are a different identity and are not automatically granted.

## Upload and configure

1. In OCI Console choose Resource Manager > Stacks > Create Stack and upload the
   ZIP directly. Terraform files belong at ZIP root; no extra enclosing folder.
2. Check the automatically populated actual tenancy, target compartment and
   Phoenix region. For the root compartment, use the tenancy OCID, not its name.
3. Leave create_network=false to reuse your actual public subnet and
   ig-quick-action-NSG. Enter their full real OCIDs. No existing route or rule is
   edited. Alternatively create_network=true creates a separate VCN, public
   subnet, Internet Gateway, default internet route and web NSG.
4. Check remaining Always Free allocation before enabling create_instance=true.
   The new node is fixed to VM.Standard.A1.Flex with 1 OCPU, 6 GB RAM and a 50-GB
   boot volume. Defaults create no new VM or network. Image selection uses the
   latest matching Oracle Linux 9 ARM64 image at Plan time, or an explicit image
   OCID. Review and pin the selected image before future replacement plans.
5. Run Plan, review new resources and selected image, then Apply through Console.
   This package has not run a live Plan or Apply against your tenancy.

Availability-domain names are looked up from your actual tenancy rather than
hardcoding phx-ad-1. Change the domain index if OCI reports unavailable capacity.
A1 availability and billing eligibility are not proven by Terraform validation.
Your existing documented 1-OCPU/6-GB node plus this new node would total 2 OCPUs
and 12 GB, before counting any other resources. Boot/block storage shares the
tenancy's 200-GB Always Free allowance. Do not select E4 Flex as a free substitute.
Custom images and services outside Always Free can incur charges. No paid load
balancer, NAT gateway, Streaming, Functions or custom-image capture is added.

## Boot profiles

**audit** (default) works with a fresh compatible platform image. It runs the
first-boot system observation and produces /var/log/sds_platform_preflight.log
and cloud-init output. Missing Git, Docker, OCI CLI or directories are gaps, not
installed software or a live application. No private Git credentials or runtime
authority are placed in user data. Optional SSH public-key input is for recovery;
SSH is not required to submit the stack or launch its audit profile.

**approved_stage** embeds the already-tested pinned bootstrap. Its immutable
source commit is recorded in release.tf and the package manifest. It requires an
explicit prepared image with a clean preseeded /opt/sds-approved-source checkout
or secure private-repository access, root-owned independent authorize-release,
private runtime.env with genuine runtime factory, active firewalld and required
host tools. The ordinary platform image does not contain those application
bindings. Staging runs the actual disposable regressions and installs timers
only after the existing gates pass. It starts no public application containers.
Image preparation/storage is a separate cost and operations decision.

The package does not invent an authorizer, signature, production runtime adapter,
private Git token, IAM membership or permission. Existing Console/Vault/artifact
provisioning must supply genuine bindings before a fully unattended application
rollout is possible. This is an explicit prerequisite, not a requirement to use
SSH: administrators may use independently authorized provisioning mechanisms.

Application activation remains the separate release-approved path with per-node
IP, DNS/TLS, durable state and live readiness checks. A public IP is assigned by
OCI; it is not cloned from 129.146.111.166. Do not duplicate the authoritative
SQLite ledger into independent writers. No zero-downtime or maximum-throughput
guarantee follows from this stack or a static test count.

## Network and lifecycle boundaries

For a new network, web NSG rules allow TCP destination 80/443 from 0.0.0.0/0 with
unrestricted source ports and all outbound traffic. The associated custom subnet
security list adds no ingress. SSH port 22 is not opened by this stack. For reused
networks, all existing security lists/NSGs still apply; attaching an NSG does not
remove broader access granted elsewhere. Validate existing network posture.

The new instance has prevent_destroy protection. Terraform refuses a destructive
replacement until its configuration/lifecycle is independently reviewed. The
stack never imports the current production VM. Optional new network resources
remain Terraform-managed and are subject to normal Plan/Apply/Destroy behavior.
Changing user data later does not rerun cloud-init automatically. This package
does not provide an in-place deployment agent for the existing VM.

Terraform Apply completion means the control-plane operation completed, not that
cloud-init finished or the platform is live. Inspect cloud-init/Console logs and
the platform's readiness evidence. application_status intentionally stays
NOT_VERIFIED; it is not promoted by VM creation. The ZIP contains unsigned source
hash pairs and a package manifest for review, not production signatures.

## Rebuild from the repository

```bash
python3 -m scripts.package_resource_manager --commit "$APPROVED_COMMIT" --output /tmp/sds-automation-stack.zip
```

The builder does not call OCI and refuses to overwrite an existing ZIP. Generated
Terraform templates, audit/bootstrap bytes and source/config hashes are included.
The private application repository itself, credentials and customer records are
not copied into metadata or the ZIP. Application commit approval remains separate.

References:

- https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Concepts/terraformconfigresourcemanager.htm
- https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Reference/terraformversions.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Tasks/create-stack-local.htm
