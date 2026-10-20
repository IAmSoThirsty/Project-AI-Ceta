# 19-STATE-AND-RECOVERY - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [state-transition](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | One canonical owner mutates the aggregate through expected-version checks. Historical corrections append rather than rewrite prior events. | [19-STATE-AND-RECOVERY](README.md) |
| [persistent-checkpoint](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | Checkpoints preserve observed effects and continuation, not reusable authentication. Resume validates current authority and target state. | [19-STATE-AND-RECOVERY](README.md) |
| [uncertain-operation](../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | Uncertainty is a durable state requiring target inspection or authoritative receipts before replay. A new attempt or compensation requires current authority. | [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md) |
| [recovery-report](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md) | Recovery reports actual restored and unresolved state, including drafts and identity preservation. Older backups cannot silently remove known security decisions. | [19-STATE-AND-RECOVERY](README.md) |
| [provenance-link](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | Each relation has a specific supported meaning and valid endpoints. Co-occurrence and visual proximity do not create a causal edge. | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
