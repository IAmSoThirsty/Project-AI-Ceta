# 15.04 - Attachments

## Purpose and boundary

This component belongs to [15-COMMUNICATION-AND-INTERACTION](../README.md) and owns the coordinated behavior below. Primary construction role: [R12 Communication And UX Engineer](../../AGENT-ROLES/R12-COMMUNICATION-AND-UX-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Stage bytes; validate type and size; inspect unsafe structures; store under scoped ownership; create source references; ingest only through qualified parsers.

**Component invariant:** Attachment names and declared content types are not trusted as proof of actual format.

**Subsystem invariant:** Incoming messages and media are untrusted content. Outgoing communication requires scoped destination and content authority; interface delivery does not imply human approval.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-15.04.01 / attachment-ingestion-controller](attachment-ingestion-controller.file.README.md) | Stage incoming files, enforce size and decompression limits, calculate digests, classify content, and queue approved extraction. Preserve original bytes separately from derived text. | A valid attachment retains exact bytes and attributable extraction records. |
| [CETA-15.04.02 / attachment-type-validator](attachment-type-validator.file.README.md) | Compare declared type, file signatures, structure, and allowed parser capabilities. Quarantine ambiguous or active content and report unsupported formats explicitly. | A mislabeled file is handled according to inspected content rather than its extension. |
| [CETA-15.04.03 / attachment-storage-linker](attachment-storage-linker.file.README.md) | Link attachments to conversations, tasks, sources, retention rules, and access scopes without duplicating unrestricted copies. Propagate deletion and source invalidation. | Removing authorized attachment access also prevents future context retrieval. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| attachment_id | text |
| content_digest | digest |
| media_type | text |
| byte_count | integer |
| access_scope | reference |
| scan_result | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[desktop-command](../../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md), [human-decision-request](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md), [human-decision-response](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-response.contract.md), [notification-event](../../INTERFACE-CONTRACTS/USER-INTERACTION/notification-event.contract.md), [inference-request](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S15 Desktop Interface Implementation](../../AGENT-SKILLS/S15-DESKTOP-INTERFACE-IMPLEMENTATION/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
