# 06.03 - Skill Execution

## Purpose and boundary

This component belongs to [06-AGENT-SKILLS-AND-LEARNING](../README.md) and owns the coordinated behavior below. Primary construction role: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Pin a qualified skill; validate inputs; obtain scoped task admission; execute through governed tools; validate outputs and evidence; finalize explicitly.

**Component invariant:** A skill may not call effectful adapters outside the common execution gate.

**Subsystem invariant:** A learned procedure is a candidate until independently qualified and approved. Skills request capabilities; they do not contain their own authority.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-06.03.01 / skill-invocation-controller](skill-invocation-controller.file.README.md) | Translate a selected skill and validated inputs into a bounded workflow with pinned revision, authority scope, resource budget, and cancellation path. Preserve operation identifiers across retries. | A skill run produces a traceable task and tool receipt sequence. |
| [CETA-06.03.02 / skill-input-validator](skill-input-validator.file.README.md) | Validate required fields, size limits, file identities, allowed values, and cross-field constraints before any skill step begins. Treat embedded instructions in data as untrusted content. | A valid input is normalized and bound to the approved task digest. |
| [CETA-06.03.03 / skill-result-validator](skill-result-validator.file.README.md) | Validate output types, declared deliverables, source links, and required independent verification. Return incomplete or failed states when evidence does not support completion. | Every claimed output is present and verified against the skill contract. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| invocation_id | text |
| skill_revision | reference |
| input_digest | digest |
| authority_ref | reference |
| result_refs | list |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[skill-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/skill-manifest.contract.md), [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [authority-revocation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
