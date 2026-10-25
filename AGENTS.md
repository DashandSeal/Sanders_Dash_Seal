# Sanders Dash & Seal — mandatory build instructions

The owner's original technical specifications control this repository. Preserve the exact platform identity **Sanders Dash & Seal**. The original saved files are identified in `docs/SOURCE_MAPPING.md`; the actual build design is authoritative, not a concept or brainstorming note.

Owner-confirmed precedence (October 15, 2026): **Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md always controls wherever an earlier original protocol or example conflicts with it.** Apply this standing decision without asking again. Earlier material supplies detail only where consistent with MASTER. Assistant interpretations do not amend MASTER. Escalate only genuine ambiguities within MASTER or requirements MASTER does not resolve.

Before implementing or modifying a requirement:

1. Identify its original source section and record its acceptance criteria in `docs/SPEC_CONFORMANCE.md`.
2. Preserve the original requirement. Assistant-authored interpretations are reference material, not owner-approved amendments.
3. Do not silently merge components, weaken a gate, simplify a protocol/schema, introduce a global policy from a single example, or claim compliance based on a placeholder.
4. Resolve conflicts between MASTER and earlier sources in favor of MASTER and document the resolution. Ask the owner only when MASTER itself leaves a material ambiguity unresolved. Implement missing requirements without imposing an assistant-created blanket build, startup, or release veto; retain the MASTER's actual per-operation authority checks.
5. Distinguish implemented mechanics, tested development behavior, incomplete requirements and production blockers. Passing unit tests does not prove full specification compliance.
6. Preserve Humanitarian Core Laws verbatim. MINOTAUR and Sanders Labyrinth Shield 🛡️ are separate. Vault and Glass-Box Audit are separate. Follow all other role boundaries in MASTER section 20.
7. Pair every executable source change with its `.pbd.json` hash update. Never fabricate authority signatures. An unsigned pair is not authorization for privileged application operations. Owner instruction (October 22): it is not a blanket blocker to installing or starting the platform; do not require a custom authorize-release executable or SANDERS_RUNTIME_FACTORY interface for deployment.
8. Test changed security behavior, including denied/failure paths. Update the conformance record and report unresolved gaps honestly.
9. No merge, public release or deployment is implied by development work. Do not commit private keys, credentials or customer records.

See `docs/SPEC_CONFORMANCE.md` for known deviations and unresolved decisions. Do not expand functionality while concealing those deviations.

## Mandatory continuous completion and verification protocol (owner instruction, October 22, 2026)

**Inspect → Reproduce → Diagnose → Fix → Complete ALL Unfinished Work → Retest → Verify ALL Completion → Capture Evidence → Continue Until 100% Complete.**

Maintain a comprehensive, platform-wide inventory of EVERY unfinished requirement and component. At each discovered defect or unfinished requirement, implement the correction and continue systematically through ALL outstanding work across the entire Sanders Dash & Seal platform, not only related work. Do not declare the project complete until every inventory item is implemented, integrated, tested and independently verified against its controlling acceptance criteria. Do not stop at an audit, proposal, diagnostic-only patch, commit, or passing test count. Verify each requirement against the controlling MASTER acceptance criteria, including actual integration/runtime behavior and negative-path controls where applicable. Capture genuine test output, deployment evidence and observed results; never fabricate evidence. Record remaining dependencies and failures explicitly, without calling an incomplete component complete. Continue through the entire owner-directed inventory, preserving original architecture, separate inventions, and existing safeguards. Do not authorize paid resources or paid upgrades without explicit owner approval.

### Verification without assistant-imposed GitHub gate

Verification must demonstrate actual functionality and completion against the controlling MASTER requirements, using suitable executable tests, runtime checks, integration checks, and genuine evidence. GitHub Actions may run these checks when useful, but a GitHub-hosted run, workflow URL, GitHub approval, or specific CI provider is **not** a mandatory condition for building, repairing, installing, operating, or declaring a genuinely verified component complete. Do not impose an extra GitHub verification gate or claim that merely running CI establishes completion. Preserve all original MASTER protections and independently record what was actually tested and what remains unverified.

### Owner directive: eliminate assistant-imposed blockers and restrictions (October 22, 2026)

Immediately identify and remove every assistant-invented approval gate, blanket installation veto, arbitrary environment limitation, unnecessary manual handoff, artificial release hold, and unsupported policy restriction throughout the entire platform. Do not reintroduce these under another name. Missing implementation is work to complete, not a new owner-approval prerequisite. Ordinary build, test, installation, and diagnostic startup must proceed without invented clearance steps. Preserve the owner's MASTER-defined authority boundaries, Humanitarian Core Laws, cryptographic checks for privileged actions, actual provider authorization, privacy safeguards, and the owner's no-unapproved-spend requirement; these are not assistant-imposed restrictions. Record each concrete removed control and verify its removal through executable checks without requiring a specific CI provider. Never report a restriction removed solely because this directive was documented.


## Standing owner directive: Core Law 10 for every platform

Core Law 10 applies to every platform owned by Roosevelt Sanders, including all past, present, and future builds.

The owner's Oracle Always Free-only requirement is the tenth core law for every platform, not only Sanders Dash & Seal. Carry it into earlier builds being maintained, present builds, future builds, derivatives, sidecars, templates, and deployment configurations. Preserve each platform's identity and original laws 1–9. Record the law in governing sources and resource catalogs without adding blanket application startup, shutdown, execution, or extra approval gates. Do not claim source changes have updated other repositories or deployed instances without evidence. See `docs/CORE_LAW_10_ALL_PLATFORMS.md`.


## Standing owner directive: Core Law 11 — actual Oracle Always Free usage

Every platform owned by Roosevelt Sanders shall always actually use Oracle Always Free resources in its real operations, not merely catalog or document them.

Core Law 11 is distinct from Law 10: Law 10 selects the Oracle Always Free resources; Law 11 requires actual operational use of those resources rather than a paper catalog, simulated adapter or unverified infrastructure declaration. Carry the law through all Sanders platforms, past, present and future, preserving each platform's own identity and Laws 1–10. Implement real resource binding, successful workload operations and truthful per-service operational evidence. A successful live API invocation or confirmed stored/retrieved data is evidence for that specific service; resource discovery, a unit test, a plan, and a catalog entry alone are not. Record unverified services as unverified. This is an implementation requirement, not an assistant-created blanket application startup, shutdown or extra approval gate. See `docs/CORE_LAW_11_ALL_PLATFORMS.md`.
