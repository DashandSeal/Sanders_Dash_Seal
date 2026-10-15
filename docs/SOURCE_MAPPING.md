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
| MASTER 8–9: independent verification, revocation, agent identity assertion | GovernedLifecycle and result-hash-bound signed attestations |
| MASTER 18: device not root of trust | injected authority public keys; remote key custody remains deployment work |

The original user-authored requirements control. Assistant-authored versions are preserved reference material, not approved amendments. See SPEC_CONFORMANCE.md for unresolved differences.

Original sample gateway names are examples, not established integrations or proof of notarial authority. The sample simulated HTTP 200 and hard-coded verification success are not used as live evidence. External routing is unimplemented; the original external-priority language and available receiving-service mechanisms require an explicit decision.
