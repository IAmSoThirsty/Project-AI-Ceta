# 17.03 - Provenance Graphs

## Purpose and boundary

This component belongs to [17-EVIDENCE-AND-PROVENANCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R14 Evidence And Provenance Engineer](../../AGENT-ROLES/R14-EVIDENCE-AND-PROVENANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Link inputs, transformations, decisions, and outputs; index lineage; validate references and causal order; expose gaps and cycles inconsistent with the relation type.

**Component invariant:** Provenance relationships describe evidence lineage and cannot manufacture missing observations.

**Subsystem invariant:** Cryptographic integrity proves binding and tamper evidence within a stated trust model; it does not prove claim truth or complete observation. Nondeterministic inference is replayed from recorded outputs or explicitly rerun as a new experiment.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-17.03.01 / provenance-relationship-builder](provenance-relationship-builder.file.README.md) | Create typed links for derived-from, authorized-by, produced-by, verified-by, supersedes, and contradicts. Require valid source and target records and explicit transformation identity. | A delivered artifact traces back to source inputs, approval, and producing operation. |
| [CETA-17.03.02 / evidence-lineage-index](evidence-lineage-index.file.README.md) | Index forward and reverse lineage with access filtering, version awareness, and efficient impact queries. Rebuild from canonical evidence records. | Revoking an input source identifies all affected derived artifacts. |
| [CETA-17.03.03 / provenance-chain-validator](provenance-chain-validator.file.README.md) | Validate complete chains for referential integrity, digest binding, causal ordering, and required trust boundaries. Report truncation and missing anchors explicitly. | A chain with all required observations and signatures passes the declared verification profile. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| node_id | text |
| relation_type | enum |
| parent_refs | list |
| transformation_ref | reference |
| graph_generation | integer |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md), [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
