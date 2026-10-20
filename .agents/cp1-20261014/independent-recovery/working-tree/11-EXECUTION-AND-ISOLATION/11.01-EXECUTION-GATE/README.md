# 11.01 - Execution Gate

## Purpose and boundary

This component belongs to [11-EXECUTION-AND-ISOLATION](../README.md) and owns the coordinated behavior below. Primary construction role: [R10 Tool And Execution Engineer](../../AGENT-ROLES/R10-TOOL-AND-EXECUTION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Validate immutable operation inputs; verify current authority; reserve resources and evidence capacity; atomically record admission; dispatch through qualified isolation.

**Component invariant:** A missing, stale, revoked, or mismatched prerequisite prevents dispatch.

**Subsystem invariant:** Authorization is bound to exact inputs and target identity and rechecked at the effect boundary. Isolation is qualified on the actual operating environment.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-11.01.01 / execution-request-validator](execution-request-validator.file.README.md) | Validate operation identity, immutable inputs, target identity, tool revision, intended effects, deadlines, and evidence requirements. Compare the normalized request digest to the approved proposal. | The admitted request exactly matches the reviewed operation and target. |
| [CETA-11.01.02 / authorization-proof-checker](authorization-proof-checker.file.README.md) | Validate capability signatures, audience, subject binding, policy generation, delegation ancestry, expiry, revocation, and usage state immediately before effect admission. | A currently valid scoped capability admits only its bound operation. |
| [CETA-11.01.03 / execution-gate-controller](execution-gate-controller.file.README.md) | Coordinate request validation, authority checking, resource and evidence reservations, single-use admission, isolated dispatch, and outcome recording. Use durable operation state and fencing to prevent duplicate starts. | Competing dispatch attempts for the same single-use operation produce at most one admitted effect. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| operation_id | text |
| proposal_digest | digest |
| capability_ref | reference |
| target_identity | record |
| admission_generation | integer |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[execution-request](../../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md), [intended-effect](../../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md), [isolation-context](../../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md), [stop-signal](../../INTERFACE-CONTRACTS/EXECUTION/stop-signal.contract.md), [uncertain-operation](../../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [capability-token](../../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
