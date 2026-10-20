# 04-PERSISTENT-MEMORY - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [memory-record](../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md) | Exact user statements, observations, inferences, and summaries remain distinct. Corrections and deletion propagate to all derived retrieval paths. | [04-PERSISTENT-MEMORY](README.md) |
| [knowledge-source](../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md) | Original bytes, extraction, and normalized interpretation are separate artifacts. Dates retain their distinct meanings and unknown values remain unknown. | [16-KNOWLEDGE-AND-RESEARCH](../16-KNOWLEDGE-AND-RESEARCH/README.md) |
| [provenance-link](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | Each relation has a specific supported meaning and valid endpoints. Co-occurrence and visual proximity do not create a causal edge. | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |
| [persistent-checkpoint](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | Checkpoints preserve observed effects and continuation, not reusable authentication. Resume validates current authority and target state. | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |
| [authority-revocation](../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md) | Revocation is durable, generation-ordered, and propagated to descendants and active admission checks. Known revocations survive restoration of older application data. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
