# 22-DESKTOP-AND-USER-EXPERIENCE - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [desktop-command](../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md) | Native services authenticate and validate each command regardless of renderer state. Effectful commands resolve into approved execution requests. | [22-DESKTOP-AND-USER-EXPERIENCE](README.md) |
| [human-decision-request](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | The request exposes exact scope and consequences and expires when its proposal changes. Approval is never inferred from viewing or silence. | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [human-decision-response](../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-response.contract.md) | The authenticated response binds to one exact current proposal. A revise response creates a new proposal rather than mutating an approved one. | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [notification-event](../INTERFACE-CONTRACTS/USER-INTERACTION/notification-event.contract.md) | Delivery and acknowledgement are presentation facts, not approval. Private details remain behind authenticated access and critical control paths remain responsive. | [15-COMMUNICATION-AND-INTERACTION](../15-COMMUNICATION-AND-INTERACTION/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |
| [recovery-report](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md) | Recovery reports actual restored and unresolved state, including drafts and identity preservation. Older backups cannot silently remove known security decisions. | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
