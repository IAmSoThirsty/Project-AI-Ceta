# 12.05 - Engineering Review

## Purpose and boundary

This component belongs to [12-ENGINEERING-INTELLIGENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R11 Engineering Workspace Engineer](../../AGENT-ROLES/R11-ENGINEERING-WORKSPACE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Inspect exact changes; compare against contracts and requirements; reproduce critical tests independently; classify findings; approve or return changes with evidence.

**Component invariant:** Independent review must inspect the actual proposed revision and cannot approve by trusting the builder summary.

**Subsystem invariant:** Engineering work operates on inspected local source with scoped file ownership. Generated code, test execution, and verified product behavior are distinct completion stages.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-12.05.01 / code-review-engine](code-review-engine.file.README.md) | Review exact diffs for logic, error handling, data integrity, resource cleanup, security boundaries, and maintainability. Link each finding to a precise file, behavior, and reproduction. | A reported defect has a source location and a concrete failing scenario. |
| [CETA-12.05.02 / regression-risk-evaluator](regression-risk-evaluator.file.README.md) | Identify impacted call paths, data contracts, migrations, permissions, and user flows using dependency and change analysis. Require tests for previously working behavior at risk. | A change to task cancellation triggers worker, recovery, and UI regression checks. |
| [CETA-12.05.03 / engineering-contract-validator](engineering-contract-validator.file.README.md) | Compare implemented APIs, schemas, state transitions, and error behavior against approved canonical contracts. Reject undocumented widening or silently incompatible responses. | Producers and consumers pass the same contract fixtures on the delivered revision. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| review_id | text |
| change_digest | digest |
| reviewer_id | text |
| findings | list |
| acceptance_impact | list |


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
