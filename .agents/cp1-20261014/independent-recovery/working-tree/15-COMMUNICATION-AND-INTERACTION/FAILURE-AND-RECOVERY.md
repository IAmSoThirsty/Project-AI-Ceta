# 15-COMMUNICATION-AND-INTERACTION - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-15.01.01 / message-session-controller](15.01-CONVERSATION/message-session-controller.file.README.md) | Loading archived history authenticates a new session automatically. |
| [CETA-15.01.02 / conversation-stream-handler](15.01-CONVERSATION/conversation-stream-handler.file.README.md) | An interrupted response is displayed as complete with missing final state. |
| [CETA-15.01.03 / conversation-history-presenter](15.01-CONVERSATION/conversation-history-presenter.file.README.md) | Generated summaries replace original messages in the audit view. |
| [CETA-15.02.01 / speech-input-controller](15.02-VOICE/speech-input-controller.file.README.md) | A low-confidence target name triggers a destructive action without confirmation. |
| [CETA-15.02.02 / speech-output-controller](15.02-VOICE/speech-output-controller.file.README.md) | Sensitive credential content is spoken automatically in a shared environment. |
| [CETA-15.02.03 / voice-session-coordinator](15.02-VOICE/voice-session-coordinator.file.README.md) | The system transcribes its own synthesized speech as a new owner command. |
| [CETA-15.03.01 / communication-channel-registry](15.03-CHANNELS/communication-channel-registry.file.README.md) | A configured channel automatically gains permission to send on the owner's behalf. |
| [CETA-15.03.02 / incoming-message-router](15.03-CHANNELS/incoming-message-router.file.README.md) | A display-name match is treated as proof of owner identity. |
| [CETA-15.03.03 / outgoing-message-controller](15.03-CHANNELS/outgoing-message-controller.file.README.md) | A timeout leads to duplicate sends without checking prior delivery state. |
| [CETA-15.04.01 / attachment-ingestion-controller](15.04-ATTACHMENTS/attachment-ingestion-controller.file.README.md) | A compressed archive expands beyond resource limits or writes outside staging. |
| [CETA-15.04.02 / attachment-type-validator](15.04-ATTACHMENTS/attachment-type-validator.file.README.md) | Executable content is treated as a harmless document because of its filename. |
| [CETA-15.04.03 / attachment-storage-linker](15.04-ATTACHMENTS/attachment-storage-linker.file.README.md) | A cached extraction remains globally readable after its source access is revoked. |
| [CETA-15.05.01 / human-decision-requester](15.05-HUMAN-INTERVENTION/human-decision-requester.file.README.md) | A prompt describes a read while the underlying proposal also includes a write. |
| [CETA-15.05.02 / decision-response-handler](15.05-HUMAN-INTERVENTION/decision-response-handler.file.README.md) | An old approval is reused after the target or content changes. |
| [CETA-15.05.03 / interaction-notification-router](15.05-HUMAN-INTERVENTION/interaction-notification-router.file.README.md) | Notification delivery is treated as evidence that the user approved the action. |
| [CETA-15.06.01 / image-input-controller](15.06-MULTIMODAL-INTERACTION/image-input-controller.file.README.md) | Hidden metadata is exported to a connected runtime without consent. |
| [CETA-15.06.02 / media-context-extractor](15.06-MULTIMODAL-INTERACTION/media-context-extractor.file.README.md) | Unreadable text is fabricated to complete a transcript. |
| [CETA-15.06.03 / multimodal-session-coordinator](15.06-MULTIMODAL-INTERACTION/multimodal-session-coordinator.file.README.md) | Unsupported media is silently omitted while the response claims it was analyzed. |


## Mandatory response model

Validation and compatibility failures stop before privileged work. Authority failures deny the affected action and invalidate stale caches. Resource pressure preserves stop, evidence, and recovery capacity. A partial or uncertain effect is recorded explicitly. Missing evidence is not filled with narrative. Internal data writes use the canonical transaction owner; external actions have separately stated idempotency and compensation rules.

## Recovery sequence

1. Close new admission for the affected scope while preserving safe inspection.
2. Capture the last durable state, exact inputs, observed effects, process or target identity, and evidence gaps.
3. Inspect actual resources and receipts to distinguish committed, absent-confirmed, and uncertain effects.
4. Select safe continuation, authorized compensation, restoration, or a human decision using current authority.
5. Preserve later known revocations, deletion markers, corrections, identity records, conversations, and unsent drafts.
6. Requalify the repaired path and record a recovery report before reopening normal effects.

## Retry and compensation

Safe reads may be retried within the same bounded task. Confirmed idempotent operations preserve their operation key and current authority. Unknown outcomes require reconciliation first. Compensation is a new effect with its own scope and can fail; never describe an irreversible external action as undone because local state changed. For pure analysis and UI units, restart computation or presentation from pinned sources without replaying actions.

## Verification

Inject interruption, stale state, malformed input, resource exhaustion, and lost observations at meaningful boundaries for the units above. A recovery claim requires actual before and after observations and source-bound test records. See [the test matrix](TEST-MATRIX.md).
