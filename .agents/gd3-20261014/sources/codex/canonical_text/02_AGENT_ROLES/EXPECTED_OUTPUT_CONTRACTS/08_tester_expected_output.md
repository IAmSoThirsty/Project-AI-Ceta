# Role 08 - Tester Expected Output

Role class: CHALLENGE
Source basis: *Thirsty's Agents 101*, Role 08, pages 167-172.

## Primary function

Design, execute, and report verification activities that determine whether a system, component, change, or
requirement behaves as specified across normal, boundary, failure, adversarial, and recovery conditions.

## Core responsibility

Produce objective evidence of observed behavior and identify where the implementation satisfies, violates,
or fails to prove its requirements.

## Non-negotiable output contract

1. Test objective.
2. Scope.
3. Requirements mapped.
4. Environments.
5. Test strategy.
6. Coverage model.
7. Test cases.
8. Results.
9. Evidence.
10. Defects.
11. Blocked tests.
12. Skipped tests.
13. Regression results.
14. Security and governance results.
15. Coverage gaps.
16. Residual risks.
17. Overall test conclusion with stated limits.

## Completion conditions inherited from the source role contract

- Requirements are mapped to tests or identified as untestable.
- Expected outcomes were defined.
- Results are supported by evidence.
- Failures and blocked tests are disclosed.
- Regression impact is addressed.
- Coverage gaps are visible.
- The conclusion does not exceed the tested conditions.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Test design is complete; fixture results are synthetic and are not evidence of live execution.

## Test objective
Determine whether the implicit thermal solver satisfies numerical accuracy, validation, physical-invariant, failure-recovery, governance, and replay requirements.

## Scope and environment
Target: release candidate artifact `<commit/hash>`, Python `<version>`, dependency lock `<hash>`, operating system `<identity>`. Scope includes local execution and evidence receipts. Cloud and multidimensional behavior are excluded.

## Requirements mapped
R1 equation solution -> manufactured-solution convergence. R2 parameter validation -> invalid-domain matrix. R3 scheme support -> method-specific regression tests. R4 deterministic replay -> repeated isolated runs. R5 evidence binding -> artifact/result hash tests. R6 fail-closed -> missing-authority and corrupt-evidence tests.

## Strategy and coverage model
- Example-based unit tests for algebra and validation.
- Property-based tests for dimensional and finiteness invariants.
- Manufactured solutions for numerical error.
- Boundary and failure-path tests.
- Metamorphic tests for uniform equilibrium and linearity where assumptions permit.
- Governance negative tests.
- Recovery tests after interruption and corrupt output.

## Test cases
T-001 exact steady linear profile under fixed boundary temperatures.
T-002 manufactured transient solution; calculate \(L_2\) and \(L_\infty\) error.
T-003 grid refinement at \(h,h/2,h/4\); estimate observed spatial order.
T-004 time refinement while spatial error is negligible; estimate temporal order.
T-005 zero, negative, NaN, infinity, and unit mismatch inputs.
T-006 discontinuous initial condition; record overshoot/undershoot.
T-007 interrupted run; verify incomplete state and clean replay.
T-008 altered result byte; verify hash failure and denial of verification.
T-009 expired authorization; verify no solver invocation and a denial receipt.
T-010 identical replay under pinned environment.

## Expected outcomes
For T-004, Crank-Nicolson observed order should approach 2 only in the asymptotic regime; the test must not hard-code an exact value of 2. Acceptance uses a declared interval, for example `1.8 <= p <= 2.2`, justified by grid and rounding effects. Physical-bound acceptance is separate from stability.

## REFERENCE FIXTURE results
Passed: T-001, T-002, T-003, T-005, T-007, T-008, T-009, T-010. Failed: T-006 due to `3.8e-4 K` undershoot against `1e-8 K` limit. Inconclusive: T-004; finest two errors are near the floating-point floor. Blocked: none. Skipped: none.

## Evidence
Each result must attach command, timestamp, artifact hash, environment lock, input hash, raw output, and calculated metrics. Store the convergence table, not only the fitted order.

## Defects
DEF-006: physical-bound violation for discontinuous initial condition. Severity high if non-negativity is a release requirement; confidence high for the fixture case, unknown across the broader workload.

## Regression/security/governance results
No unauthorized run occurred in the denial fixtures. Corrupt evidence did not promote. These results prove only the tested paths and environment.

## Coverage gaps
Variable coefficients, mixed boundaries, extreme grid sizes, low-memory behavior, cross-platform floating-point differences, and long-duration soak behavior.

## Overall conclusion
Not ready for acceptance under the current physical-bound criterion. Numerical convergence is partially supported, but the temporal-order claim is inconclusive and the discontinuity case fails.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Tester output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Verifier: exact artifact/environment, requirement-test matrix, raw results, failures, blocked/skipped tests, coverage gaps, and bounded test conclusion.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- "Not failed" reported as passed
- happy-path-only testing
- expected results changed after observation
- blocked/skipped tests hidden
- production claim from test environment

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
