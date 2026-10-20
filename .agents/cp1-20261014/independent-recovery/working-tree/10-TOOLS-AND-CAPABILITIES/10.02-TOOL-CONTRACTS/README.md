# 10.02 - Tool Contracts

## Purpose and boundary

This component belongs to [10-TOOLS-AND-CAPABILITIES](../README.md) and owns the coordinated behavior below. Primary construction role: [R10 Tool And Execution Engineer](../../AGENT-ROLES/R10-TOOL-AND-EXECUTION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Validate exact arguments; classify all intended effects; bind normalized input to approval; validate returned observations before consumers use them.

**Component invariant:** Unknown effects require explicit classification or denial rather than a permissive default.

**Subsystem invariant:** Tools declare effects before execution and return observations after execution. Discovery or selection never grants authority.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-10.02.01 / tool-input-validator](tool-input-validator.file.README.md) | Validate required fields, sizes, encodings, ranges, cross-field constraints, and target identities. Produce a canonical normalized argument record before authorization. | The approved argument digest matches the dispatched normalized arguments. |
| [CETA-10.02.02 / tool-output-validator](tool-output-validator.file.README.md) | Validate output schema, completion status, artifact references, size limits, and effect observations. Quarantine malformed results while retaining raw diagnostic evidence under access control. | A valid result is accepted with exact artifact and receipt references. |
| [CETA-10.02.03 / tool-effect-classifier](tool-effect-classifier.file.README.md) | Map tool arguments to reads, writes, process launches, network transfers, messages, and irreversible actions using the declared implementation contract. Include transitive effects. | A command that writes and sends data declares both effects before approval. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| invocation_ref | reference |
| normalized_arguments | record |
| declared_effects | list |
| result_schema | text |
| validation_status | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[tool-manifest](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-manifest.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md), [tool-result](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-result.contract.md), [intended-effect](../../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md), [execution-request](../../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
