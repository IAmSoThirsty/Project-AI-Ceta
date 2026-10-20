# 14.04 - Automation Dispatch

## Purpose and boundary

This component belongs to [14-AUTOMATION-AND-SCHEDULING](../README.md) and owns the coordinated behavior below. Primary construction role: [R08 Workflow And Automation Engineer](../../AGENT-ROLES/R08-WORKFLOW-AND-AUTOMATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Claim an occurrence; validate schedule revision and current authority; acquire concurrency and resources; submit a durable task; record admission or blocking reason.

**Component invariant:** Authorization is checked when the scheduled action runs, not only when the schedule was created.

**Subsystem invariant:** A schedule grants no more authority than its approved scope and lifetime. Missed triggers are reconciled according to an explicit policy, not blindly replayed.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-14.04.01 / automation-job-dispatcher](automation-job-dispatcher.file.README.md) | Convert a validated occurrence into a task with exact template revision, inputs, source event, and stable idempotency identity. Persist the occurrence-to-task link before delivery. | Duplicate trigger deliveries resolve to the same admitted task. |
| [CETA-14.04.02 / scheduled-authority-validator](scheduled-authority-validator.file.README.md) | Check current grant scope, expiry, revocation, task inputs, and changed policy at occurrence time. Pause and request renewal when authority no longer covers the action. | An expired recurring grant pauses the next occurrence with a clear renewal request. |
| [CETA-14.04.03 / automation-concurrency-controller](automation-concurrency-controller.file.README.md) | Enforce skip, queue, replace, or overlap behavior as explicitly configured, including resource caps and stop semantics for replacement. Use durable leases. | A nonoverlapping schedule queues or skips according to its approved policy. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| occurrence_ref | reference |
| task_ref | reference |
| authority_generation | integer |
| concurrency_key | text |
| admission_ref | reference |


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
