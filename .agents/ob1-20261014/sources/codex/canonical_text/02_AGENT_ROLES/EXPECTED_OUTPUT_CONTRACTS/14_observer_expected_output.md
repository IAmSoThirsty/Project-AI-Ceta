# Role 14 - Observer Expected Output

Role class: DEFINE
Source basis: *Thirsty's Agents 101*, Role 14, pages 206-212.

## Primary function

Capture, timestamp, classify, and report events, states, behaviors, signals, and changes without adding
unsupported interpretation, causation, judgment, or recommendation.

## Core responsibility

Produce a faithful and traceable record of what was directly detected, received, measured, or witnessed.

## Non-negotiable output contract

1. Observation objective.
2. Scope.
3. Sources.
4. Collection method.
5. Baseline state.
6. Observation timeline.
7. State transitions.
8. Recorded events.
9. Threshold triggers.
10. Data-quality status.
11. Missing or unavailable data.
12. Integrity protections.
13. Privacy controls.
14. Collection interruptions.
15. Direct observations.
16. Explicitly excluded interpretations.
17. Evidence references.
18. Observation limits.
19. Handoff destination.
20. Completion status.

## Completion conditions inherited from the source role contract

- Observation scope is explicit.
- Data sources are identified.
- Direct observation is separated from interpretation.
- Timestamps and ordering limits are preserved.
- Missing data is disclosed.
- Evidence integrity is documented.
- Collection remained within authorized boundaries.
- The resulting record can be reviewed independently.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Observation record is complete; no causal interpretation or remediation recommendation is included.

## Observation objective
Capture the complete state transition of one local thermal-simulation run from request receipt through evidence finalization.

## Scope and sources
Process events from orchestrator, authority gate, solver, result store, and evidence ledger; filesystem metadata under the approved run directory; monotonic and wall-clock timestamps. Excluded: unrelated processes, user content outside the run, and network traffic.

## Collection method
Subscribe to structured local events; snapshot the run directory before and after; compute hashes of declared artifacts; preserve raw event order and record clock source. Collection is read-only.

## Baseline state
REFERENCE FIXTURE at `2026-07-28T20:00:00-06:00`: orchestrator healthy; no active run; result store contains 12 finalized runs; policy hash `fixture-policy`; run directory `RUN-013` absent.

## Timeline
20:00:05.112 request `RUN-013` received. 20:00:05.118 canonical request hash recorded. 20:00:05.121 validation passed. 20:00:05.126 authority decision `permit` recorded. 20:00:05.130 solver process started. 20:00:05.411 solver emitted diagnostics. 20:00:05.430 result artifact written. 20:00:05.435 result hash recorded. 20:00:05.441 evidence receipt finalized. 20:00:05.447 run state changed to `awaiting_verification`.

## State transitions
`absent -> received -> validated -> authorized -> executing -> result_created -> evidence_finalized -> awaiting_verification`.

## Recorded events
18 events received; sequence numbers 4401-4418 contiguous. Two filesystem writes observed in the approved directory: result array and receipt. No network socket event was present in the subscribed source.

## Threshold triggers
Solver wall time exceeded neither the 2 s warning nor 5 s termination threshold. Peak resident memory fixture measurement: 84 MiB, below 512 MiB warning threshold.

## Data-quality status
Event sequence complete according to source counter. Wall clock resolution 1 ms; monotonic clock resolution 1 microsecond. Filesystem timestamp ordering is not used to infer exact write order because its resolution and buffering semantics differ.

## Missing or unavailable data
No kernel-level proof that network access was impossible; only the subscribed process event source reported none. CPU instruction-level behavior was not captured.

## Integrity and privacy
Raw event log hashed after collection. No source file content or unrelated user data retained. Result content hash recorded; result values not copied into the observation report.

## Direct observations
The authority permit event preceded the solver-start event in the captured stream. A finalized receipt exists and references the observed result hash. The run ended in `awaiting_verification`, not `verified`.

## Explicitly excluded interpretations
This record does not establish that the authority decision was correct, that the numerical result is accurate, that no unmonitored network activity occurred, or that the run is ready for release.

## Handoff
Verifier receives the event log hash, result and receipt identities, environment identity, and replay instructions.

## Completion status
Observation complete for the declared sources and interval; limitations remain as stated.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Observer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Analyst or Verifier: immutable observation record, source identities, timeline, data-quality limits, missing intervals, and explicit boundary between observation and interpretation.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Causation inferred from sequence
- missing data concealed
- collection outside scope
- estimate reported as direct measurement
- absence of observation treated as observation of absence

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
