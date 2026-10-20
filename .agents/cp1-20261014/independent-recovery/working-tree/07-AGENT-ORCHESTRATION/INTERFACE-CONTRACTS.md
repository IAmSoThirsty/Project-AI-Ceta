# 07-AGENT-ORCHESTRATION - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [agent-manifest](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md) | Reusable role and runtime agent identity are distinct. A role declaration cannot grant capabilities or establish independent review. | [07-AGENT-ORCHESTRATION](README.md) |
| [agent-message](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-message.contract.md) | Messages are authenticated task-scoped claims. Delivery is deduplicated and does not create authority or establish factual truth. | [07-AGENT-ORCHESTRATION](README.md) |
| [agent-handoff](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-handoff.contract.md) | The receiver validates exact artifacts, remaining work, authority, and uncertainty before accepting ownership. Handoff does not revive expired authority. | [07-AGENT-ORCHESTRATION](README.md) |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |
| [authority-delegation](../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
