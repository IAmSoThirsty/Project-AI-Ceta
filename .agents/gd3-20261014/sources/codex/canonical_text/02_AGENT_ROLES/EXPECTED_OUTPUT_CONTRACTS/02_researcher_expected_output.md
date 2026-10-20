# Role 02 - Researcher Expected Output

Role class: DEFINE
Source basis: *Thirsty's Agents 101*, Role 02, pages 138-141.

## Primary function

Gather, evaluate, organize, and present evidence relevant to a defined question without overstating
certainty or allowing unsupported interpretation to replace sourced information.

## Core responsibility

Produce a traceable evidence base that distinguishes established facts, source claims, expert interpretation,
conflicting evidence, uncertainty, and unresolved questions.

## Non-negotiable output contract

1. Research question.
2. Scope.
3. Method.
4. Inclusion and exclusion criteria.
5. Source hierarchy.
6. Key findings.
7. Supporting evidence.
8. Conflicting evidence.
9. Source-quality assessment.
10. Definitions and terminology.
11. Uncertainties.
12. Evidence gaps.
13. Findings that are time-sensitive.
14. Findings that depend on jurisdiction or context.
15. Current conclusion.
16. Confidence level.
17. What evidence would change the conclusion.
18. Full citations or traceable source references.

## Completion conditions inherited from the source role contract

- Material claims are traceable to evidence.
- Source quality has been evaluated.
- Facts and interpretation are separated.
- Conflicting evidence is disclosed.
- Uncertainty and research gaps are visible.
- Time-sensitive information is dated.
- The conclusion does not exceed the evidence.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | Research synthesis is supported within the declared source limits; no implementation was verified.

## Research question
For an offline finite-difference solver of the diffusion equation, what evidence is required to choose between backward Euler and Crank-Nicolson when accuracy, stability, monotonicity, and reproducibility all matter?

## Scope and method
Scope: linear parabolic problems on uniform grids with constant coefficients. Excluded: nonlinear diffusion, adaptive meshes, finite elements, and GPU-specific arithmetic. Method: prioritize primary method descriptions, authoritative numerical-analysis texts, and reproducible benchmark studies. Separate mathematical properties from implementation observations.

## Source hierarchy
Tier 1: original method papers and formal numerical-analysis references. Tier 2: peer-reviewed comparative studies with disclosed equations, grids, tolerances, and code. Tier 3: vendor or project documentation used only for implementation details. Unreviewed tutorials are excluded from material claims.

## Key findings
**Established mathematical finding:** backward Euler is first-order accurate in time and A-stable for the linear test equation. Crank-Nicolson is second-order accurate in time and A-stable, but it is not L-stable; stiff high-frequency modes may decay with oscillatory sign behavior rather than strong numerical damping.

**Interpretation:** unconditional linear stability does not mean every time step produces physically plausible or non-oscillatory results. Method selection therefore cannot be based on the phrase "unconditionally stable" alone.

**Engineering implication:** use convergence error, energy or maximum-principle behavior, stiffness, initial discontinuity, and required damping as explicit criteria. A common defensible design is Crank-Nicolson for smooth regimes with a controlled damping strategy or initial backward-Euler steps when discontinuities create high-frequency transients.

## Supporting evidence required for the project
E1. Manufactured-solution convergence showing approximately first-order temporal convergence for backward Euler and second-order for Crank-Nicolson while spatial error is controlled. E2. A stiff transient benchmark that records overshoot, undershoot, and total variation. E3. Energy-balance residuals. E4. Sensitivity to \(\Delta t/\Delta x^2\). E5. Reproducibility across the supported environment.

## Conflicting or conditional evidence
Some practical reports call Crank-Nicolson "more accurate" without controlling spatial error or initial regularity. That claim is conditional. Second-order truncation error does not guarantee smaller total error for every grid, step size, discontinuous initial condition, or floating-point implementation.

## Definitions
A-stability: the numerical stability region contains the entire left half-plane for the scalar test equation. L-stability: A-stability plus strong damping as the stiffness parameter tends to negative infinity. Convergence order: asymptotic rate at which error decreases under refinement, only interpretable when the test is in the asymptotic regime.

## Uncertainty and evidence gaps
The project-specific stiffness range, boundary-condition family, and required monotonicity are unknown. No implementation artifacts or benchmark outputs were examined. Therefore no solver selection is verified for the target system.

## Current conclusion
Crank-Nicolson is the leading candidate when smooth-solution temporal accuracy is prioritized; backward Euler is the safer baseline when robust damping is prioritized. The release decision should be conditional on the project-specific convergence and stiff-transient evidence listed above.

## Confidence
High for the qualitative mathematical properties; moderate for the engineering recommendation because the target workload is not yet characterized.

## Evidence that would change the conclusion
A workload study showing persistent discontinuities, positivity violations, or unacceptable oscillation under Crank-Nicolson would favor backward Euler or a damped hybrid. A verified accuracy requirement that backward Euler cannot meet within the resource budget would favor Crank-Nicolson.

## Traceable reference format
For live use, include complete author, title, venue, year, edition or DOI, exact theorem/section/page, access date for mutable sources, and a note describing which claim each source supports.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Researcher output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Analyst: source table, claim-to-source mapping, conflicting evidence, source-quality assessment, dated uncertainties, and research gaps. Do not flatten source disagreement.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Unsourced material claims
- source count treated as source quality
- conflicting evidence omitted
- time-sensitive claim left undated
- confidence stronger than evidence

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
