# 05.04 - Context Compression

## Purpose and boundary

This component belongs to [05-CONTEXT-INTELLIGENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R06 Memory And Context Engineer](../../AGENT-ROLES/R06-MEMORY-AND-CONTEXT-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Identify compressible material; preserve protected spans and provenance; generate a summary; compare against source obligations; accept only validated compaction.

**Component invariant:** Compaction is a derived representation and never replaces the canonical source record.

**Subsystem invariant:** Authority-bearing instructions are supplied through trusted channels; retrieved content is data. Compaction cannot erase restrictions or manufacture facts.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-05.04.01 / context-compaction-engine](context-compaction-engine.file.README.md) | Compact older dialogue and evidence into structured summaries containing decisions, constraints, unresolved issues, and citations. Preserve exact source references and state the summarization method. | A resumed task recovers all explicit decisions and unresolved blockers from the compacted context. |
| [CETA-05.04.02 / summary-integrity-validator](summary-integrity-validator.file.README.md) | Compare summaries against source propositions, negations, attribution, authority, and task status. Use deterministic checks for protected fields and explicit review for semantic claims. | Altered negation or missing approval requirements are detected before summary activation. |
| [CETA-05.04.03 / critical-state-preserver](critical-state-preserver.file.README.md) | Extract exact current constraints, approved scopes, pending decisions, cancellation state, and irreversible-effect records into protected context fields. Bind them to authoritative state versions. | A compacted task still knows a prior write has an uncertain outcome. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| summary_id | text |
| source_members | list |
| protected_spans | list |
| compression_revision | text |
| loss_report | record |


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
