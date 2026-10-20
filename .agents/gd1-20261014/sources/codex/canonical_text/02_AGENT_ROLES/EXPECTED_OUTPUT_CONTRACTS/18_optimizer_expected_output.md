# Role 18 - Optimizer Expected Output

Role class: EXECUTE
Source basis: *Thirsty's Agents 101*, Role 18, pages 237-245.

## Primary function

Improve measurable system characteristics such as latency, throughput, resource consumption, reliability,
cost, scalability, responsiveness, or operational efficiency while preserving required behavior, security,
governance, correctness, and quality.

## Core responsibility

Identify and implement or recommend evidence-supported improvements against an explicit baseline and
defined optimization objective.

## Non-negotiable output contract

1. Optimization objective.
2. Target metrics.
3. Protected properties.
4. Baseline method.
5. Baseline results.
6. Workload.
7. Environment.
8. Bottleneck analysis.
9. Options considered.
10. Selected change or recommendation.
11. Tradeoffs.
12. Implementation details, when authorized.
13. Comparative measurements.
14. Statistical results.
15. Regression results.
16. Security and governance impact.
17. Reliability impact.
18. Cost impact.
19. Rollback procedure.
20. Residual limitations.
21. Acceptance determination.
22. What evidence would change the conclusion.

## Completion conditions inherited from the source role contract

- The optimization target is measurable.
- A reproducible baseline exists.
- The bottleneck is supported by evidence.
- Results were measured under comparable conditions.
- Required behavior remains intact.
- Security and governance properties remain intact.
- Regressions are disclosed.
- Tradeoffs are explicit.
- Rollback is available where required.
- Claimed improvement remains within the measured scope.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | Optimization recommendation is supported only by the declared synthetic controlled benchmark; no live change was authorized.

## Objective and target metrics
Reduce median runtime of the tridiagonal solve by at least 20% for `n=10,000` while preserving residual accuracy, exception behavior, determinism, memory ceiling, security, and evidence fields.

## Protected properties
Normalized residual <= existing threshold; identical validation and controlled errors; no mutation of caller inputs; no new dependency or authority path; peak memory <= 2x baseline; rollback available.

## Baseline method and environment
REFERENCE FIXTURE: pure-Python list implementation, Python 3.11, pinned CPU affinity, warm cache protocol, 30 measured iterations after five warm-ups. Dataset and seed fixed. Report median, interquartile range, and bootstrap 95% interval for median difference.

## Baseline results
Median 8.40 ms; IQR 0.31 ms; peak 1.2 MiB; maximum normalized residual `2.1e-15`.

## Bottleneck analysis
Profile attributes 71% of time to repeated Python-level element access and temporary list construction. Solver arithmetic is linear and not dominated by validation for large `n`.

## Options considered
O1 local-variable/list optimization with no dependency. O2 NumPy arrays and vectorization; rejected because forward elimination remains sequential and conversion cost dominates at this size. O3 compiled extension; likely faster but adds build, portability, and supply-chain costs outside current authority. O4 reuse preallocated work buffers; fastest potential but changes ownership/lifetime semantics.

## Selected recommendation
Implement O1: reduce tuple expansion, bind lists locally, avoid repeated concatenation during finiteness checks, and combine validation passes without changing the public contract. Keep O3 as a separately authorized future option.

## Comparative fixture measurements
Candidate median 6.31 ms; IQR 0.27 ms. Relative median improvement 24.9%. Bootstrap 95% interval for improvement: 22.8%-27.1%. Peak memory 1.0 MiB. Residual distribution indistinguishable at the reported precision; exact floating-point output remained identical in the fixture.

## Statistical cautions
Iterations from one process are not fully independent. The interval quantifies resampling variability of the recorded benchmark, not cross-machine performance. No normality assumption is required for the bootstrap, but workload representativeness remains an external assumption.

## Regression results required
Full unit/property suite; exception-message compatibility if public; small-`n` benchmark to detect overhead regression; multiple sizes; at least one second supported environment; evidence-receipt identity unchanged.

## Security/governance/reliability impact
No new I/O, dependency, privilege, or control path. Combined validation must preserve fail-closed ordering and exact non-finite rejection. Review the change to ensure performance work does not skip checks.

## Cost and rollback
Low implementation cost; revert one commit. No data migration.

## Residual limitations
The optimization does not address asymptotic complexity or very large systems where a compiled implementation may be required.

## Acceptance determination
Candidate meets the synthetic fixture target. Live acceptance remains pending repository tests, independent benchmark reproduction, and approval of the change scope.

## Evidence that would change the conclusion
A supported environment showing <20% improvement, any changed numerical/error behavior, increased memory beyond the limit, or evidence that the profile was not representative.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Optimizer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Implementer and Verifier: baseline, workload, environment, selected change, measurements with uncertainty, regressions, protected properties, rollback, and bounded acceptance claim.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- No reproducible baseline
- different workloads compared
- mean-only claim with no variability
- correctness checks removed for speed
- improvement generalized beyond measurements

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
