# Sanders Dash & Seal — mandatory build instructions

The owner's original technical specifications control this repository. Preserve the exact platform identity **Sanders Dash & Seal**. The original saved files are identified in `docs/SOURCE_MAPPING.md`; the actual build design is authoritative, not a concept or brainstorming note.

Before implementing or modifying a requirement:

1. Identify its original source section and record its acceptance criteria in `docs/SPEC_CONFORMANCE.md`.
2. Preserve the original requirement. Assistant-authored interpretations are reference material, not owner-approved amendments.
3. Do not silently merge components, weaken a gate, simplify a protocol/schema, introduce a global policy from a single example, or claim compliance based on a placeholder.
4. Where original sources conflict or lack implementation details, document the precise conflict and obtain the owner's decision before selecting a behavior. Keep the affected production capability blocked.
5. Distinguish implemented mechanics, tested development behavior, incomplete requirements and production blockers. Passing unit tests does not prove full specification compliance.
6. Preserve Humanitarian Core Laws verbatim. MINOTAUR and Sanders Labyrinth Shield 🛡️ are separate. Vault and Glass-Box Audit are separate. Follow all other role boundaries in MASTER section 20.
7. Pair every executable source change with its `.pbd.json` hash update. Never fabricate authority signatures. An unsigned pair is a production blocker, not authorization.
8. Test changed security behavior, including denied/failure paths. Update the conformance record and report unresolved gaps honestly.
9. No merge, public release or deployment is implied by development work. Do not commit private keys, credentials or customer records.

See `docs/SPEC_CONFORMANCE.md` for known deviations and unresolved decisions. Do not expand functionality while concealing those deviations.
