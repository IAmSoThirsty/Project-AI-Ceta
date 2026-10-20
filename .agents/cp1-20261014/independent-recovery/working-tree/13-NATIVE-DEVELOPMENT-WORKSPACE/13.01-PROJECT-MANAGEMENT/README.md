# 13.01 - Project Management

## Purpose and boundary

This component belongs to [13-NATIVE-DEVELOPMENT-WORKSPACE](../README.md) and owns the coordinated behavior below. Primary construction role: [R11 Engineering Workspace Engineer](../../AGENT-ROLES/R11-ENGINEERING-WORKSPACE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Open an owner-selected project; validate path boundaries; register the local baseline; restore authorized interface state; expose project structure and health.

**Component invariant:** Switching projects also switches context, resource scope, and pending-decision visibility.

**Subsystem invariant:** The interface presents and proposes changes; native services enforce authority and filesystem boundaries. Local projects remain usable without remote hosting.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-13.01.01 / workspace-project-registry](workspace-project-registry.file.README.md) | Register local project roots, stable identities, trust choices, language metadata, and recent sessions. Detect moved roots and conflicting aliases without merging unrelated projects. | Reopening a moved project requires identity reconciliation and preserves its history. |
| [CETA-13.01.02 / project-session-controller](project-session-controller.file.README.md) | Manage open project sessions, selected files, pending edits, task bindings, and close/reopen behavior. Preserve unsaved drafts separately from committed source. | Closing and reopening restores unsaved editor content without overwriting source. |
| [CETA-13.01.03 / project-structure-explorer](project-structure-explorer.file.README.md) | Display directories, files, generated assets, ignored content, and access boundaries using bounded incremental scans. Surface unreadable paths and link targets accurately. | A large project remains navigable while inaccessible folders are clearly identified. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| workspace_id | text |
| project_id | text |
| selected_root | record |
| active_session | reference |
| source_snapshot | digest |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[desktop-command](../../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md), [human-decision-request](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [persistent-checkpoint](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S15 Desktop Interface Implementation](../../AGENT-SKILLS/S15-DESKTOP-INTERFACE-IMPLEMENTATION/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).
