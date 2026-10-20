# 17.01 - Evidence Capture

## Purpose and boundary

This component belongs to [17-EVIDENCE-AND-PROVENANCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R14 Evidence And Provenance Engineer](../../AGENT-ROLES/R14-EVIDENCE-AND-PROVENANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Reserve evidence capacity; capture authenticated operation events and artifacts; persist causal ordering; redact by policy; report capture gaps before final verification.

**Component invariant:** An absent observation is not proof that an effect did not occur.

**Subsystem invariant:** Cryptographic integrity proves binding and tamper evidence within a stated trust model; it does not prove claim truth or complete observation. Nondeterministic inference is replayed from recorded outputs or explicitly rerun as a new experiment.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-17.01.01 / execution-evidence-collector](execution-evidence-collector.file.README.md) | Collect gate decisions, dispatch, process identity, target observations, stop events, and outcomes with causal correlation and sequence tracking. Detect gaps and bounded-buffer loss. | A complete operation has an ordered evidence path from authorization to observed outcome. |
| [CETA-17.01.02 / input-output-recorder](input-output-recorder.file.README.md) | Preserve approved exact inputs and observed outputs or permitted digests with source mappings, sensitivity labels, and retention rules. Distinguish raw and normalized forms. | An auditor can identify the exact bytes or authorized digest used in an operation. |
| [CETA-17.01.03 / evidence-artifact-register](evidence-artifact-register.file.README.md) | Register artifact identity, content digest, media type, producer operation, storage reference, retention, and access scope. Detect duplicate identities with differing bytes. | A claimed deliverable resolves to the exact registered artifact content. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| event_id | text |
| operation_id | text |
| event_sequence | integer |
| source_identity | reference |
| artifact_refs | list |


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
