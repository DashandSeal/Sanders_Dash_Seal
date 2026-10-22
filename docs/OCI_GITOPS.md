# Automatic Oracle deployment from GitHub

`.github/workflows/oci-gitops-deploy.yml` runs automatically on pushes to main.
There is no production-environment approval, custom release token, manual
verification checkbox or required self-hosted runner. A workflow-dispatch event
can rerun the same workflow on main. Deployment runs are serialized rather than
canceling an in-progress installation.

The workflow executes the actual Python and Node suites, Node dependency audit,
container builds and repository integrity check. It packages all committed
application source into `sds-unified-production-stack.zip`, uses the actual
GitHub commit SHA, uploads the ZIP with the supported `--config-source` option,
runs Plan and Apply, then executes and waits for application installation on
the existing `sanders-dash-seal` VM using the Oracle agent. Failed jobs and
nonzero install exit codes fail the workflow. Test counts are reported by the
test runners, never hardcoded as success messages.

The workflow preserves the stack's actual existing/new-node profile. When
Terraform state already contains the stack's A1 instance, GitOps keeps that
instance selected rather than changing to the original host or destroying it.
Resource Manager completes Apply before the agent installs the exact release;
this works for updates as well as first boot. A stack must already exist;
the workflow uses its actual OCID rather than inventing one.

Repository Actions secrets required once:

| Secret | Actual value |
| --- | --- |
| OCI_TENANCY_OCID | Actual tenancy OCID from Oracle |
| OCI_USER_OCID | Actual OCI API-signing user OCID |
| OCI_FINGERPRINT | Fingerprint of the uploaded API public key |
| OCI_PRIVATE_KEY | Matching unencrypted PEM signing private key |
| OCI_STACK_OCID | Actual existing-host Resource Manager stack OCID |
| OCI_REGION | us-phoenix-1; this region is also the default |

The username `Rooseveltsanders381` is not an OCID. The earlier example ending
in `aaaaaaaarooseveltsandersroot` was not a verified account identifier.
Put private keys directly into GitHub's secret field, never a source file,
issue, chat message or ZIP. The workflow creates a temporary 0600 key/config,
uses API-key authentication, and removes its temporary directory. It does not
use Instance Principals on a GitHub-hosted runner; the Oracle application VM
uses Instance Principals to retrieve releases, backups and designated secrets.
The API-signing user needs OCI policies for the actual stack, its managed
resources and instance-agent commands. No secret values are supplied here.

This connector cannot set repository Actions secrets or account billing
controls. GitHub-hosted private-repository runners have included minutes and
may charge for overages; use GitHub's stop-usage budget controls to enforce
the owner's $0 requirement. This workflow does not select a larger paid
runner, create extra compute, buy DNS or upgrade an Oracle account. It cannot
guarantee a $0 GitHub bill without the account's billing controls.

The live Stripe webhook has been registered at
`https://sandersdashandseal.com/stripe/webhook`. The application's restricted
live API key and matching webhook signing secret still belong in the protected
`sds-runtime-provider-config` Oracle secret, never in the source ZIP. GitHub
deployment authentication and the application's Stripe credentials are separate.
No live payment round trip or Oracle Apply is claimed by these source changes.

### Existing owner stack

GitOps defaults to the owner-supplied Phoenix Resource Manager stack
`ocid1.ormstack.oc1.phx.amaaaaaaftib4xqaggduipcxfh7oscxgqq4276qzr3u25dynr3vzs3hiadqa`.
An `OCI_STACK_OCID` Actions secret overrides the repository variable of the same
name, which overrides this default. The identifier is not a signing key. OCI
authentication still uses the configured tenancy, user, fingerprint and private
key. This addition targets the existing stack; it does not create another stack
or establish that Apply, application installation or business integrations ran.
