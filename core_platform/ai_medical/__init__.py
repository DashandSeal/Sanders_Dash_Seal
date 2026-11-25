"""Sanders AI Medical — Constitutional Execution Stack.

The enforcement layer over AI_DOCTOR (Q53) and AI_PSYCHIATRIST
(Q54), built into the main repo from the received design
(2026-11-25) and conformed to the sovereign Charter (Arts. I-IX)
under the AI Medical fix plan (fixes 0-12):

- identity_kernel: entity identity manifests whose charter texts
  scope the patient class to artificial intelligences ONLY (Fix 0);
  baselines pinned by the signed policy bundle, never self-derived
  (Fix 7); keys load-only, never minted at boot (Fix 8).
- policy_bundle: the owner-signed bundle that pins identity
  baselines and firewall calibration outside the code (Fixes 5, 7).
- policy_kernel: closed-schema output gate (Fix 1), whole-output
  evaluation (Fix 2), no silent prohibition skips — UNKNOWN blocks
  (Fix 3), signed outputs and signed decision receipts (Fix 4).
- input_firewall: AI-system origin only; human-patient subject
  matter is a hard reject (Fix 0); the gate is reachable by
  legitimate system input and unreachable by human origin (Fix 6).
- constraint_engine: prohibited intent ABORTS (Fix 9); executable
  content is stripped from otherwise-lawful outputs.
- semantic_risk_engine: the documented severity ladder, MEDIUM
  included, implemented as documented (Fix 12).
- audit_ledger: hash-chained append-only ledger; Merkle anchoring
  into the repo's Glass-Box chain when the sink is bound; optional
  Ed25519 entry signatures (Fix 12). Every event type is emitted
  by a real code path (Fix 10).
- fail_state_machine: HALT is a flag, never a blocked thread;
  termination belongs to the embedding process (Fix 12).
- cross_validator: all three stated conflict conditions, including
  prohibition asymmetry (Fix 11); engagement is structural in the
  gateway, never caller-optional.
- api_gateway: the single pipeline every model interaction passes
  through; fails closed with named provisioning states.
- enforcement: the facade production bindings attach to the two
  platform services; unprovisioned means outcomes are refused with
  the named state, never waved through.

The 9 approval gates are untouched by this layer; no gate is
flipped, no secret is provisioned by this code.
"""

from __future__ import annotations

__all__ = [
    "api_gateway",
    "audit_ledger",
    "constraint_engine",
    "cross_validator",
    "enforcement",
    "fail_state_machine",
    "identity_kernel",
    "input_firewall",
    "policy_bundle",
    "policy_kernel",
    "semantic_risk_engine",
]
