# 04.03 - Memory Consolidation

## Purpose and boundary

This component belongs to [04-PERSISTENT-MEMORY](../README.md) and owns the coordinated behavior below. Primary construction role: [R06 Memory And Context Engineer](../../AGENT-ROLES/R06-MEMORY-AND-CONTEXT-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Select eligible memory versions; group related content; preserve conflicts and exact evidence; propose consolidated records; retain reversible lineage.

**Component invariant:** Consolidation cannot discard explicit corrections, consent restrictions, or contrary evidence.

**Subsystem invariant:** Retrieved memory remains evidence with provenance and uncertainty, not an authority source. Deletion, correction, and retention are explicit owner-controlled operations.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-04.03.01 / memory-consolidation-engine](memory-consolidation-engine.file.README.md) | Combine redundant records into attributed summaries with complete source membership and version lineage. Preserve canonical originals according to retention policy. | A consolidated summary can expand to every source record it represents. |
| [CETA-04.03.02 / memory-conflict-resolver](memory-conflict-resolver.file.README.md) | Detect contradictory propositions, changed preferences, and invalidated facts. Resolve only through explicit source precedence or recorded owner decisions, otherwise retain the conflict. | A direct user correction supersedes a prior inferred preference with a visible history link. |
| [CETA-04.03.03 / memory-significance-analyzer](memory-significance-analyzer.file.README.md) | Rank retention and retrieval value using explicit criteria such as task relevance, user marking, repetition source diversity, and future obligations. Keep scoring separate from truth and permission. | A user-pinned decision remains important even when rarely accessed. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| candidate_refs | list |
| synthesis_ref | reference |
| contradiction_set | list |
| significance_score | bounded-number |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[memory-record](../../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md), [knowledge-source](../../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md), [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md), [persistent-checkpoint](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md), [authority-revocation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md), [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md).
