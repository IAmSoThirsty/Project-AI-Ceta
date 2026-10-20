# 08.03 - Durable Execution

## Purpose and boundary

This component belongs to [08-TASK-AND-WORKFLOW-ENGINE](../README.md) and owns the coordinated behavior below. Primary construction role: [R08 Workflow And Automation Engineer](../../AGENT-ROLES/R08-WORKFLOW-AND-AUTOMATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Persist admission and operation identity; launch the worker; checkpoint at safe boundaries; reconcile receipts after interruption; resume only validated remaining work.

**Component invariant:** Checkpoint restoration restores intent and observations, not expired authority.

**Subsystem invariant:** Durable orchestration does not guarantee exactly-once external effects. Unknown outcomes require reconciliation before replay or compensation.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-08.03.01 / durable-task-runner](durable-task-runner.file.README.md) | Run admitted nodes with stable operation identifiers, lease fencing, resource budgets, and durable attempt records. Use a transactional publication mechanism for work and result notifications. | Restart after dispatch discovers the prior attempt rather than creating a hidden duplicate. |
| [CETA-08.03.02 / task-checkpoint-controller](task-checkpoint-controller.file.README.md) | Capture task state, pinned inputs, model and skill revisions, committed effects, outstanding operations, and continuation position. Validate a checkpoint before marking it recoverable. | A checkpoint restores exact completed and remaining steps. |
| [CETA-08.03.03 / interrupted-task-resumer](interrupted-task-resumer.file.README.md) | Classify interruption state, revalidate dependencies and authority, inspect unknown effects, and resume only safe remaining steps. Request renewal where consent or capability expired. | A completed file write is observed and not repeated after restart. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| run_id | text |
| attempt | integer |
| idempotency_key | text |
| checkpoint_ref | reference |
| effect_ledger_ref | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [workflow-transition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/workflow-transition.contract.md), [persistent-checkpoint](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md), [uncertain-operation](../../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md).
