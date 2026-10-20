# 06.05 - Skill Lifecycle

## Purpose and boundary

This component belongs to [06-AGENT-SKILLS-AND-LEARNING](../README.md) and owns the coordinated behavior below. Primary construction role: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence.

**Component invariant:** Rollback of skill content cannot restore previously revoked authority.

**Subsystem invariant:** A learned procedure is a candidate until independently qualified and approved. Skills request capabilities; they do not contain their own authority.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-06.05.01 / skill-version-manager](skill-version-manager.file.README.md) | Maintain immutable revisions, migration notes, compatibility requirements, and a controlled active-version pointer. Preserve reproducible references for historical runs. | A rollback selects a previously qualified revision without altering its content. |
| [CETA-06.05.02 / skill-revocation-controller](skill-revocation-controller.file.README.md) | Revoke exact skill revisions or a lineage, prevent new admissions, and signal affected running tasks. Record already committed effects and safe stopping boundaries. | A queued invocation cannot start after its skill revision is revoked. |
| [CETA-06.05.03 / skill-audit-recorder](skill-audit-recorder.file.README.md) | Record discovery, qualification, approval, invocation, update, and revocation events with actor and artifact references. Redact sensitive inputs without erasing accountability. | An auditor reconstructs who approved and invoked a particular skill revision. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| revision_ref | reference |
| supersedes | reference |
| revocation_generation | integer |
| affected_tasks | list |
| audit_refs | list |


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
