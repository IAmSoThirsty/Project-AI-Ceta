# Role 09 - Verifier Expected Output

Role class: CHALLENGE
Source basis: *Thirsty's Agents 101*, Role 09, pages 173-178.

## Primary function

Determine whether claims, outputs, implementations, decisions, evidence, and reported results are
accurate, complete, reproducible, internally consistent, and supported by the required standard of proof.

## Core responsibility

Independently compare what is claimed against what can be demonstrated through direct evidence,
reproducible procedures, authoritative requirements, and observed behavior.

## Non-negotiable output contract

1. Claim under verification.
2. Scope.
3. Required proof standard.
4. Claim decomposition.
5. Acceptance criteria.
6. Evidence examined.
7. Evidence-integrity assessment.
8. Procedures performed.
9. Reproduction results.
10. Contradictory evidence.
11. Verification state for each claim.
12. Limits.
13. Assumptions.
14. Unresolved questions.
15. Additional evidence required.
16. Final verification conclusion.
17. What evidence would change the conclusion.

## Completion conditions inherited from the source role contract

- The exact claim has been bounded.
- Material subclaims have been identified.
- Evidence has been mapped to each subclaim.
- Artifact, version, environment, and timeframe are established.
- Verification procedures are reproducible where practical.
- Contradictory evidence is disclosed.
- Verification conclusions remain within the proven scope.
- Remaining uncertainty is explicit.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | Verification conclusion applies only to the declared synthetic fixture.

## Claim under verification
"Release candidate RC-7 reproduces the manufactured-solution benchmark with normalized \(L_2\) error <= `1.0e-4`, rejects unauthorized execution, and emits an evidence receipt bound to the result artifact."

## Scope and proof standard
Scope: exact RC-7 artifact, pinned local environment, benchmark dataset MS-03, and the three stated subclaims. Proof standard: independent reproduction plus integrity-bound evidence. No claim about production readiness, all workloads, or security beyond the tested denial path.

## Claim decomposition
C1 numerical error meets threshold. C2 unauthorized request is denied before solver execution. C3 receipt binds actor, policy, request, code, environment, and result hashes.

## Acceptance criteria
C1 calculated normalized \(L_2\) error <= `1.0e-4` using the specified quadrature and reference solution. C2 no result directory or solver-start event exists after denial. C3 recomputed hashes match receipt fields and any byte change invalidates verification.

## Evidence examined
REFERENCE FIXTURE: release archive hash, signed manifest, dependency lock, benchmark input, reference-generation procedure, raw result array, denial log, receipt JSON, and commands used by the claimant.

## Evidence-integrity assessment
Artifact and manifest hashes are internally consistent. The benchmark source is versioned. Independence is limited because the reference-generation code and solver share one utility for grid construction; that shared dependency was separately inspected but not independently reimplemented.

## Procedures performed
1. Rebuilt isolated environment from lock. 2. Recomputed artifact hashes. 3. Executed benchmark from clean state. 4. Recomputed reference values and error metric. 5. Submitted expired authorization. 6. Inspected process and filesystem evidence. 7. Mutated one result byte and re-ran receipt validation.

## Reproduction results
C1: error `7.04e-5`; verified within the fixture. C2: denial emitted, no solver-start event, no result artifact; verified for the expired-token path. C3: all hashes matched before mutation and verification failed after mutation; verified.

## Contradictory evidence
The claimant's summary described the reference as "independent." The shared grid utility means full independence is not established. The numerical result remains supported, but the independence wording must be narrowed.

## Verification states
C1 Verified within stated limits. C2 Verified within stated limits. C3 Verified. "Independent reference implementation" Not verified. "Production-ready" Out of scope.

## Limits and assumptions
Assumes the operating system and Python distribution identified by the environment hash were not compromised. Only one denial condition and one benchmark were reproduced. Cross-platform reproducibility was not tested.

## Final conclusion
The exact bounded claim is verified within the stated synthetic-fixture limits after replacing "independent reference" with "separately executed reference procedure sharing the disclosed grid utility."

## Evidence that would change the conclusion
Hash mismatch, failure to reproduce the error threshold, evidence of solver execution after denial, an undisclosed shared implementation path, or a result mutation that still validates.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Verifier output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Governance Reviewer or release authority: claim-by-claim states, evidence integrity, reproduction procedure, contradictions, limits, and evidence that would reverse the conclusion.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Assertion treated as proof
- artifact/version mismatch ignored
- partial evidence promoted to full verification
- contradictory evidence concealed
- claim boundary expanded

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
