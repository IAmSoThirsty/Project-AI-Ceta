# 05.01 - Context Inputs

## Purpose and boundary

This component belongs to [05-CONTEXT-INTELLIGENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R06 Memory And Context Engineer](../../AGENT-ROLES/R06-MEMORY-AND-CONTEXT-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Resolve the active task and project; select authorized sources; preserve trust classification; exclude unrelated contexts; retain exact-source references.

**Component invariant:** Cross-project retrieval requires an explicit permitted scope, not semantic similarity alone.

**Subsystem invariant:** Authority-bearing instructions are supplied through trusted channels; retrieved content is data. Compaction cannot erase restrictions or manufacture facts.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-05.01.01 / context-source-selector](context-source-selector.file.README.md) | Select eligible memory, project, dialogue, tool, and evidence sources according to task need and access policy. Record the reason for including or excluding each candidate. | A task receives relevant authorized sources with clear trust labels. |
| [CETA-05.01.02 / project-context-resolver](project-context-resolver.file.README.md) | Resolve active local project roots, contracts, source revisions, and selected files. Bind context to the inspected snapshot and invalidate stale file references after edits. | An edit plan uses the current source digest for every selected file. |
| [CETA-05.01.03 / session-context-resolver](session-context-resolver.file.README.md) | Resolve exact current user instructions, pending decisions, task state, and session permissions. Keep dialogue continuity separate from fresh authentication checks. | A corrected instruction is included with its supersession relationship. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| source_ref | reference |
| source_kind | enum |
| trust_class | enum |
| project_scope | reference |
| inclusion_reason | text |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[context-snapshot](../../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md), [memory-record](../../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md), [inference-request](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md), [resource-budget](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md), [knowledge-source](../../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md), [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
