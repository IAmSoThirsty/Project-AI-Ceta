# Role 06 - Implementer Expected Output

Role class: EXECUTE
Source basis: *Thirsty's Agents 101*, Role 06, pages 157-161.

## Primary function

Convert approved requirements, designs, plans, and acceptance criteria into working code, configurations,
infrastructure, documentation, or operational changes.

## Core responsibility

Produce the authorized implementation while preserving scope, required behavior, security controls,
governance constraints, compatibility, and traceability.

## Non-negotiable output contract

1. Accepted implementation objective.
2. Scope.
3. Files or components changed.
4. Functional changes.
5. Security-relevant changes.
6. Governance-relevant changes.
7. Tests added or updated.
8. Validation performed.
9. Results.
10. Deviations.
11. Assumptions.
12. Known limitations.
13. Migration requirements.
14. Deployment requirements.
15. Rollback procedure.
16. Remaining work.
17. Evidence supporting completion.

## Completion conditions inherited from the source role contract

- Authorized requirements are implemented.
- Changes remain within scope.
- Applicable tests pass.
- Known failures are disclosed.
- Documentation is updated.
- Security and governance controls remain intact.
- Deployment and rollback implications are documented.
- Completion claims are supported by evidence.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Reference-fixture implementation is complete for the declared single-module scope; no command was executed by this document.

## Accepted implementation objective
Implement a validated Thomas-algorithm solver for a real tridiagonal linear system used by the implicit heat-equation step. Preserve deterministic behavior, reject malformed systems, and expose numerical failure clearly.

## Scope
Included: one Python module and unit-test specification. Excluded: sparse pivoting, cyclic systems, complex arithmetic, GPU support, and integration into a repository not supplied here.

## Files/components changed
- `src/thermalbench/linalg.py` - new solver.
- `tests/test_linalg.py` - required tests described below.

## Implementation
```python
from __future__ import annotations

from collections.abc import Sequence
import math


class TridiagonalError(ValueError):
    """Raised when a tridiagonal system is malformed or numerically singular."""


def solve_tridiagonal(
    lower: Sequence[float],
    diagonal: Sequence[float],
    upper: Sequence[float],
    rhs: Sequence[float],
    *,
    pivot_tolerance: float = 1.0e-14,
) -> list[float]:
    """Solve Ax=b for a real tridiagonal matrix using the Thomas algorithm.

    The matrix has ``lower`` and ``upper`` length n-1 and ``diagonal`` and
    ``rhs`` length n. The algorithm is O(n) time and O(n) memory. It does not
    pivot; callers must use a pivoting solver when diagonal dominance or an
    equivalent nonsingularity condition is not established.
    """
    n = len(diagonal)
    if n == 0:
        raise TridiagonalError("diagonal must contain at least one element")
    if len(rhs) != n or len(lower) != n - 1 or len(upper) != n - 1:
        raise TridiagonalError(
            "expected len(rhs)=len(diagonal)=n and "
            "len(lower)=len(upper)=n-1"
        )
    if not math.isfinite(pivot_tolerance) or pivot_tolerance <= 0.0:
        raise TridiagonalError("pivot_tolerance must be finite and positive")

    a = [float(v) for v in lower]
    b = [float(v) for v in diagonal]
    c = [float(v) for v in upper]
    d = [float(v) for v in rhs]
    if not all(math.isfinite(v) for v in (*a, *b, *c, *d)):
        raise TridiagonalError("system coefficients and rhs must be finite")

    coefficient_scale = max(abs(v) for v in (*a, *b, *c))
    if coefficient_scale == 0.0:
        raise TridiagonalError("matrix coefficients must not all be zero")
    threshold = pivot_tolerance * coefficient_scale

    for i in range(1, n):
        if abs(b[i - 1]) <= threshold:
            raise TridiagonalError(f"near-zero pivot at index {i - 1}")
        multiplier = a[i - 1] / b[i - 1]
        b[i] -= multiplier * c[i - 1]
        d[i] -= multiplier * d[i - 1]

    if abs(b[-1]) <= threshold:
        raise TridiagonalError(f"near-zero pivot at index {n - 1}")

    x = [0.0] * n
    x[-1] = d[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        if abs(b[i]) <= threshold:
            raise TridiagonalError(f"near-zero pivot at index {i}")
        x[i] = (d[i] - c[i] * x[i + 1]) / b[i]

    if not all(math.isfinite(v) for v in x):
        raise TridiagonalError("solution contains a non-finite value")
    return x
```

## Functional changes
The module solves a validated tridiagonal system in linear time. It does not silently continue through near-zero pivots and documents the no-pivot limitation.

## Security/governance effects
No file, network, subprocess, environment, or secret access. Inputs are copied before elimination, so caller-owned sequences are not mutated. No governance claim is made beyond the module boundary.

## Tests required
T1 known 3x3 system compared with an exact rational solution. T2 n=1. T3 dimension mismatch. T4 empty system. T5 NaN and infinity rejection. T6 zero/near-zero pivot. T7 input immutability. T8 randomized diagonally dominant matrices compared with a trusted dense solver using a stated tolerance. T9 residual check \(\|Ax-b\|_\infty/(\|A\|_\infty\|x\|_\infty+\|b\|_\infty)\).

## Validation performed
Not executed by this reference fixture. Required live commands: `python -m pytest tests/test_linalg.py -q` and the repository's lint/type-check commands.

## Deviations and limitations
No partial pivoting. The tolerance is scale-relative but not a complete condition-number estimate. Ill-conditioned systems may return a finite but inaccurate solution; callers must evaluate residual and conditioning requirements.

## Deployment/migration
None for a new isolated module. Integration must preserve the existing solver interface and error model.

## Rollback
Remove the new module and tests, or revert the exact commit. No data migration is involved.

## Remaining work
Execute tests in the target repository, integrate through an approved interface, run regression and manufactured-solution tests, and obtain independent verification.

## Evidence supporting completion
Created code only. Test and integration claims remain not verified.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Implementer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Tester: exact diff/artifact, requirements implemented, tests added, commands, known limitations, rollback, and claims requiring independent verification.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Partial scaffold called complete
- tests claimed but not run
- requirements changed silently
- security/control bypass for convenience
- rollback omitted

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
