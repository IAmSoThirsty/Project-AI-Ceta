# 09-MODEL-RUNTIME - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [model-manifest](../INTERFACE-CONTRACTS/INTELLIGENCE/model-manifest.contract.md) | Declared capabilities and observed qualification are recorded separately. A configured endpoint or downloaded artifact is not necessarily ready for inference. | [09-MODEL-RUNTIME](README.md) |
| [inference-request](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md) | Inputs, model revision, context, and data destination are pinned. Fallback that changes locality requires an explicit new data-export decision. | [09-MODEL-RUNTIME](README.md) |
| [inference-response](../INTERFACE-CONTRACTS/INTELLIGENCE/inference-response.contract.md) | Model content and tool proposals are untrusted outputs requiring downstream validation. Partial streams cannot trigger incomplete action arguments. | [09-MODEL-RUNTIME](README.md) |
| [resource-budget](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md) | Child budgets share the parent envelope. Measured use, estimates, and reservations are distinct and control-plane reserve remains available. | [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) |
| [workload-admission](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md) | Admission atomically reserves resources and is fenced by generation. Capacity checks alone do not authorize launch. | [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
