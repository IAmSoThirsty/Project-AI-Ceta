# 08.05 - Workflow Completion

## Purpose and boundary

This component belongs to [08-TASK-AND-WORKFLOW-ENGINE](../README.md) and owns the coordinated behavior below. Primary construction role: [R08 Workflow And Automation Engineer](../../AGENT-ROLES/R08-WORKFLOW-AND-AUTOMATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Collect outputs; validate their content and provenance; run acceptance checks; obtain required independent review; commit a final result with evidence.

**Component invariant:** An incomplete test set cannot become a successful finalization by omission.

**Subsystem invariant:** Durable orchestration does not guarantee exactly-once external effects. Unknown outcomes require reconciliation before replay or compensation.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-08.05.01 / deliverable-validator](deliverable-validator.file.README.md) | Check expected artifacts, paths, schemas, digests, behavior, and completeness against the task contract. Validate real output bytes rather than claimed filenames. | All declared deliverables exist and match their accepted content revisions. |
| [CETA-08.05.02 / completion-evidence-checker](completion-evidence-checker.file.README.md) | Require each acceptance obligation to have an admissible result, exact source binding, execution record, and appropriate verifier. Distinguish missing, stale, failed, and not-executed evidence. | Every required test result is tied to the delivered source and artifact revision. |
| [CETA-08.05.03 / task-finalization-controller](task-finalization-controller.file.README.md) | Atomically seal final task state, result references, unresolved limitations, and evidence summary. Make duplicate finalization idempotent and reject contradictory terminal results. | Repeated finalization returns the same verified result without duplicate events. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| deliverable_ref | reference |
| expected_digest | digest |
| acceptance_result | enum |
| verifier_id | text |
| finalization_version | integer |


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
