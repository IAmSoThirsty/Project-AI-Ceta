# 04.06 - Memory Portability

## Purpose and boundary

This component belongs to [04-PERSISTENT-MEMORY](../README.md) and owns the coordinated behavior below. Primary construction role: [R06 Memory And Context Engineer](../../AGENT-ROLES/R06-MEMORY-AND-CONTEXT-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Export authorized records with manifests; validate imports in staging; reconcile identities and conflicts; commit accepted records; verify reconstructability.

**Component invariant:** Importing memory never imports execution credentials or governing authority.

**Subsystem invariant:** Retrieved memory remains evidence with provenance and uncertainty, not an authority source. Deletion, correction, and retention are explicit owner-controlled operations.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-04.06.01 / memory-import-controller](memory-import-controller.file.README.md) | Validate package structure, content digests, schema versions, record access labels, and duplicate identifiers. Stage conflicts for explicit reconciliation before canonical writes. | A valid export is imported with preserved attribution and controlled identifier mapping. |
| [CETA-04.06.02 / memory-export-controller](memory-export-controller.file.README.md) | Export selected authorized records, provenance, corrections, and a completeness manifest in a portable documented format. Apply encryption and redaction according to owner policy. | The export contains exactly the selected records and all permitted necessary source references. |
| [CETA-04.06.03 / memory-reconstruction-validator](memory-reconstruction-validator.file.README.md) | Rebuild a separate test memory view from an export and compare record counts, version links, citations, and deletion markers. Report unavailable external references explicitly. | A round-trip preserves record identity, corrections, and authorized retrieval behavior. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| export_id | text |
| format_revision | text |
| record_count | integer |
| encrypted_payload_ref | reference |
| import_decision | reference |


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
