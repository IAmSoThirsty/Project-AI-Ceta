# 11-EXECUTION-AND-ISOLATION - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [execution-request](../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md) | The normalized immutable request is approved before dispatch and is compared again at use time. Any changed input, effect, tool revision, or target requires reevaluation. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [intended-effect](../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md) | Every transitive effect is declared. Reversibility describes an actual compensating mechanism, not merely local state rollback. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [isolation-context](../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md) | Required restrictions must be qualified and observed active for the actual worker generation. Unsupported restrictions block the affected action. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [stop-signal](../INTERFACE-CONTRACTS/EXECUTION/stop-signal.contract.md) | Stop closes new admission before waiting for worker acknowledgement. Requested, acknowledged, terminated, and effects-reconciled are separately observed stages. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [uncertain-operation](../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | Uncertainty is a durable state requiring target inspection or authoritative receipts before replay. A new attempt or compensation requires current authority. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [execution-result](../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | Complete requires declared outputs and observed effects. Cancellation and uncertainty preserve already committed effects; an exit code does not override contradictory observations. | [11-EXECUTION-AND-ISOLATION](README.md) |
| [capability-token](../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
