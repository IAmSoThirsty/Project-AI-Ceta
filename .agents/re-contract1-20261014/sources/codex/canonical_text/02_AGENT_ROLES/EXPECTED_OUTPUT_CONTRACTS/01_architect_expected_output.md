# Role 01 - Architect Expected Output

Role class: DEFINE
Source basis: *Thirsty's Agents 101*, Role 01, pages 134-137.

## Primary function

Design coherent systems, structures, workflows, and implementation models from defined requirements,
constraints, authorities, and objectives.

## Core responsibility

Transform an accepted problem definition into an explicit architecture that identifies components,
interfaces, dependencies, trust boundaries, data flows, control points, failure conditions, and
implementation sequencing.

## Non-negotiable output contract

1. Accepted objective.
2. Confirmed scope.
3. Requirements.
4. Constraints.
5. Assumptions.
6. Unknowns.
7. Proposed architecture.
8. Component definitions.
9. Interface definitions.
10. Data flows.
11. Authority flows.
12. Trust boundaries.
13. Failure modes.
14. Security considerations.
15. Governance considerations.
16. Alternative architectures.
17. Tradeoff analysis.
18. Implementation sequence.
19. Verification plan.
20. Open decisions requiring human resolution.

## Completion conditions inherited from the source role contract

- Every major requirement maps to an architectural element.
- Every component has a defined responsibility.
- Every critical interface has a contract.
- Trust and authority boundaries are explicit.
- Known assumptions and unknowns are visible.
- Failure and recovery behavior are addressed.
- The architecture includes a verification path.
- Unresolved decisions are presented without being decided on the user’s behalf.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Not verified | Proposed architecture; not implemented or verified.

## Accepted objective
Design an offline-first, reproducible Python system that solves the one-dimensional transient heat equation and returns numerical results together with an evidence receipt. The architecture must preserve deterministic replay, explicit authority boundaries, failure isolation, and independent verification.

## Confirmed scope
Included: local dataset ingestion, parameter validation, finite-difference solution, result packaging, evidence generation, replay, and verification hooks. Excluded: cloud deployment, graphical mesh generation, multidimensional physics, and production certification.

## Requirements
R1. Solve
\[
\frac{\partial T}{\partial t}=\alpha\frac{\partial^2T}{\partial x^2}+\frac{q(x,t)}{\rho c_p}
\]
for \(x\in[0,L]\), \(t\in[0,t_f]\), with declared initial and boundary conditions.
R2. Validate units and domains: \(L>0\), \(\alpha>0\), \(\rho>0\), \(c_p>0\), \(\Delta x>0\), \(\Delta t>0\).
R3. Support backward Euler and Crank-Nicolson schemes.
R4. Produce deterministic results for identical artifact, configuration, and floating-point environment.
R5. Bind every result to input hashes, solver version, dependency lock, configuration, and acceptance evidence.
R6. Fail closed when required provenance, authority, or validation is absent.

## Constraints
Python 3.11; local execution; no network dependency in the core path; 16 GB memory ceiling; no hidden telemetry; exact input files remain immutable.

## Assumptions
A1. Uniform spatial grid is acceptable for version 1. A2. Material properties are constant within one run. A3. IEEE-754 double precision is the reference arithmetic.

## Unknowns
U1. Maximum production grid size. U2. Required long-term evidence retention. U3. Whether mixed boundary conditions are mandatory in version 1.

## Proposed architecture
1. **Command/API boundary** - accepts an immutable `SimulationRequest` and returns an action identifier.
2. **Validation service** - performs schema, range, unit, and cross-field checks before state creation.
3. **Authority gate** - verifies actor, permitted operation, dataset scope, and policy version.
4. **Solver engine** - pure numerical kernel with no file or network access.
5. **Result store** - content-addressed local artifacts; append-only metadata.
6. **Evidence ledger** - records hashes, environment, command, tolerances, residuals, and test references.
7. **Replay service** - reconstructs a run from the original request and pinned environment.
8. **Independent verifier adapter** - compares replay and manufactured-solution evidence without modifying the target artifact.

## Component contracts
**SimulationRequest**
- Inputs: geometry, material parameters, source term, initial/boundary conditions, grid, time interval, scheme, tolerances.
- Output: canonical JSON bytes and SHA-256 identity.
- Failure: reject unknown units, non-finite values, inconsistent array lengths, or unauthorized paths.

**SolverEngine.solve(request)**
- Precondition: validated request and authorized action receipt.
- Postcondition: temperature array shape `(n_time, n_space)`, finite values, monotonic time vector, solver diagnostics.
- Invariants: input object is immutable; no external I/O; matrix dimensions agree with grid; declared scheme is recorded.
- Failure behavior: controlled numerical failure with residual and iteration context; never return partial output as verified.

**EvidenceReceipt**
- Contains: action ID, actor ID, policy hash, request hash, code version, environment hash, result hash, method, tolerances, verification state, and excluded claims.

## Data flow
User request -> canonicalization -> validation -> authority gate -> immutable run directory -> solver -> diagnostics -> result hashing -> evidence receipt -> optional independent replay.

## Authority flow
The owner authorizes execution scope. The authority gate may permit or deny; it cannot broaden scope. The solver has computation authority only. The verifier may read artifacts and execute isolated reproduction but may not rewrite results or acceptance criteria.

## Trust boundaries
TB1: untrusted user input to validation. TB2: authorized orchestration to pure solver. TB3: mutable runtime to append-only evidence store. TB4: claimant-controlled artifacts to independent verification environment.

## Failure and recovery
Invalid input: deny before run creation. Numerical instability or singular system: mark failed, preserve diagnostics, no success receipt. Interrupted run: preserve immutable inputs and incomplete status; replay from the beginning. Corrupt result hash: quarantine artifact and deny verification. Evidence-store failure: result may be retained as unverified but cannot be promoted.

## Alternatives and tradeoffs
A monolithic CLI is simpler but weakens isolation and independent verification. A microservice design adds operational complexity without benefit for the offline-first target. Selected: modular monolith with pure solver kernel and explicit internal contracts.

## Implementation sequence
1. Canonical schemas and unit validation. 2. Pure solver with manufactured-solution tests. 3. Evidence receipt and content-addressed storage. 4. Replay. 5. Authority gate. 6. independent verifier. 7. owner acceptance workflow.

## Verification plan
- Analytical/manufactured solution convergence study using \(L_2\) and \(L_\infty\) norms.
- Time-step and grid refinement; estimate observed order \(p=\log(E_h/E_{h/2})/\log 2\).
- Boundary, invalid-input, interruption, corruption, and denial tests.
- Deterministic replay comparison by result hash and tolerance-bounded array comparison.
- Trace every requirement R1-R6 to test and evidence IDs.

## Open human decisions
D1. Approve required boundary-condition families. D2. Set maximum resource budget. D3. Define evidence retention and deletion policy. D4. Select the proof standard required before release.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Architect output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Planner and Implementer: approved architecture version, requirement-to-component map, interfaces, trust boundaries, open owner decisions, and verification plan. Implementation authority is not implied.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Invented current architecture
- undefined interfaces
- hidden tradeoffs
- implementation presented as proof
- unresolved owner decisions silently made

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
