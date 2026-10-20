# 00.02 - System Topology

## Purpose and boundary

This component belongs to [00-MASTER-ARCHITECTURE](../README.md) and owns the coordinated behavior below. Primary construction role: [R01 Architecture Coordinator](../../AGENT-ROLES/R01-ARCHITECTURE-COORDINATOR/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Register components; validate unique ownership; distinguish build, runtime, data, and optional dependency edges; expose navigation and impact analysis.

**Component invariant:** An optional integration never becomes a prerequisite for the local baseline.

**Subsystem invariant:** One canonical owner exists for every authority decision, state record, interface, and observable effect. Planning names never establish that a component already exists.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-00.02.01 / subsystem-registry](subsystem-registry.file.README.md) | Register the 25 subsystem identities with versioned exports, readiness states, and lifecycle hooks. Resolve by stable identifier rather than display label and publish a read-only capability view. | A renamed display label preserves references to its stable subsystem identity. |
| [CETA-00.02.02 / component-ownership-map](component-ownership-map.file.README.md) | Assign one implementation owner and a distinct review owner per logical unit. Track storage ownership, shared contract ownership, and permitted consumer access without creating cross-owned files. | An interface amendment identifies every affected owner and consumer. |
| [CETA-00.02.03 / architecture-graph](architecture-graph.file.README.md) | Construct typed dependency graphs, compute strongly connected groups for runtime analysis, and require an acyclic build-prerequisite graph. Generate impact sets without treating message flow as build order. | The build graph has a valid topological ordering and stable impact results. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| subsystem_id | text |
| component_id | text |
| dependency_id | text |
| edge_kind | enum |
| owner_role | text |


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
