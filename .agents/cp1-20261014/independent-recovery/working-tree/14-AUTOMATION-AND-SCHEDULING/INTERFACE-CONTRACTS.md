# 14-AUTOMATION-AND-SCHEDULING - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [scheduled-task](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/scheduled-task.contract.md) | Occurrence identity is stable across restart and clock changes. Current authority is checked when each occurrence is admitted. | [14-AUTOMATION-AND-SCHEDULING](README.md) |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |
| [authority-delegation](../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |
| [resource-budget](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md) | Child budgets share the parent envelope. Measured use, estimates, and reservations are distinct and control-plane reserve remains available. | [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) |
| [workflow-transition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/workflow-transition.contract.md) | Only declared transitions with satisfied guards commit. Expected-version checks prevent stale workers from overwriting newer state. | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |
| [evidence-receipt](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md) | Receipts bind exact operation evidence within a declared trust model. Integrity, attribution, observation completeness, and functional success remain separate checks. | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
