# Role 15 - Memory Curator Expected Output

Role class: GOVERN
Source basis: *Thirsty's Agents 101*, Role 15, pages 213-219.

## Primary function

Select, classify, normalize, preserve, update, retrieve, and retire information intended for governed
short-term or long-term memory.

## Core responsibility

Maintain useful continuity without allowing memory to become an uncontrolled source of false
assumptions, stale authority, duplicated facts, privacy violations, or fabricated identity continuity.

## Non-negotiable output contract

1. Memory action requested.
2. Candidate information.
3. Eligibility decision.
4. Memory classification.
5. Source.
6. Normalized memory.
7. Verification status.
8. Sensitivity.
9. Retention rule.
10. Retrieval conditions.
11. Conflicts.
12. Supersession state.
13. Privacy controls.
14. Audit action.
15. Information rejected from retention.
16. Reason for rejection.
17. Deletion or correction status.
18. Remaining uncertainty.

## Completion conditions inherited from the source role contract

- Retention has a defined purpose.
- Source and provenance are recorded.
- Facts and inferences are separated.
- Sensitivity is classified.
- Retention and expiration rules are defined.
- Conflicts are handled transparently.
- Current authority overrides stale memory.
- Deletion and correction requests are respected.
- Retrieved memory remains relevant to the current task.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | Memory-curation decision applies only to the submitted synthetic candidates.

## Memory action requested
Retain durable project facts needed to resume the thermal-solver work without relying on chat history.

## Candidate information
C1 "Offline-first local operation is the authoritative deployment profile." C2 "Crank-Nicolson is the chosen solver." C3 "Fixture T-006 observed an undershoot of `3.8e-4 K`." C4 "The owner prefers concise reports." C5 Raw benchmark logs.

## Eligibility decisions
C1 eligible as an owner-authorized architectural decision if source and date are attached. C2 not eligible as settled fact because current analysis presents it as conditional and the owner has not approved the selection. C3 eligible as a time-bounded test observation tied to exact artifact/environment, not as a universal solver property. C4 rejected unless the preference is explicitly supplied for durable retention and remains relevant to agent operation. C5 retain by reference in the evidence store rather than duplicating raw logs in memory.

## Classification and normalization
M-001 Decision: "The authoritative production profile is offline-first local operation; hosted profiles are secondary unless later authorized." Source: owner decision record `<id/date>`. Verification: explicit instruction. Sensitivity: internal project context. Retention: until superseded or project closure.

M-002 Observation: "In test T-006 for artifact `<hash>` and environment `<hash>`, maximum undershoot was `3.8e-4 K` against a `1e-8 K` limit." Source: test report `<id>`. Verification: not independently reproduced. Retention: through remediation and one release cycle; then archive with test evidence.

## Retrieval conditions
Retrieve M-001 for deployment-model questions. Retrieve M-002 only for the affected artifact, solver behavior, remediation, or release review. Do not inject either into unrelated tasks.

## Conflicts and supersession
C2 conflicts with the current conditional recommendation. No "chosen solver" memory is created. If the owner later approves a solver, create a new decision record rather than rewriting historical analysis. M-002 is superseded only by a named retest; the original observation remains historically valid.

## Privacy controls
Store the minimum necessary project information. Do not retain unrelated personal attributes or raw user data. Access follows the project's authorized role boundary.

## Audit action
Record curator identity, timestamp, source IDs, normalization diff, retention rule, and rejected candidates with reasons.

## Information rejected
C2 as unapproved conclusion; C4 as insufficiently authorized and not necessary; C5 as duplicate raw evidence.

## Remaining uncertainty
The exact retention duration and archive location require owner policy. Until resolved, no irreversible deletion is performed.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Memory Curator output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to memory system and owner: normalized entries, provenance, sensitivity, retention/expiry, conflicts, supersession, rejected candidates, and audit record.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Every statement retained as truth
- inference stored as fact
- stale memory overrides current authority
- no retention purpose
- deletion/correction ignored

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
