# Authoritative source mapping

Read for this build from the owner's saved files on October 15, 2026:

1. `Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md` — authoritative build baseline, sections 1–21.
2. `Sanders_Dash_Seal_Actual_Build_Design_RAW_PROTOCOLS_2026-10-11.md` — original protocol/code archive, sections A–L.
3. `Sanders_Dash_Seal_PBD_Routing_Logic_Both_Versions.md` — original routing and bounded production interpretation.
4. `Sanders_Dash_Seal_Platinum_Blue_Diamond_Token_Protocol.md` — original and bounded token definitions.

The saved source documents are preserved unchanged. This repository implements selected requirements and does not replace those records.

| Source requirements | Implementation |
|---|---|
| MASTER 8–11: Twin Gate, bounded authority, denial, one-use leases | `core_platform/security.py`: TwinGate, Vault |
| MASTER 13–15: paired files, manifest gate, Sentinel | security.py: PBDManifestGenerator, PBDScriptValidationEngine, GlobalPBDSentinel |
| MASTER 5–8, 19–20: role separation and verified completion | `core_platform/lifecycle.py` |
| Routing version 2: independent verification, revocation, proof of possession | GovernedLifecycle and result-hash-bound signed attestations |
| MASTER 18: device not root of trust | injected authority public keys; remote key custody remains deployment work |

Original sample gateway names are examples, not established integrations or proof of notarial authority. The sample simulated HTTP 200 and hard-coded verification success are not used as live evidence. Internal priority cannot override third-party access controls. No external bypass behavior is implemented.
