# Role 10 - Documentation Writer Expected Output

Role class: EXECUTE
Source basis: *Thirsty's Agents 101*, Role 10, pages 179-185.

## Primary function

Create accurate, structured, maintainable, audience-appropriate documentation that explains a system,
process, decision, requirement, interface, or operational procedure without inventing behavior or
obscuring uncertainty.

## Core responsibility

Translate verified technical and operational information into documentation that enables understanding,
implementation, use, maintenance, review, and recovery.

## Non-negotiable output contract

1. Documentation objective.
2. Audience.
3. Scope.
4. Source materials used.
5. Document status.
6. Structured documentation.
7. Definitions.
8. Procedures or references.
9. Examples.
10. Failure and recovery information.
11. Security and governance notes.
12. Limitations.
13. Assumptions.
14. Unresolved gaps.
15. Verification references.
16. Revision information.

## Completion conditions inherited from the source role contract

- The audience and purpose are explicit.
- Material claims are traceable to established information.
- Implemented and planned behavior are separated.
- Procedures include prerequisites and failure handling.
- Terminology is consistent.
- Examples are valid.
- Limitations and gaps are visible.
- Version and ownership information are present where required.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Documentation exemplar is complete; live technical statements still require verified source material.

# ThermalBench tridiagonal solver

## Purpose
`solve_tridiagonal` solves a real tridiagonal linear system \(Ax=b\) using the Thomas algorithm. It is intended for implicit one-dimensional finite-difference steps where the matrix structure and no-pivot preconditions are established.

## Audience
Python developers integrating the numerical kernel, testers designing residual and failure tests, and reviewers assessing numerical limitations.

## Preconditions
For system dimension \(n\ge1\): `diagonal` and `rhs` contain `n` finite real values; `lower` and `upper` contain `n-1`; the elimination pivots remain larger than the configured scale-relative tolerance. The function does not perform pivoting and is not a general replacement for a robust sparse solver.

## Interface
```python
solve_tridiagonal(lower, diagonal, upper, rhs, *, pivot_tolerance=1e-14) -> list[float]
```
Inputs are copied and are not mutated. The returned list has length `n`.

## Method
Forward elimination removes the subdiagonal in \(O(n)\) operations. Back substitution recovers the solution in \(O(n)\). Memory use is \(O(n)\). The method can be numerically unsafe when a pivot is zero or small relative to the matrix scale; the implementation rejects detected near-zero pivots rather than silently dividing.

## Example
```python
x = solve_tridiagonal(
    lower=[-1.0, -1.0],
    diagonal=[2.0, 2.0, 2.0],
    upper=[-1.0, -1.0],
    rhs=[1.0, 0.0, 1.0],
)
```
Expected mathematical solution: `[1.0, 1.0, 1.0]`. In live documentation, this expected value must be covered by an executable test.

## Failure behavior
Raises `TridiagonalError` for empty or inconsistent dimensions, non-finite values, invalid tolerance, and detected near-zero pivots. A finite return value is not proof of high accuracy for an ill-conditioned matrix. Callers with a numerical-accuracy requirement should evaluate a normalized residual and, where necessary, a condition estimate.

## Security and governance
The function performs no file, network, environment, subprocess, identity, or policy operation. It must be called only after upstream validation and authorization. Documentation must not imply that this numerical utility enforces governance.

## Verification
Required references: exact source file and commit, unit-test IDs, randomized comparison procedure, residual formula, supported environment, and the latest test result. Distinguish "command to verify" from "verified in this release."

## Recovery and rollback
The function is stateless. Recovery consists of handling the controlled exception and preserving the failed run's diagnostics. Rollback is source-version reversion; there is no data migration.

## Limitations
Real arithmetic only; no partial pivoting; no cyclic tridiagonal matrices; accuracy depends on matrix conditioning and floating-point environment.

## Revision record
Record the version, date, author or agent role, reviewed sources, changed behavior, and verifier reference for each material revision.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Documentation Writer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to technical owner and Verifier: document version, authoritative sources, implemented-versus-planned distinctions, executable procedures, limitations, and verification references.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Planned behavior written as implemented
- commands or paths not checked
- audience undefined
- failure/recovery omitted
- documentation claims beyond source evidence

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
