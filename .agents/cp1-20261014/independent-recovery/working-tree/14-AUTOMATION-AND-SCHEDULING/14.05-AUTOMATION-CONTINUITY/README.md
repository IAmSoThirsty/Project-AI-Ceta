# 14.05 - Automation Continuity

## Purpose and boundary

This component belongs to [14-AUTOMATION-AND-SCHEDULING](../README.md) and owns the coordinated behavior below. Primary construction role: [R08 Workflow And Automation Engineer](../../AGENT-ROLES/R08-WORKFLOW-AND-AUTOMATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Reconcile downtime and event gaps; apply approved catch-up rules; renew authority where needed; recover task links; record actual outcomes and remaining uncertainty.

**Component invariant:** Catch-up behavior cannot create a burst of unapproved or stale effects.

**Subsystem invariant:** A schedule grants no more authority than its approved scope and lifetime. Missed triggers are reconciled according to an explicit policy, not blindly replayed.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-14.05.01 / missed-trigger-reconciler](missed-trigger-reconciler.file.README.md) | Compare persisted occurrence history with the schedule across downtime. Apply explicit skip, latest-only, or bounded catch-up behavior and preserve the reason for each decision. | A long outage produces only the configured bounded catch-up set. |
| [CETA-14.05.02 / automation-recovery-controller](automation-recovery-controller.file.README.md) | Restore scheduler leases, occurrence claims, task references, and event subscriptions. Inspect actual task state before redispatch and fence stale scheduler instances. | Recovery reconnects an already running task rather than launching another copy. |
| [CETA-14.05.03 / automation-outcome-recorder](automation-outcome-recorder.file.README.md) | Record scheduled versus actual times, authority decision, task result, missed-run handling, and evidence references. Distinguish trigger delivery from successful task completion. | A failed task remains a failed automation occurrence despite successful scheduling. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| reconciliation_id | text |
| missed_occurrences | list |
| selected_policy | enum |
| outcome_refs | list |
| schedule_generation | integer |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[scheduled-task](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/scheduled-task.contract.md), [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md), [resource-budget](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md), [workflow-transition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/workflow-transition.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md).

Implement declarations and conformance fixtures before effectful behavior. Use the existing composition mechanism to connect producers and consumers. The internal file list is an ownership map, not a forced call order. Pure checks remain separate from controlled effects, authoritative storage remains with its designated owner, and UI components issue authenticated native commands rather than performing privileged actions themselves.

## Failure and recovery

A malformed record is rejected before privileged work. Missing references, stale versions, invalid authority, and unsupported environment capabilities produce explicit blocked or failed results. An interruption after possible dispatch preserves uncertainty and invokes canonical reconciliation before retry. Keep source and output versions distinct, preserve user drafts and known security decisions, and do not destroy original evidence during repair.

## Construction sequence and acceptance

1. Inspect the mapped local component and record reuse, extension, or creation decisions.
2. Freeze shared contracts and acquire file ownership for the assigned builder.
3. Implement each linked unit and its explicit positive and negative fixtures.
4. Connect the component flow above through real local interfaces and test adverse transitions.
5. Inject interruption, concurrent update, cancellation, and stale-authority conditions where applicable.
6. Hand exact source, output artifacts, and test records to the independent verifier; accept only current evidence.

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md).
