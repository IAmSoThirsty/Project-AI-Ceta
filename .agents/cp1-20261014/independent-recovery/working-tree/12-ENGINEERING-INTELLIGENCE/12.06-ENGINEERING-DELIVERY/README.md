# 12.06 - Engineering Delivery

## Purpose and boundary

This component belongs to [12-ENGINEERING-INTELLIGENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R11 Engineering Workspace Engineer](../../AGENT-ROLES/R11-ENGINEERING-WORKSPACE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Build from the pinned source; run verification; reconcile documentation and interfaces; report exact deliverables and unresolved obligations; hand off to product qualification.

**Component invariant:** A successful compile alone cannot establish installed product completion.

**Subsystem invariant:** Engineering work operates on inspected local source with scoped file ownership. Generated code, test execution, and verified product behavior are distinct completion stages.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-12.06.01 / build-verification-coordinator](build-verification-coordinator.file.README.md) | Run the locally reconciled build, test, and packaging steps in controlled environments. Bind each result to source, dependencies, configuration, and produced artifacts. | The built artifact is demonstrably produced from the tested source revision. |
| [CETA-12.06.02 / implementation-report-generator](implementation-report-generator.file.README.md) | Produce an evidence-backed report of changed files, contracts, tests, observed outcomes, unresolved issues, and exact artifact references. Keep proposed and executed work separate. | Every completion claim links to a current artifact or test result. |
| [CETA-12.06.03 / documentation-sync-controller](documentation-sync-controller.file.README.md) | Update interface, operation, migration, recovery, and user guidance to match accepted behavior. Validate links and examples against the delivered configuration. | Documentation describes actual qualified cancellation and recovery behavior. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| build_ref | reference |
| source_digest | digest |
| test_result_refs | list |
| documentation_revision | text |
| delivery_state | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md), [context-snapshot](../../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md), [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S04 File Specification Implementation](../../AGENT-SKILLS/S04-FILE-SPECIFICATION-IMPLEMENTATION/SKILL.md), [S05 Architectural Dependency Analysis](../../AGENT-SKILLS/S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md).
