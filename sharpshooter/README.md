# SharpShooter RTSA — executable foundation

SharpShooter is an operational infrastructure diagnosis and remediation service, not a governing or constitutional layer.

## Run

```bash
python -m sharpshooter.cli diagnose example.org
python -m unittest discover -s sharpshooter/tests -v
```

## Implemented

- DNS, TCP/443 and certificate-verified TLS handshake diagnosis with SNI
- Incident generation and integrity-hashed JSON evidence
- Provider adapter contract with explicit capabilities
- Authorization-aware remediation planner
- Execute-versus-plan separation
- Independent post-execution TLS verification
- Unit tests

## Next production integrations

Implement real provider adapters, credential acquisition, persistent event store, multi-region probes, certificate chain/ARI inventory, API service, queue-based concurrent workflows, rollback, contracts, billing and production deployment. No provider mutations occur until an adapter with valid credentials is configured. This is an initial executable foundation, not a completed end-to-end production deployment.
