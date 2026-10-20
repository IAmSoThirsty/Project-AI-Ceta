# 03-COMPANION-INTELLIGENCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-03.01.01 / companion-profile](03.01-COMPANION-IDENTITY/companion-profile.file.README.md) | An inferred preference is promoted into a permanent owner instruction without approval. |
| [CETA-03.01.02 / companion-identity-lifecycle](03.01-COMPANION-IDENTITY/companion-identity-lifecycle.file.README.md) | Importing a profile grants the previous device's credentials. |
| [CETA-03.01.03 / companion-capability-profile](03.01-COMPANION-IDENTITY/companion-capability-profile.file.README.md) | A documented capability is advertised as executable before installation and qualification. |
| [CETA-03.02.01 / conversation-controller](03.02-DIALOGUE-INTELLIGENCE/conversation-controller.file.README.md) | A retry appends the same user turn twice and starts duplicate work. |
| [CETA-03.02.02 / dialogue-state-manager](03.02-DIALOGUE-INTELLIGENCE/dialogue-state-manager.file.README.md) | A generated summary overwrites the user's exact earlier instruction. |
| [CETA-03.02.03 / response-planning-engine](03.02-DIALOGUE-INTELLIGENCE/response-planning-engine.file.README.md) | A plausible narrative is used as proof that an operation occurred. |
| [CETA-03.03.01 / companion-continuity-manager](03.03-CONTINUITY-AND-ADAPTATION/companion-continuity-manager.file.README.md) | Session restoration replays the previous external action automatically. |
| [CETA-03.03.02 / interaction-adaptation-engine](03.03-CONTINUITY-AND-ADAPTATION/interaction-adaptation-engine.file.README.md) | Repeated user frustration is interpreted as authorization to bypass approval. |
| [CETA-03.03.03 / continuity-recovery-controller](03.03-CONTINUITY-AND-ADAPTATION/continuity-recovery-controller.file.README.md) | Unavailable conversation content is invented to make the history appear complete. |
| [CETA-03.04.01 / initiative-proposal-engine](03.04-INITIATIVE-AND-DELIBERATION/initiative-proposal-engine.file.README.md) | A proposal expands from one selected project into unrelated local directories. |
| [CETA-03.04.02 / collaborative-deliberation-engine](03.04-INITIATIVE-AND-DELIBERATION/collaborative-deliberation-engine.file.README.md) | A majority of agents is treated as proof that a factual claim is true. |
| [CETA-03.04.03 / initiative-authority-filter](03.04-INITIATIVE-AND-DELIBERATION/initiative-authority-filter.file.README.md) | A task goal is treated as blanket authorization for every possible means. |
| [CETA-03.05.01 / companion-task-coordinator](03.05-COMPANION-OPERATIONS/companion-task-coordinator.file.README.md) | A task is marked complete because the model stopped generating text. |
| [CETA-03.05.02 / companion-tool-requester](03.05-COMPANION-OPERATIONS/companion-tool-requester.file.README.md) | Tool arguments contain hidden additional writes not declared in the proposal. |
| [CETA-03.05.03 / companion-activity-presenter](03.05-COMPANION-OPERATIONS/companion-activity-presenter.file.README.md) | Optimistic UI state is displayed as a completed operation before confirmation. |


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
