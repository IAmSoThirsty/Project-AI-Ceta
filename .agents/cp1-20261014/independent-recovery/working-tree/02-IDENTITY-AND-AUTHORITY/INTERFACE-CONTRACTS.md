# 02-IDENTITY-AND-AUTHORITY - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [principal-identity](../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md) | Identity is stable across credential rotation; display labels never determine identity. Credential references never expose secret values. | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authenticated-session](../INTERFACE-CONTRACTS/AUTHORITY/authenticated-session.contract.md) | A restored conversation is not a restored authenticated session. Every privileged use checks current session and binding generation. | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [capability-token](../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authority-delegation](../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. | [02-IDENTITY-AND-AUTHORITY](README.md) |
| [authority-revocation](../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md) | Revocation is durable, generation-ordered, and propagated to descendants and active admission checks. Known revocations survive restoration of older application data. | [02-IDENTITY-AND-AUTHORITY](README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
