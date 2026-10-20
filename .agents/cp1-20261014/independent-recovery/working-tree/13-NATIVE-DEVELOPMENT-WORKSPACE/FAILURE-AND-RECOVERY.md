# 13-NATIVE-DEVELOPMENT-WORKSPACE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-13.01.01 / workspace-project-registry](13.01-PROJECT-MANAGEMENT/workspace-project-registry.file.README.md) | Two folders with the same display name share permissions accidentally. |
| [CETA-13.01.02 / project-session-controller](13.01-PROJECT-MANAGEMENT/project-session-controller.file.README.md) | A project switch carries a previous project's active execution permission. |
| [CETA-13.01.03 / project-structure-explorer](13.01-PROJECT-MANAGEMENT/project-structure-explorer.file.README.md) | A directory link expands outside the selected root without an authorized scope change. |
| [CETA-13.02.01 / source-document-controller](13.02-SOURCE-EDITOR/source-document-controller.file.README.md) | An external edit is lost when an old buffer autosaves. |
| [CETA-13.02.02 / editor-state-manager](13.02-SOURCE-EDITOR/editor-state-manager.file.README.md) | Restored editor state writes old draft content directly into current source. |
| [CETA-13.02.03 / editor-diagnostics-presenter](13.02-SOURCE-EDITOR/editor-diagnostics-presenter.file.README.md) | A stale error marker is shown as current after the underlying file changed. |
| [CETA-13.03.01 / file-diff-presenter](13.03-CHANGE-INSPECTION/file-diff-presenter.file.README.md) | A large omitted section contains an undisclosed destructive change. |
| [CETA-13.03.02 / change-staging-controller](13.03-CHANGE-INSPECTION/change-staging-controller.file.README.md) | Later edits enter an already approved staging set unnoticed. |
| [CETA-13.03.03 / change-history-viewer](13.03-CHANGE-INSPECTION/change-history-viewer.file.README.md) | A deleted branch or renamed workspace makes accepted history unverifiable. |
| [CETA-13.04.01 / terminal-session-controller](13.04-TERMINAL-WORKSPACE/terminal-session-controller.file.README.md) | An interactive terminal inherits unrestricted host credentials. |
| [CETA-13.04.02 / command-output-presenter](13.04-TERMINAL-WORKSPACE/command-output-presenter.file.README.md) | Sensitive environment values are displayed or persisted without permission. |
| [CETA-13.04.03 / terminal-lifecycle-manager](13.04-TERMINAL-WORKSPACE/terminal-lifecycle-manager.file.README.md) | A closed terminal leaves hidden child processes running with stale authority. |
| [CETA-13.05.01 / source-control-adapter](13.05-VERSION-CONTROL/source-control-adapter.file.README.md) | Missing external version-control metadata prevents all workspace use. |
| [CETA-13.05.02 / isolated-workspace-manager](13.05-VERSION-CONTROL/isolated-workspace-manager.file.README.md) | Isolation copies confidential files outside the authorized project scope. |
| [CETA-13.05.03 / revision-comparison-controller](13.05-VERSION-CONTROL/revision-comparison-controller.file.README.md) | A forceful replacement discards local work to match an agent-produced tree. |
| [CETA-13.06.01 / application-preview-controller](13.06-DEVELOPMENT-PREVIEW/application-preview-controller.file.README.md) | A development server binds to an unrestricted network interface without approval. |
| [CETA-13.06.02 / visual-inspection-presenter](13.06-DEVELOPMENT-PREVIEW/visual-inspection-presenter.file.README.md) | A static image is treated as proof that the displayed control works. |
| [CETA-13.06.03 / workspace-recovery-controller](13.06-DEVELOPMENT-PREVIEW/workspace-recovery-controller.file.README.md) | Restoring interface state automatically reruns an earlier destructive command. |


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
