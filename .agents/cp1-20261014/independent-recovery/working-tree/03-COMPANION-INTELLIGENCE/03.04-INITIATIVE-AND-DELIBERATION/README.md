# 03.04 - Initiative And Deliberation

## Purpose and boundary

This component belongs to [03-COMPANION-INTELLIGENCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R05 Companion Intelligence Engineer](../../AGENT-ROLES/R05-COMPANION-INTELLIGENCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Identify a useful initiative; state rationale and alternatives; assess authority; ask for decisions where required; create a governed task only after valid approval.

**Component invariant:** Initiative may propose action; it cannot self-approve authority-bearing consequences.

**Subsystem invariant:** Continuity, preference, confidence, and personality cannot confer execution authority. Human decisions remain attributable and task consent remains scoped.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-03.04.01 / initiative-proposal-engine](initiative-proposal-engine.file.README.md) | Generate bounded proposals from active goals, deadlines, and observed project state. Include expected outcome, required access, resource estimate, and a reversible first step. | A suggested maintenance task identifies exactly which files and tests it would affect. |
| [CETA-03.04.02 / collaborative-deliberation-engine](collaborative-deliberation-engine.file.README.md) | Represent options, assumptions, evidence, tradeoffs, and unresolved disagreements. Preserve human conclusions as explicit decisions rather than interpreting silence as agreement. | Conflicting evidence remains visible with source-specific reasoning and a decision request. |
| [CETA-03.04.03 / initiative-authority-filter](initiative-authority-filter.file.README.md) | Classify proposed effects and check whether current authority covers them. Route allowed work to task admission and undecided work to human deliberation without scope widening. | An already authorized read proceeds while a new publish effect requires a new decision. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| initiative_id | text |
| rationale_refs | list |
| proposed_effects | list |
| decision_state | enum |
| authority_ref | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[agent-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md), [inference-request](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md), [context-snapshot](../../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md), [memory-record](../../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md), [human-decision-request](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md), [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
