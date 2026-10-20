# Role 12 - Planner Expected Output

Role class: DEFINE
Source basis: *Thirsty's Agents 101*, Role 12, pages 192-198.

## Primary function

Convert an approved objective into an ordered, dependency-aware, resource-conscious, verifiable plan of
work.

## Core responsibility

Define what must be done, in what order, by whom or by which role, under what conditions, with what
evidence, and with what completion criteria.

## Non-negotiable output contract

1. Approved objective.
2. Scope.
3. Current state.
4. Target state.
5. Assumptions.
6. Constraints.
7. Deliverables.
8. Work breakdown.
9. Dependencies.
10. Roles and ownership.
11. Phases.
12. Milestones.
13. Validation gates.
14. Risks.
15. Blockers.
16. Contingencies.
17. Resource requirements.
18. Schedule or sequence.
19. Completion evidence.
20. Open decisions requiring human resolution.

## Completion conditions inherited from the source role contract

- The objective maps to defined deliverables.
- Deliverables map to executable tasks.
- Dependencies are explicit.
- Ownership is assigned or identified as unresolved.
- Entry and exit criteria exist.
- Risks and blockers are visible.
- Validation and completion evidence are defined.
- Unresolved authority decisions remain with the human.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Executable plan is defined; no workstream is reported as completed.

## Approved objective
Deliver an offline-first thermal-simulation release candidate with reproducible numerical evidence, bounded authority, failure recovery, and owner-operable start-to-proof-to-stop workflow.

## Scope
Included: requirements, architecture, implementation, tests, verification, security review, owner workflow, release package, rollback, and continuity. Excluded: hosted deployment and multidimensional physics.

## Current state
Role contracts and target equation are defined. Repository state, existing implementation, dependency policy, and owner acceptance environment are unknown and must be inspected before changes.

## Target state
A versioned local artifact that installs from a clean machine, executes one governed simulation offline, displays truthful status, preserves evidence, reproduces the result, recovers from ordinary failure, and uninstalls or rolls back cleanly.

## Deliverables
D1 requirements traceability matrix. D2 architecture and threat model. D3 numerical kernel and validated schemas. D4 evidence/replay subsystem. D5 test package. D6 independent verification report. D7 owner cockpit workflow. D8 release archive, checksum, signature if authorized, rollback and continuity records.

## Work breakdown and ownership
W1 Observer: capture repo/environment baseline. W2 Architect: produce architecture and interfaces. W3 Researcher/Analyst: define numerical-method evidence and acceptance thresholds. W4 Implementer: implement approved slices. W5 Tester: normal/boundary/failure/recovery suite. W6 Security Auditor and Governance Reviewer: inspect authority and evidence paths. W7 Verifier: independently reproduce claims. W8 UX Reviewer: owner journey. W9 Documentation Writer: setup/run/test/recovery/rollback. W10 Coordinator: preserve dependencies, conflicts, and provenance.

## Dependencies
W1 is a hard dependency for repository work. Architecture and acceptance criteria precede implementation. Evidence schema precedes release claims. Independent verification follows a frozen candidate. Owner acceptance follows a complete end-to-end path.

## Phases and gates
P0 Baseline gate: correct repo, branch, continuity, tools, and constraints established. P1 Design gate: requirements map, architecture, threat model, and open decisions approved. P2 Vertical slice: one real simulation from input to evidence. P3 Numerical gate: convergence and physical-invariant evidence. P4 Control gate: denial, tamper, replay, recovery, and rollback evidence. P5 Owner gate: start, understand, act, verify, recover, stop. P6 Release gate: exact artifact independently verified and continuity current.

## Risks and contingencies
R1 acceptance thresholds undefined -> escalate before optimizing. R2 existing architecture conflicts -> present minimal alternatives; do not replace silently. R3 solver oscillation -> retain backward-Euler fallback. R4 environment unavailable -> complete safe repository-controlled work and mark runtime verification blocked. R5 evidence path fails -> result remains unverified; no promotion.

## Resource requirements
Local Python environment, dependency lock, representative datasets, isolated verification environment, source control, artifact hashing, and owner acceptance time.

## Sequence
Execute P0 through P6. Parallelize research, UX journey mapping, and threat modeling after baseline, provided they do not assume uninspected implementation facts.

## Completion evidence
Every deliverable maps to artifact IDs and acceptance evidence. Final report enumerates created, modified, tested, verified, failed, blocked, not executed, risks, rollback, and next safe action.

## Open human decisions
Approve numerical tolerances, evidence retention, signing authority, supported environments, and release acceptance standard.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Planner output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Coordinator: work breakdown, dependencies, roles, gates, blockers, contingencies, required resources, completion evidence, and owner decisions.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Task list without dependencies
- no ownership
- no evidence gates
- blocked work sequenced as executable
- owner decisions silently assumed

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
