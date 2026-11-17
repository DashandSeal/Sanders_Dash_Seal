# Sanders Corporations Secretary — Functional Non-Interference Principle

**Owner-directed design requirement — November 17, 2026**

## Governing principle

Do not introduce unnecessary verifications, blockers, tests, repetitive confirmations, or approval gates that interfere with the true purpose and intended functionality of any Sanders system.

The design must enable the system to carry out its authorized work efficiently, including persistent owner recognition, global communication with authorized personnel, real-time corporate operations, and reliable execution of permitted tasks.

## Engineering requirements

1. **Purpose first.** Define success by the system's actual ability to perform its assigned functions, not by the number of gates or checklists it passes.
2. **Recognize the authorized owner without repetitive prompts.** Use secure persistent sessions and identity binding; do not treat a typed name alone as proof of identity. Require a renewed sign-in only when the session expires or a meaningful security event warrants it.
3. **Make communication operational.** Once an owner-authorized channel and recipient directory are configured, allow routine authorized messages and notices to send promptly, with delivery/error status. Do not demand a new confirmation for each routine message when authorization and scope are already established.
4. **Respect explicit limits.** Protect credentials, confidential records, and individual company boundaries. Require additional authorization only for genuinely consequential actions such as financial transfers, legally binding signatures, confidential disclosures, or material external changes.
5. **Non-interfering tests.** Run tests automatically in development and CI, not as obstacles in the user's daily workflow. Tests must verify real functionality, including failure and recovery; do not disable capabilities merely to satisfy artificial checks.
6. **Recover rather than stall.** Provide retry, queueing, status reporting, and escalation for failed communications and integrations. Avoid silent failures and invented completion claims.
7. **Owner authority is final for internal decisions.** The system must not impose assistant-created internal approval chains. Legal, privacy, and platform requirements still apply where necessary.
8. **Honest operational status.** Clearly distinguish implemented features, configured channels, successfully delivered actions, and planned integrations. A mockup or proposal is not a completed live operation.

## Acceptance criteria

- A signed-in owner is consistently recognized across valid sessions.
- Authorized global communications can be dispatched through configured providers without needless per-message confirmation, and delivery results are recorded.
- Tests do not block normal operational use after a build has been released.
- Company records remain separate and access-controlled.
- The system reports actual operation and recovery states accurately.

This principle applies to future Sanders corporate systems and subsequent versions of Sanders Corporations Secretary.
