# 22-DESKTOP-AND-USER-EXPERIENCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-22.01.01 / desktop-shell-controller](22.01-APPLICATION-SHELL/desktop-shell-controller.file.README.md) | Renderer-visible state is trusted as proof of owner authorization. |
| [CETA-22.01.02 / application-navigation-router](22.01-APPLICATION-SHELL/application-navigation-router.file.README.md) | A deep link injects an arbitrary native command. |
| [CETA-22.01.03 / window-state-manager](22.01-APPLICATION-SHELL/window-state-manager.file.README.md) | Restoring a window repeats the last effectful action automatically. |
| [CETA-22.02.01 / system-overview-dashboard](22.02-COMMAND-CENTER/system-overview-dashboard.file.README.md) | A green summary masks a failed mandatory enforcement service. |
| [CETA-22.02.02 / active-task-dashboard](22.02-COMMAND-CENTER/active-task-dashboard.file.README.md) | An estimated progress percentage is presented as proof of completion. |
| [CETA-22.02.03 / operational-health-presenter](22.02-COMMAND-CENTER/operational-health-presenter.file.README.md) | A missing heartbeat is converted into a fabricated success status. |
| [CETA-22.03.01 / agent-activity-dashboard](22.03-AGENT-CONTROL/agent-activity-dashboard.file.README.md) | A previous agent's heartbeat keeps a new failed instance marked healthy. |
| [CETA-22.03.02 / agent-task-inspector](22.03-AGENT-CONTROL/agent-task-inspector.file.README.md) | A summarized task description omits a consequential planned effect. |
| [CETA-22.03.03 / agent-capability-viewer](22.03-AGENT-CONTROL/agent-capability-viewer.file.README.md) | A capability listing is treated as a grant merely because it is visible. |
| [CETA-22.04.01 / authorization-request-view](22.04-GOVERNANCE-INTERFACE/authorization-request-view.file.README.md) | A hidden field changes the approved action while the visible summary remains unchanged. |
| [CETA-22.04.02 / authority-delegation-view](22.04-GOVERNANCE-INTERFACE/authority-delegation-view.file.README.md) | A convenience preset silently grants all resources or indefinite duration. |
| [CETA-22.04.03 / governance-decision-history](22.04-GOVERNANCE-INTERFACE/governance-decision-history.file.README.md) | A later rule revision rewrites the apparent basis of an earlier decision. |
| [CETA-22.05.01 / companion-conversation-view](22.05-INTELLIGENCE-INTERFACE/companion-conversation-view.file.README.md) | Generated text is visually presented as a direct user instruction. |
| [CETA-22.05.02 / memory-explorer-view](22.05-INTELLIGENCE-INTERFACE/memory-explorer-view.file.README.md) | A deletion control removes only the visible row while derived retrieval remains active. |
| [CETA-22.05.03 / context-inspection-view](22.05-INTELLIGENCE-INTERFACE/context-inspection-view.file.README.md) | A context view exposes restricted source content through an explanation panel. |
| [CETA-22.06.01 / evidence-timeline-view](22.06-EVIDENCE-INTERFACE/evidence-timeline-view.file.README.md) | Missing event ranges are hidden by a continuous-looking line. |
| [CETA-22.06.02 / provenance-graph-view](22.06-EVIDENCE-INTERFACE/provenance-graph-view.file.README.md) | Visual closeness is presented as evidence of a relationship absent from the graph data. |
| [CETA-22.06.03 / execution-verification-view](22.06-EVIDENCE-INTERFACE/execution-verification-view.file.README.md) | A valid signature turns every other verification indicator green. |
| [CETA-22.07.01 / application-settings-controller](22.07-USER-CONTROLS/application-settings-controller.file.README.md) | A visual preference inadvertently changes authority or data-export policy. |
| [CETA-22.07.02 / accessibility-preferences](22.07-USER-CONTROLS/accessibility-preferences.file.README.md) | A critical decision is inaccessible because it relies only on a transient animation. |
| [CETA-22.07.03 / notification-preferences](22.07-USER-CONTROLS/notification-preferences.file.README.md) | A private message body appears in a public notification despite hidden-preview settings. |
| [CETA-22.08.01 / first-run-setup-controller](22.08-OWNER-ONBOARDING/first-run-setup-controller.file.README.md) | A partially completed setup enables privileged operations before ownership is established. |
| [CETA-22.08.02 / hardware-qualification-view](22.08-OWNER-ONBOARDING/hardware-qualification-view.file.README.md) | A compatibility estimate is displayed as a completed benchmark. |
| [CETA-22.08.03 / local-ownership-verification](22.08-OWNER-ONBOARDING/local-ownership-verification.file.README.md) | Merely being the first process to launch the interface grants unrestricted ownership. |
| [CETA-22.09.01 / backup-management-view](22.09-NATIVE-MAINTENANCE/backup-management-view.file.README.md) | An archive creation success is presented as proof of complete recoverability. |
| [CETA-22.09.02 / restore-and-repair-view](22.09-NATIVE-MAINTENANCE/restore-and-repair-view.file.README.md) | A repair button silently deletes databases or resets ownership. |
| [CETA-22.09.03 / application-update-view](22.09-NATIVE-MAINTENANCE/application-update-view.file.README.md) | A newer package is substituted after approval without a fresh decision. |


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
