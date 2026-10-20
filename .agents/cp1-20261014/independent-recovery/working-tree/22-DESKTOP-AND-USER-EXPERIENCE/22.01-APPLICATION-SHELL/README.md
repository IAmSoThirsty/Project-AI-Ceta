# 22.01 - Application Shell

## Purpose and boundary

This component belongs to [22-DESKTOP-AND-USER-EXPERIENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R12 Communication And UX Engineer](../../AGENT-ROLES/R12-COMMUNICATION-AND-UX-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Launch a restricted shell; establish authenticated native communication; restore safe layout; activate routes from runtime readiness; preserve owner control during partial failures.

**Component invariant:** Opening a view does not grant its displayed capability.

**Subsystem invariant:** Visual state is derived from authenticated native state. A disabled button is not a security boundary; every command is validated again by the runtime.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-22.01.01 / desktop-shell-controller](desktop-shell-controller.file.README.md) | Own application startup presentation, authenticated native bridge, top-level error containment, and global stop access. Keep privileged operations in native services rather than renderer state. | A compromised or malformed view request is rejected by native command validation. |
| [CETA-22.01.02 / application-navigation-router](application-navigation-router.file.README.md) | Route between projects, tasks, memory, evidence, settings, and maintenance with scoped state and deep-link validation. Prevent stale views from acting on a different active project. | Switching projects invalidates stale action contexts while preserving unsaved drafts safely. |
| [CETA-22.01.03 / window-state-manager](window-state-manager.file.README.md) | Persist size, position, panels, and accessibility preferences with bounds checking and multi-display recovery. Separate layout restoration from task execution. | A window restored after display changes remains visible and usable. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| window_id | text |
| route_id | text |
| session_ref | reference |
| view_generation | integer |
| persisted_layout | record |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[desktop-command](../../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md), [human-decision-request](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md), [human-decision-response](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-response.contract.md), [notification-event](../../INTERFACE-CONTRACTS/USER-INTERACTION/notification-event.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S15 Desktop Interface Implementation](../../AGENT-SKILLS/S15-DESKTOP-INTERFACE-IMPLEMENTATION/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).
