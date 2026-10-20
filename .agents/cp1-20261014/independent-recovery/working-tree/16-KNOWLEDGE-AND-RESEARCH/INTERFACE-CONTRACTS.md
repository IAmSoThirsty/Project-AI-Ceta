# 16-KNOWLEDGE-AND-RESEARCH - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [knowledge-source](../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md) | Original bytes, extraction, and normalized interpretation are separate artifacts. Dates retain their distinct meanings and unknown values remain unknown. | [16-KNOWLEDGE-AND-RESEARCH](README.md) |
| [research-claim](../INTERFACE-CONTRACTS/INTELLIGENCE/research-claim.contract.md) | Claim support is evaluated against exact relevant spans. Repetition, cryptographic integrity, and absence of disproof do not establish truth. | [16-KNOWLEDGE-AND-RESEARCH](README.md) |
| [memory-record](../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md) | Exact user statements, observations, inferences, and summaries remain distinct. Corrections and deletion propagate to all derived retrieval paths. | [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) |
| [provenance-link](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | Each relation has a specific supported meaning and valid endpoints. Co-occurrence and visual proximity do not create a causal edge. | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |
| [context-snapshot](../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md) | Trusted instructions and retrieved data are structurally separated. Critical constraints are preserved exactly and source versions are pinned. | [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
