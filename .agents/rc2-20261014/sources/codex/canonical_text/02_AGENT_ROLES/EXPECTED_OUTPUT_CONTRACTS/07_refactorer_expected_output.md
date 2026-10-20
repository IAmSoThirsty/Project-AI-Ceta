# Role 07 - Refactorer Expected Output

Role class: EXECUTE
Source basis: *Thirsty's Agents 101*, Role 07, pages 162-166.

## Primary function

Improve the internal structure, clarity, maintainability, modularity, testability, or efficiency of an
implementation while preserving its externally observable behavior unless behavior changes are explicitly
authorized.

## Core responsibility

Reduce structural weakness and technical debt without introducing unintended functional change.

## Non-negotiable output contract

1. Refactoring objective.
2. Scope.
3. Preserved behavior.
4. Structural problems identified.
5. Changes made.
6. Interfaces affected.
7. Tests added or strengthened.
8. Regression evidence.
9. Performance comparison, where relevant.
10. Security and governance impact.
11. Compatibility impact.
12. Remaining technical debt.
13. Known risks.
14. Any behavior changes requiring separate authorization.

## Completion conditions inherited from the source role contract

- Required behavior remains intact.
- Tests support the equivalence claim.
- Structural improvement is explicit.
- No unauthorized features were introduced.
- Compatibility effects are documented.
- Security and governance semantics remain preserved.
- Any unresolved divergence is disclosed.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Not verified | Refactoring plan and exemplar diff are defined; behavior equivalence has not been verified.

## Refactoring objective
Separate numerical assembly from time stepping in the implicit heat solver while preserving all externally observable behavior, public signatures, result ordering, error types, and evidence fields.

## Scope
`solver.py`, new private `assembly.py`, and affected tests. No algorithm, tolerance, schema, or public API change is authorized.

## Preserved behavior
For every accepted input in the existing contract: identical array shapes and ordering; numerically equivalent values within the established tolerance; identical exception classes for invalid input; identical evidence-receipt fields; no new I/O.

## Structural problems
The current step function validates inputs, assembles coefficients, solves the system, updates boundaries, and formats diagnostics. This prevents isolated testing, obscures invariants, and duplicates coefficient logic across two schemes.

## Changes made
1. Extract pure `_assemble_backward_euler(...)` and `_assemble_crank_nicolson(...)` functions returning immutable coefficient records. 2. Retain the public `solve(...)` signature. 3. Centralize boundary-condition application. 4. Replace duplicated index arithmetic with one validated grid descriptor. 5. Preserve existing exception translation at the public boundary.

## Interfaces affected
Only private module interfaces are new. Public imports and serialized output are unchanged. The new coefficient record contains `lower`, `diagonal`, `upper`, and `rhs` with explicit shape invariants.

## Tests strengthened
- Golden-master outputs for approved fixtures.
- Property test: assembly arrays have lengths `n-1`, `n`, `n-1`, `n`.
- Metamorphic test: zero source and uniform initial/boundary temperature remain uniform.
- Regression test for previous boundary-index defect.
- Exception compatibility test.
- Evidence-receipt snapshot excluding intentionally variable timestamps.

## Equivalence evidence required
Run old and new implementations against the same corpus. Report maximum absolute difference, normalized residual difference, exception equivalence, and serialized receipt diff. A passing unit suite alone is insufficient if it does not cover the preserved behavior contract.

## Performance comparison
No performance improvement is claimed. Measure only to detect a material regression; acceptance threshold: median runtime no worse than 5% under the controlled benchmark, with uncertainty reported.

## Security/governance impact
The extraction introduces no authority or I/O path. Review must confirm the new private module cannot bypass validation or evidence generation.

## Remaining technical debt
The dense diagnostic object remains coupled to the public result schema. Changing it would require separate authorization.

## Known risks
Snapshot tests may conceal correlated defects if the baseline is already wrong. Mitigation: manufactured-solution and invariant tests remain independent of the old implementation.

## Behavior changes requiring authorization
None proposed. Any change in tolerance, algorithm, error type, or output field must be separated from this refactor.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Refactorer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Tester and Verifier: preserved-behavior contract, baseline identity, refactored artifact, equivalence tests, regression evidence, remaining debt, and any unauthorized behavior difference.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Behavior change hidden inside refactor
- equivalence inferred from compilation
- baseline absent
- public API changed without authority
- performance claim without measurement

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
