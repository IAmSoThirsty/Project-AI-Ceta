# State And Evidence contracts

Canonical shared records for state and evidence. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [state-transition](state-transition.contract.md) | [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | One canonical owner mutates the aggregate through expected-version checks. Historical corrections append rather than rewrite prior events. |
| [persistent-checkpoint](persistent-checkpoint.contract.md) | [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | Checkpoints preserve observed effects and continuation, not reusable authentication. Resume validates current authority and target state. |
| [evidence-receipt](evidence-receipt.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md) | Receipts bind exact operation evidence within a declared trust model. Integrity, attribution, observation completeness, and functional success remain separate checks. |
| [provenance-link](provenance-link.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md) | Each relation has a specific supported meaning and valid endpoints. Co-occurrence and visual proximity do not create a causal edge. |
| [verification-result](verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../../23-TESTING-AND-QUALIFICATION/README.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. |
| [recovery-report](recovery-report.contract.md) | [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | Recovery reports actual restored and unresolved state, including drafts and identity preservation. Older backups cannot silently remove known security decisions. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
