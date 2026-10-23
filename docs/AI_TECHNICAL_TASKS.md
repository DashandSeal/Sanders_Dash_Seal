# Durable AI technical-task execution

The observation worker now submits one `BUG_DIAGNOSIS` task per open measured
incident and diagnosis mode into the existing technical dispatcher. Connecting a
local model creates a separate model-analysis task while retaining the original
deterministic diagnosis. Registered read-only workers
atomically claim tasks, execute their diagnostic handlers, and persist both result
and independent local evidence review. Work claims are ownership tokens, not
Vault execution leases or authority credentials. An expired claim can redeliver
read-only work; the former worker cannot finish or fail a reassigned task.
Mutating capabilities are not automatically executed or retried by this worker.

The diagnosis component produces evidence hashes and unproven causal hypotheses.
A separate reviewer reads the actual observation history to validate factual
findings. A factual finding is not a proven root cause, a signed Quality Agent
attestation, or a grant to perform a repair. An absent reviewer leaves the result
recorded without claiming independent verification. Handler failure is recorded
without exception text or automatic mutation retries. Results survive restarts.

The authenticated operator can read `GET /api/operator/ai/tasks`. Worker ownership
tokens are excluded. The API is read-only and preserves the existing operator and
host checks. The application remains available without a model service.

## Local inference connection

The same diagnosis path can use a model server on the existing VM. The implemented
transport follows the self-hosted llama.cpp chat-completions protocol documented
at https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md.
No model weights, model-server image, remote AI account, API credential, paid
service or new compute instance is created by this change.

When a model server is actually installed in the backend's local network namespace,
the host's existing protected runtime mount can contain `ai-model.json`:

```json
{
  "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
  "model": "installed-local-model"
}
```

The model name must match the installed server's configured identity/alias.
The configuration must be root-owned and private, readable by the backend group,
matching the existing runtime configuration custody. The mounted backend path is
`/run/sds/ai-model.json`; localhost refers to the container's network namespace,
not an unrelated service on the Docker host. No public endpoint is opened.

All ten laws and only measured diagnostic evidence are sent. The client requests
bounded, structured hypotheses and counterevidence, follows no redirects and sends
no tools. Responses are locally validated for shape, completeness and exact
evidence references. Generated hypotheses remain UNPROVEN. A model response never
becomes a Twin-Gate approval or an execution grant.

Without a configuration, deterministic evidence diagnosis continues and records
NOT_CONFIGURED. If the configured server cannot provide a valid response, that
attempt records UNAVAILABLE while preserving the deterministic diagnosis. Only
an actual successful HTTP response enters the model-assisted result path. With
a model configured, at most one diagnostic task is processed per cycle to keep
inference work separate from the normal recurring observation schedule.

## Remaining work

An installed model with verified weights, observed real inference quality/latency,
independently operated authority/signing services, protected distinct role keys,
governed repair executors, model learning and immutable external evidence remain
unfinished. Real HTTP fixture tests establish transport behavior, not the presence
of a functioning model or production authority service. The existing full-platform
completion inventory remains in force.
