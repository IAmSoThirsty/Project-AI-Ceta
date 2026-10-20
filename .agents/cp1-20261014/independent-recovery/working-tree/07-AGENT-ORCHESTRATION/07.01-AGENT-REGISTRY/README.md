# 07.01 - Agent Registry

## Purpose and boundary

This component belongs to [07-AGENT-ORCHESTRATION](../README.md) and owns the coordinated behavior below. Primary construction role: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Register agents and roles; bind authenticated execution identities; match qualified capabilities; expose availability without granting new permissions.

**Component invariant:** A role label never grants capabilities by itself.

**Subsystem invariant:** Agent consensus cannot create authority or factual proof. Builders and final verifiers have distinct assignments and evidence obligations.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-07.01.01 / agent-identity-manifest](agent-identity-manifest.file.README.md) | Define stable agent identity, role, model binding, allowed task classes, capability references, resource bounds, and provenance. Separate runtime instance identity from reusable role definition. | Two instances of the same role remain individually attributable. |
| [CETA-07.01.02 / agent-role-registry](agent-role-registry.file.README.md) | Register role responsibilities, scope, expected deliverables, reviewer separation, and compatible skills. Resolve role revisions for each assignment. | An implementation task and its final review have distinct accountable owners. |
| [CETA-07.01.03 / agent-capability-matcher](agent-capability-matcher.file.README.md) | Match tasks to currently qualified agents using input support, skill dependencies, available resources, and authority constraints. Explain excluded candidates. | A task is assigned only to an agent that meets every required capability. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| agent_id | text |
| role_id | text |
| model_binding | reference |
| capability_refs | list |
| qualification_state | enum |


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
