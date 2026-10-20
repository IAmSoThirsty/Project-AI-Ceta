# User Interaction contracts

Canonical shared records for user interaction. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [desktop-command](desktop-command.contract.md) | [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md) | Native services authenticate and validate each command regardless of renderer state. Effectful commands resolve into approved execution requests. |
| [human-decision-request](human-decision-request.contract.md) | [15-COMMUNICATION-AND-INTERACTION](../../15-COMMUNICATION-AND-INTERACTION/README.md) | The request exposes exact scope and consequences and expires when its proposal changes. Approval is never inferred from viewing or silence. |
| [human-decision-response](human-decision-response.contract.md) | [15-COMMUNICATION-AND-INTERACTION](../../15-COMMUNICATION-AND-INTERACTION/README.md) | The authenticated response binds to one exact current proposal. A revise response creates a new proposal rather than mutating an approved one. |
| [notification-event](notification-event.contract.md) | [15-COMMUNICATION-AND-INTERACTION](../../15-COMMUNICATION-AND-INTERACTION/README.md) | Delivery and acknowledgement are presentation facts, not approval. Private details remain behind authenticated access and critical control paths remain responsive. |
| [application-error](application-error.contract.md) | [00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md) | Errors preserve effect certainty and retry safety. User-facing messages are safe summaries with access-controlled diagnostics; unknown codes never imply success. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
