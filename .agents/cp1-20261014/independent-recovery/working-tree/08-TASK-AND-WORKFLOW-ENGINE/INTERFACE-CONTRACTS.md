# 08-TASK-AND-WORKFLOW-ENGINE - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. | [08-TASK-AND-WORKFLOW-ENGINE](README.md) |
| [workflow-transition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/workflow-transition.contract.md) | Only declared transitions with satisfied guards commit. Expected-version checks prevent stale workers from overwriting newer state. | [08-TASK-AND-WORKFLOW-ENGINE](README.md) |
| [persistent-checkpoint](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | Checkpoints preserve observed effects and continuation, not reusable authentication. Resume validates current authority and target state. | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |
| [uncertain-operation](../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | Uncertainty is a durable state requiring target inspection or authoritative receipts before replay. A new attempt or compensation requires current authority. | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [execution-result](../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | Complete requires declared outputs and observed effects. Cancellation and uncertainty preserve already committed effects; an exit code does not override contradictory observations. | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
