# Authority contracts

Canonical shared records for authority. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [principal-identity](principal-identity.contract.md) | [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | Identity is stable across credential rotation; display labels never determine identity. Credential references never expose secret values. |
| [authenticated-session](authenticated-session.contract.md) | [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | A restored conversation is not a restored authenticated session. Every privileged use checks current session and binding generation. |
| [policy-decision](policy-decision.contract.md) | [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md) | Allow applies only to the exact proposal under the specified policy and authority generation. Missing required facts and evaluation errors do not allow execution. |
| [governance-packet](governance-packet.contract.md) | [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md) | Every approval binds the same proposal, eligible authority, and validity interval. Duplicate principal identities never count as distinct quorum votes. |
| [capability-token](capability-token.contract.md) | [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. |
| [authority-delegation](authority-delegation.contract.md) | [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. |
| [authority-revocation](authority-revocation.contract.md) | [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | Revocation is durable, generation-ordered, and propagated to descendants and active admission checks. Known revocations survive restoration of older application data. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
