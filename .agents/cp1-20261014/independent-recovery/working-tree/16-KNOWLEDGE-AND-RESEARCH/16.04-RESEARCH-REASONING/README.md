# 16.04 - Research Reasoning

## Purpose and boundary

This component belongs to [16-KNOWLEDGE-AND-RESEARCH](../README.md) and owns the coordinated behavior below. Primary construction role: [R13 Knowledge And Research Engineer](../../AGENT-ROLES/R13-KNOWLEDGE-AND-RESEARCH-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Decompose research questions; compare sources and chronology; assess independence and support; seek disconfirming evidence; state supported findings and unresolved gaps.

**Component invariant:** Multiple copies of the same original report count as one evidence lineage, not independent corroboration.

**Subsystem invariant:** Source integrity, source credibility, claim support, and claim truth are different assessments. Contrary evidence and unknowns remain visible.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-16.04.01 / source-comparison-engine](source-comparison-engine.file.README.md) | Compare source content, dates, methods, provenance, and shared origins. Identify duplicate reporting, disagreement, later corrections, and changes in scope. | Syndicated copies are grouped under their common origin. |
| [CETA-16.04.02 / evidence-weighting-engine](evidence-weighting-engine.file.README.md) | Assess relevance, directness, methodological quality, independence, recency where material, and known uncertainty using an explicit rubric. Keep integrity verification separate from evidential strength. | A direct relevant primary record outweighs unsupported repetition under the declared rubric. |
| [CETA-16.04.03 / claim-verification-planner](claim-verification-planner.file.README.md) | Break assertions into testable subclaims, required evidence, counterevidence searches, and decision thresholds. Preserve speculation as speculation until evidence supports a stronger status. | Each material claim has a defined verification path and current evidence status. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| claim_id | text |
| supporting_sources | list |
| contradicting_sources | list |
| independence_groups | list |
| assessment | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[knowledge-source](../../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md), [research-claim](../../INTERFACE-CONTRACTS/INTELLIGENCE/research-claim.contract.md), [memory-record](../../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md), [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md), [context-snapshot](../../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md), [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
