# 00.04 - Integration Baseline

## Purpose and boundary

This component belongs to [00-MASTER-ARCHITECTURE](../README.md) and owns the coordinated behavior below. Primary construction role: [R01 Architecture Coordinator](../../AGENT-ROLES/R01-ARCHITECTURE-COORDINATOR/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Inspect only the selected local root; capture a read-only baseline; map logical units to observed files; resolve collisions; approve reuse or extension before editing.

**Component invariant:** The source path is established by local inspection, never inferred from a remote project.

**Subsystem invariant:** One canonical owner exists for every authority decision, state record, interface, and observable effect. Planning names never establish that a component already exists.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-00.04.01 / existing-component-inspector](existing-component-inspector.file.README.md) | Inventory local entry points, modules, storage, tests, release assets, and owner-selected directories. Hash the inspected baseline and retain explicit unknowns for inaccessible files. | A project without remote hosting or version-control metadata is inventoried successfully. |
| [CETA-00.04.02 / compatibility-mapper](compatibility-mapper.file.README.md) | Map each logical unit to reuse, extend, or create based on observed interfaces and test evidence. Record language, real file path, owning module, and migration implications before construction. | An existing compliant authorization service is reused through an explicit contract mapping. |
| [CETA-00.04.03 / integration-conflict-detector](integration-conflict-detector.file.README.md) | Detect duplicate authorities, incompatible schemas, conflicting source ownership, and behavior regressions between this plan and the inspected application. Produce minimal affected sets and resolution choices. | Two competing task stores produce a conflict with affected producers and consumers. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| logical_unit | text |
| observed_path | text |
| source_digest | text |
| reuse_decision | enum |
| compatibility_evidence | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[desktop-command](../../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md), [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md), [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md), [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
