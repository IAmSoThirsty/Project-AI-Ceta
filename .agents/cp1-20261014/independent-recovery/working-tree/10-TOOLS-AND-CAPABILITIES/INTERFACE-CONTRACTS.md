# 10-TOOLS-AND-CAPABILITIES - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [tool-manifest](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-manifest.contract.md) | The manifest binds exact implementation and effects, including transitive actions. Discovery exposes availability, not permission. | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [tool-invocation](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | Invocation arguments are normalized before approval and immutable afterward. Every invocation goes through the common execution gate. | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [tool-result](../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-result.contract.md) | Schema-valid success still requires declared outputs and observed effects. Preserve raw evidence and unknown outcomes. | [10-TOOLS-AND-CAPABILITIES](README.md) |
| [intended-effect](../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md) | Every transitive effect is declared. Reversibility describes an actual compensating mechanism, not merely local state rollback. | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [execution-request](../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md) | The normalized immutable request is approved before dispatch and is compared again at use time. Any changed input, effect, tool revision, or target requires reevaluation. | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [evidence-receipt](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md) | Receipts bind exact operation evidence within a declared trust model. Integrity, attribution, observation completeness, and functional success remain separate checks. | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
