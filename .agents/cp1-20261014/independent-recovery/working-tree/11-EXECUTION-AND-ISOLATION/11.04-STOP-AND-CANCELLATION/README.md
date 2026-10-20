# 11.04 - Stop And Cancellation

## Purpose and boundary

This component belongs to [11-EXECUTION-AND-ISOLATION](../README.md) and owns the coordinated behavior below. Primary construction role: [R10 Tool And Execution Engineer](../../AGENT-ROLES/R10-TOOL-AND-EXECUTION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome.

**Component invariant:** Stop acknowledgement, worker termination, and effect completion are separate facts.

**Subsystem invariant:** Authorization is bound to exact inputs and target identity and rechecked at the effect boundary. Isolation is qualified on the actual operating environment.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-11.04.01 / stop-signal-controller](stop-signal-controller.file.README.md) | Authenticate stop requests, assign monotonic generations, propagate them to affected tasks and workers, and prevent new descendant work. Keep the control path responsive under resource pressure. | A stop request blocks new effects before waiting for worker acknowledgement. |
| [CETA-11.04.02 / running-operation-terminator](running-operation-terminator.file.README.md) | Apply cooperative cancellation, bounded grace, and qualified process-group termination. Validate process ownership before termination and preserve uncertain external outcomes. | All owned descendants stop within the qualified bound or are explicitly reported as residual. |
| [CETA-11.04.03 / cancellation-evidence-recorder](cancellation-evidence-recorder.file.README.md) | Record request time, admission closure, worker acknowledgements, observed termination, committed effects, and unresolved effects. Avoid describing already completed external effects as undone. | The cancellation report distinguishes prevented, completed, and uncertain effects. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| stop_id | text |
| target_scope | record |
| stop_generation | integer |
| deadline | duration |
| observed_stop_state | enum |


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
