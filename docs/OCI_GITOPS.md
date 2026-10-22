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

This continuous-deployment profile reuses the existing VM. The separate direct
first-install profile creates a new node; an existing new-node stack is not
silently converted because that could remove its instance. Select the actual
existing-host Resource Manager stack for this workflow. A stack must already
exist; this workflow updates it rather than inventing a stack OCID.

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
