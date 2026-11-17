# Oracle deployment — source and acceptance record

## Original owner requirement

Source: owner's conversation instruction dated 2026-11-16, directing that all Sanders platforms be hosted on Oracle Always Free rather than Render, with the first Secretary release committed publicly on GitHub `main`. Also the repository governing `AGENTS.md` and `docs/CORE_LAW_10_ALL_PLATFORMS.md` (Oracle Always Free only) plus `docs/CORE_LAW_11_ALL_PLATFORMS.md` (actual live Oracle resource use).

## Acceptance criteria and observable implementation

1. **Public source:** Secretary source remains on public `main` under `sanders-corporations-secretary/`. Present in the repository.
2. **Oracle delivery:** `.github/workflows/deploy_scs_to_oracle_always_free.yml` listens for relevant `main` pushes and passes the exact commit SHA to an Oracle VM over pinned-host-key SSH. Implemented in source; execution on Oracle not yet evidenced.
3. **No Render runtime:** No Render deployment is created or referenced as a production target. Implemented in source.
4. **Distinct live service:** Remote script runs Secretary via separate checkout, user token, SQLite state, and systemd unit, bound to VM loopback 127.0.0.1:8791. Scripted; real host state not yet verified.
5. **No secret publication:** GitHub SSH credentials come from Actions Secrets; initial Secretary access token is generated on Oracle, not in the repository. Implemented in source; actual secret setup remains external.
6. **Other businesses stay intact:** Remote script does not run existing Dash & Seal deployment commands or modify existing Compose project, DNS, firewalls, existing services, or databases. Implemented in source.
7. **No extra assistant release gates:** No PR merge, approval switch, CI test requirement, authorizer executable, or unrelated validation is added. Implemented in source.
8. **Production truth:** A source commit alone does not establish a running Oracle service, Internet exposure, full AI capabilities, or operational Core Law 11 proof. Installation/runtime evidence to be reported separately.

No tests are added or run as part of this deployment packaging. The workflow and shell installer have adjacent SHA-256 unsigned-source PBD manifest pairs, not fabricated signatures.