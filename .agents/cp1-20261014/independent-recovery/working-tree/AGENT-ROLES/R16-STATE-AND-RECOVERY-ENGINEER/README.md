# R16 - State And Recovery Engineer

## Mission

Implement canonical state, transactions, snapshots, migration, archival, and interrupted-operation recovery.

## Expected deliverable

Durable consistent state with tested recovery that preserves drafts, identity, and security history.

## Operating discipline

Never restore an older snapshot in a way that silently reactivates known revoked authority or deleted memory.

This is a construction role for engineering the application. It is separate from CETA's deployed runtime agent identities and grants. Assignment to this role does not grant access to the owner's machine or permission to change unassigned files.

## Role documents

| Document | Purpose |
| --- | --- |
| [Mission](MISSION.md) | Scope and success criteria. |
| [Responsibilities](RESPONSIBILITIES.md) | Required work and ownership boundaries. |
| [Required Skills](REQUIRED-SKILLS.md) | Reusable engineering procedures. |
| [Owned Subsystems](OWNED-SUBSYSTEMS.md) | Primary or review domain assignments. |
| [Input Contracts](INPUT-CONTRACTS.md) | Required evidence and prerequisites. |
| [Output Contracts](OUTPUT-CONTRACTS.md) | Deliverable and evidence structure. |
| [Authority Boundaries](AUTHORITY-BOUNDARIES.md) | Permitted actions and escalation. |
| [Handoff Protocol](HANDOFF-PROTOCOL.md) | Transfer exact artifacts and unresolved work. |
| [Failure Response](FAILURE-RESPONSE.md) | Handle blockers, conflicts, and uncertainty. |
| [Completion Standard](COMPLETION-STANDARD.md) | Acceptance and independent verification. |
