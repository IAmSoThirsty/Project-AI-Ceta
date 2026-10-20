# 01-CONSTITUTIONAL-GOVERNANCE - interface contract bindings

## Required canonical contracts

| Contract | Semantics | Schema owner |
| --- | --- | --- |
| [policy-decision](../INTERFACE-CONTRACTS/AUTHORITY/policy-decision.contract.md) | Allow applies only to the exact proposal under the specified policy and authority generation. Missing required facts and evaluation errors do not allow execution. | [01-CONSTITUTIONAL-GOVERNANCE](README.md) |
| [governance-packet](../INTERFACE-CONTRACTS/AUTHORITY/governance-packet.contract.md) | Every approval binds the same proposal, eligible authority, and validity interval. Duplicate principal identities never count as distinct quorum votes. | [01-CONSTITUTIONAL-GOVERNANCE](README.md) |
| [principal-identity](../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md) | Identity is stable across credential rotation; display labels never determine identity. Credential references never expose secret values. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |
| [capability-token](../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. | [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) |
| [state-transition](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | One canonical owner mutates the aggregate through expected-version checks. Historical corrections append rather than rewrite prior events. | [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) |


## Binding procedure

Read [common contract rules](../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md). Map these records to the existing local language and transport conventions. Preserve exact semantics, versioning, required fields, denial behavior, and uncertainty. Record actual producer and consumer paths. Do not create private schema variants to avoid integration work.

For each boundary implement valid, malformed, unsupported-version, stale-reference, access-denied, cancellation, and uncertain-outcome fixtures. Verify both producer serialization and consumer behavior on the same pinned contract revision. A transport-level success is not domain completion. Any amendment must name affected consumers, compatibility and migration rules, and renewed qualification obligations.

## Error and verification records

Use [application-error](../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for safe cross-boundary failures and [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for actual acceptance evidence. Preserve exact artifact identities and the distinction between design, implementation, executed tests, and release qualification.
