# 07.04 - Multiagent Execution

## Purpose and boundary

This component belongs to [07-AGENT-ORCHESTRATION](../README.md) and owns the coordinated behavior below. Primary construction role: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Admit ready assignments; acquire scoped write leases; execute governed work; observe cancellation; resolve conflicts through recorded decisions; release leases.

**Component invariant:** Expired leases fence old workers from further writes.

**Subsystem invariant:** Agent consensus cannot create authority or factual proof. Builders and final verifiers have distinct assignments and evidence obligations.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-07.04.01 / agent-execution-coordinator](agent-execution-coordinator.file.README.md) | Start, pause, stop, and join agent tasks through durable workflow admission. Persist assignments before launch and retain exact worker generations. | A restarted coordinator discovers live assignments without launching duplicates. |
| [CETA-07.04.02 / agent-concurrency-controller](agent-concurrency-controller.file.README.md) | Enforce per-agent and shared resource budgets, write leases, fairness, and lease fencing. Recheck ownership immediately before publishing shared artifacts. | A stale worker cannot write after its lease is reassigned. |
| [CETA-07.04.03 / agent-conflict-arbitrator](agent-conflict-arbitrator.file.README.md) | Detect conflicting edits, divergent results, and incompatible assumptions. Present evidence and contract impact to the designated authority rather than selecting by confidence alone. | Conflicting edits remain isolated until an explicit merge decision is verified. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| assignment_id | text |
| lease_generation | integer |
| worker_state | enum |
| shared_resource | text |
| conflict_record | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[agent-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md), [agent-message](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-message.contract.md), [agent-handoff](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-handoff.contract.md), [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).
