# 03-COMPANION-INTELLIGENCE - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [agent-manifest](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md) | Reusable role and runtime agent identity are distinct. A role declaration cannot grant capabilities or establish independent review. | [07-AGENT-ORCHESTRATION](../07-AGENT-ORCHESTRATION/README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | Inputs, model revision, context, and data destination are pinned. Fallback that changes locality requires an explicit new data-export decision. | [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) |
| [context-snapshot](../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md) | Trusted instructions and retrieved data are structurally separated. Critical constraints are preserved exactly and source versions are pinned. | [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) |
| [memory-record](../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md) | Exact user statements, observations, inferences, and summaries remain distinct. Corrections and deletion propagate to all derived retrieval paths. | [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) |
| [human-decision-request](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | The request exposes exact scope and consequences and expires when its proposal changes. Approval is never inferred from viewing or silence. | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [task-definition](../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. | [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
