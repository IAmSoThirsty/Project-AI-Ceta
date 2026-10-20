# Execution contracts

Canonical shared records for execution. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [execution-request](execution-request.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | The normalized immutable request is approved before dispatch and is compared again at use time. Any changed input, effect, tool revision, or target requires reevaluation. |
| [intended-effect](intended-effect.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Every transitive effect is declared. Reversibility describes an actual compensating mechanism, not merely local state rollback. |
| [execution-result](execution-result.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Complete requires declared outputs and observed effects. Cancellation and uncertainty preserve already committed effects; an exit code does not override contradictory observations. |
| [isolation-context](isolation-context.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Required restrictions must be qualified and observed active for the actual worker generation. Unsupported restrictions block the affected action. |
| [stop-signal](stop-signal.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Stop closes new admission before waiting for worker acknowledgement. Requested, acknowledged, terminated, and effects-reconciled are separately observed stages. |
| [uncertain-operation](uncertain-operation.contract.md) | [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Uncertainty is a durable state requiring target inspection or authoritative receipts before replay. A new attempt or compensation requires current authority. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
