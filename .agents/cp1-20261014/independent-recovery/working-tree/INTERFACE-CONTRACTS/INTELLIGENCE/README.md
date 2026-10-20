# Intelligence contracts

Canonical shared records for intelligence. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [model-manifest](model-manifest.contract.md) | [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md) | Declared capabilities and observed qualification are recorded separately. A configured endpoint or downloaded artifact is not necessarily ready for inference. |
| [inference-request](inference-request.contract.md) | [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md) | Inputs, model revision, context, and data destination are pinned. Fallback that changes locality requires an explicit new data-export decision. |
| [inference-response](inference-response.contract.md) | [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md) | Model content and tool proposals are untrusted outputs requiring downstream validation. Partial streams cannot trigger incomplete action arguments. |
| [memory-record](memory-record.contract.md) | [04-PERSISTENT-MEMORY](../../04-PERSISTENT-MEMORY/README.md) | Exact user statements, observations, inferences, and summaries remain distinct. Corrections and deletion propagate to all derived retrieval paths. |
| [context-snapshot](context-snapshot.contract.md) | [05-CONTEXT-INTELLIGENCE](../../05-CONTEXT-INTELLIGENCE/README.md) | Trusted instructions and retrieved data are structurally separated. Critical constraints are preserved exactly and source versions are pinned. |
| [knowledge-source](knowledge-source.contract.md) | [16-KNOWLEDGE-AND-RESEARCH](../../16-KNOWLEDGE-AND-RESEARCH/README.md) | Original bytes, extraction, and normalized interpretation are separate artifacts. Dates retain their distinct meanings and unknown values remain unknown. |
| [research-claim](research-claim.contract.md) | [16-KNOWLEDGE-AND-RESEARCH](../../16-KNOWLEDGE-AND-RESEARCH/README.md) | Claim support is evaluated against exact relevant spans. Repetition, cryptographic integrity, and absence of disproof do not establish truth. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
