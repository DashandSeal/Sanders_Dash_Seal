# Sanders Dash & Seal — mandatory build instructions

The owner's original technical specifications control this repository. Preserve the exact platform identity **Sanders Dash & Seal**. The original saved files are identified in `docs/SOURCE_MAPPING.md`; the actual build design is authoritative, not a concept or brainstorming note.

Owner-confirmed precedence (October 15, 2026): **Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md always controls wherever an earlier original protocol or example conflicts with it.** Apply this standing decision without asking again. Earlier material supplies detail only where consistent with MASTER. Assistant interpretations do not amend MASTER. Escalate only genuine ambiguities within MASTER or requirements MASTER does not resolve.

Before implementing or modifying a requirement:

1. Identify its original source section and record its acceptance criteria in `docs/SPEC_CONFORMANCE.md`.
2. Preserve the original requirement. Assistant-authored interpretations are reference material, not owner-approved amendments.
3. Do not silently merge components, weaken a gate, simplify a protocol/schema, introduce a global policy from a single example, or claim compliance based on a placeholder.
4. Resolve conflicts between MASTER and earlier sources in favor of MASTER and document the resolution. Ask the owner only when MASTER itself leaves a material ambiguity unresolved. Keep affected production capabilities blocked until requirements are satisfied.
5. Distinguish implemented mechanics, tested development behavior, incomplete requirements and production blockers. Passing unit tests does not prove full specification compliance.
6. Preserve Humanitarian Core Laws verbatim. MINOTAUR and Sanders Labyrinth Shield 🛡️ are separate. Vault and Glass-Box Audit are separate. Follow all other role boundaries in MASTER section 20.
7. Pair every executable source change with its `.pbd.json` hash update. Never fabricate authority signatures. An unsigned pair is not authorization for privileged application operations. Owner instruction (October 22): it is not a blanket blocker to installing or starting the platform; do not require a custom authorize-release executable or SANDERS_RUNTIME_FACTORY interface for deployment.
8. Test changed security behavior, including denied/failure paths. Update the conformance record and report unresolved gaps honestly.
9. No merge, public release or deployment is implied by development work. Do not commit private keys, credentials or customer records.

See `docs/SPEC_CONFORMANCE.md` for known deviations and unresolved decisions. Do not expand functionality while concealing those deviations.

## Mandatory continuous completion and verification protocol (owner instruction, October 22, 2026)

**Inspect → Reproduce → Diagnose → Fix → Complete ALL Unfinished Work → Retest → Verify ALL Completion → Capture Evidence → Continue Until 100% Complete.**

Maintain a comprehensive, platform-wide inventory of EVERY unfinished requirement and component. At each discovered defect or unfinished requirement, implement the correction and continue systematically through ALL outstanding work across the entire Sanders Dash & Seal platform, not only related work. Do not declare the project complete until every inventory item is implemented, integrated, tested and independently verified against its controlling acceptance criteria. Do not stop at an audit, proposal, diagnostic-only patch, commit, or passing test count. Verify each requirement against the controlling MASTER acceptance criteria, including actual integration/runtime behavior and negative-path controls where applicable. Capture genuine test output, deployment evidence and observed results; never fabricate evidence. Record remaining dependencies and failures explicitly, without calling an incomplete component complete. Continue through the entire owner-directed inventory, preserving original architecture, separate inventions, and existing safeguards. Do not authorize paid resources or paid upgrades without explicit owner approval.
