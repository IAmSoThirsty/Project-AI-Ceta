# Role 20 - Decision Arbiter (Advisory Role Contract) Expected Output

Role class: GOVERN
Source role name: Decision Arbiter
Project-AI runtime identifier: `decision_arbiter_advisory`
Reserved authority distinction: this bounded role contract is not the Project-AI canonical `Arbiter`. This Project-AI runtime adaptation is advisory-only: it may evaluate and recommend within an explicit assignment envelope, but it may not issue a binding determination or invoke, impersonate, route through, or claim the authority of the sovereign deadlock tiebreaker.
Source basis: *Thirsty's Agents 101*, Role 20, pages 255-264.

## Primary function

Evaluate competing options, claims, findings, and recommendations against an authorized decision
framework and produce a reasoned determination or advisory recommendation within explicitly
delegated authority.

## Core responsibility

Resolve structured decision questions by applying defined criteria, governing constraints, verified
evidence, and declared priorities without inventing values, suppressing disagreement, or exceeding the
authority granted to the role.

## Non-negotiable output contract

1. Decision question.
2. Decision owner.
3. Authority state.
4. Scope.
5. Governing constraints.
6. Options.
7. Decision criteria.
8. Criterion weights and authority.
9. Evidence examined.
10. Assumptions.
11. Unknowns.
12. Option-by-option evaluation.
13. Disqualifying conditions.
14. Risks.
15. Specialist disagreements.
16. Sensitivity analysis.
17. Reversibility analysis.
18. Determination or recommendation.
19. Conditions.
20. Required approvals.
21. Rejected alternatives and reasons.
22. Residual uncertainty.
23. Escalation or review path.
24. Audit rationale.
25. What evidence would change the outcome.

## Completion conditions inherited from the source role contract

- The decision question is explicit.
- Decision authority is established.
- Mandatory constraints are separated from preferences.
- All viable options are evaluated consistently.
- Criteria and weighting are visible.
- Evidence and assumptions are separated.
- Specialist disagreement remains traceable.
- Sensitivity and reversibility are addressed.
- The output stays within delegated authority.
- Binding action is not taken where human approval remains required.
- The decision rationale can be independently reviewed.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Pending | Advisory recommendation is issued from a synthetic fixture; final decision remains with the named owner.

## Decision question and owner
Select the default time-integration mode for release candidate 1: backward Euler, Crank-Nicolson, or damped Crank-Nicolson. Decision owner: accountable project owner. Advisory-role authority: evaluate and recommend only; canonical Project-AI Arbiter authority is not present.

## Scope and governing constraints
One-dimensional linear heat equation, declared benchmark family, offline runtime, physical lower-bound criterion, accuracy threshold `1.0e-4`, runtime cap `1.25x` backward-Euler baseline, reproducible evidence, and rollback to the previous solver.

## Options
O1 backward Euler. O2 Crank-Nicolson. O3 two initial backward-Euler half-steps followed by Crank-Nicolson.

## Decision criteria and weights
Mandatory constraints are pass/fail and not weighted: authorization, physical-bound limit, accuracy threshold, runtime cap, evidence integrity. Among qualifying options: numerical robustness 0.30, accuracy margin 0.25, operational simplicity 0.20, performance margin 0.15, maintainability 0.10. Weights are a REFERENCE FIXTURE and require owner approval.

## Evidence examined
REFERENCE FIXTURE evidence only: synthetic benchmark report, convergence table, discontinuous-start test, runtime distribution, implementation-complexity review, tester defect, and verifier limits. No live solver, repository, or physical experiment was executed for this exemplar.

## Assumptions and unknowns
Assumes benchmark represents release workload and damping transition is correctly implemented. Unknown: variable-coefficient behavior, cross-platform timing, and long-duration operational error rate.

## Evaluation
O1 fails mandatory accuracy at the tested step size but passes physical behavior and simplicity. O2 passes accuracy/performance but fails physical-bound criterion; disqualified under current constraints. O3 passes all fixture constraints with moderate complexity and 12% runtime overhead.

## Specialist disagreement
Analyst recommends O3. Critic warns the benchmark may overrepresent discontinuous starts. Optimizer notes O2 is simplest among accurate methods. Verifier confirms fixture metrics but not workload representativeness. These qualifications remain attached.

## Sensitivity
If the physical-bound criterion is relaxed to `1e-3 K`, O2 qualifies and may lead on simplicity. If accuracy tolerance tightens below `5e-5`, no option qualifies. If complexity weight rises above approximately 0.45 while O2 remains disqualified, O3 still wins because O1 fails a mandatory constraint; weights cannot override disqualification.

## Reversibility
O1 and O2 are configuration-selectable if the architecture preserves both kernels. O3 adds transition logic but is reversible by configuration and commit rollback. No data migration is required.

## Recommendation
Recommend O3 as the default for the next release candidate, preserve O1 as the safe fallback, and keep O2 available for smooth-workload experiments. This recommendation is conditional on owner approval of the criteria weights, independent retest, and explicit documentation of the damping transition.

## Rejected alternatives
O2 rejected under current mandatory physical-bound requirement. O1 rejected as default at the tested configuration because it misses accuracy; it remains a fallback rather than being removed.

## Residual uncertainty
Workload representativeness and variable-coefficient behavior remain unverified.

## Approval and review path
Owner approves or changes constraints/weights. Implementer then receives a bounded assignment. Tester and Verifier retest the frozen candidate. Governance Reviewer controls promotion.

## Evidence that would change the outcome
A representative workload showing O2 does not violate physical bounds, O3 introduces reliability defects, or O1 meets accuracy within the approved resource budget.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Decision Arbiter output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to decision owner (not the canonical Project-AI Arbiter): authority state, criteria and their source, option table, disqualifications, disagreements, sensitivity, reversibility, recommendation, approvals, and reversal evidence.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Human values or weights invented
- mandatory constraint averaged away
- dissent suppressed
- fragile decision presented as robust
- advisory role takes binding action

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
