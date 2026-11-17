# Controlled rollout — public code, private runtime

1. Merge reviewed v0.2 source into the public `sanders-corporations-secretary/` subdirectory. Keep existing company app code outside this directory untouched.
2. Install Python 3.11+, requirements and run `pytest -q` before serving.
3. Generate `SCS_API_TOKEN` securely on the deployment machine; never commit an actual token, model key or SQLite database.
4. Deploy with HTTPS, restricted access, and durable private storage for `state/secretary.sqlite3`. The default app is intended to listen only on localhost.
5. Index owner-authorized original corporate documents using the local Knowledge Vault. Preserve version and citation; do not place confidential documents into public GitHub.
6. Sync the public GitHub connector and verify source URL, timestamps and event idempotence.
7. Configure an optional trusted inference service only with explicit owner consent and after reviewing provider data retention policies; do not enable remote sending by default.
8. Verify live external connectivity separately. The v0.2 system does not yet monitor filing portals or operate continuously in an external cloud deployment.