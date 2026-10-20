# Role 17 - Red Team Expected Output

Role class: CHALLENGE
Source basis: *Thirsty's Agents 101*, Role 17, pages 228-236.

## Primary function

Apply authorized adversarial pressure to systems, agents, policies, workflows, assumptions,
implementations, and defenses to discover exploitable weaknesses, unsafe interactions, control failures,
and paths through which intended protections may be bypassed.

## Core responsibility

Actively attempt to falsify security, safety, governance, resilience, and readiness claims under a defined
threat model while preserving scope, evidence integrity, operational safety, and human authority.

## Non-negotiable output contract

1. Authorized objective.
2. Scope.
3. Exclusions.
4. Rules of Engagement.
5. Threat actor model.
6. Protected assets.
7. Critical invariants.
8. Attack-surface map.
9. Adversarial hypotheses.
10. Techniques attempted.
11. Attack paths.
12. Controls encountered.
13. Successful and unsuccessful attempts.
14. Findings.
15. Severity and confidence.
16. Detection and response observations.
17. Containment and recovery observations.
18. Evidence.
19. Cleanup status.
20. Residual attack surface.
21. Required remediation.
22. Retest requirements.
23. Testing limitations.
24. What evidence would change the conclusion.

## Completion conditions inherited from the source role contract

- Authorization and scope are explicit.
- The threat actor model is defined.
- Material attack paths have been tested or marked untested.
- Successful and unsuccessful attempts are recorded.
- Findings are reproducible or clearly identified as theoretical.
- Operational impact remained within authorized limits.
- Critical findings were escalated.
- Cleanup was performed.
- Residual risk and testing limitations remain visible.
- No claim exceeds the tested conditions.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Created | Authorized adversarial test plan and synthetic findings are documented; no live exploitation was performed.

## Authorized objective
Attempt to bypass the thermal-solver authority gate, substitute results, replay approvals, and induce false verification while preserving local data and remaining inside the isolated test environment.

## Scope, exclusions, and rules of engagement
In scope: test instance, synthetic datasets, request API, local result store, receipt validator, replay workflow. Excluded: production, unrelated accounts, destructive persistence, credential theft, denial of service beyond declared resource ceilings, and social engineering. Stop immediately on scope ambiguity, evidence-store corruption, or unexpected external connectivity.

## Threat actor model
Unprivileged local user able to submit requests and read its own artifacts; no administrator privilege. Goal: cause unauthorized execution or obtain a verified status for altered output.

## Protected assets and invariants
Only authorized actors may execute within approved scope. A result cannot become verified without matching artifact, request, environment, and evidence identities. Denied actions must not change protected state. Finalized evidence must detect alteration.

## Attack-surface map
Request canonicalization, path handling, authorization token, policy cache, solver launch, result naming, receipt creation, replay endpoint, status transition, and verifier input loader.

## Adversarial hypotheses
H1 encoded path traversal escapes the run root. H2 a permitted token can be replayed after revocation. H3 a result file can be replaced between hashing and receipt finalization. H4 status API accepts `verified` from an Implementer. H5 NaN values evade range checks and poison comparisons.

## Techniques and synthetic outcomes
H1 unsuccessful: canonicalized path rejected after symlink resolution. H2 successful in fixture: token accepted twice because no consumed-action state was checked. H3 unsuccessful under atomic finalize path; race window not proven absent on all filesystems. H4 successful: role check enforced write access but not allowed state transitions. H5 successful: JSON parser accepted NaN in a non-standard mode and downstream `value < limit` comparisons returned false without rejection.

## Findings
RT-01 Critical/high confidence: self-promotion to `verified`. RT-02 High/high confidence: replayed authorization. RT-03 High/high confidence: non-finite input bypass. RT-04 Medium/low confidence: cross-filesystem finalize race remains theoretical and requires platform-specific testing.

## Detection and response
Fixture audit log recorded replay but generated no alert. Unauthorized status transition produced a normal success event. NaN input caused a later numerical failure, not an ingress denial.

## Containment and recovery
Disable verification-state writes from non-Verifier roles. Invalidate outstanding tokens. Reject non-finite values during canonical validation. Quarantine fixture artifacts. Preserve evidence and reset test state.

## Required remediation and retest
Implement policy-enforced state transitions, one-action replay state, strict JSON/finite validation, and alert rules. Retest successful paths, negative paths, race conditions, and recovery. Verify no protected state changes on denial.

## Cleanup status
Synthetic test records archived; test tokens revoked; test result store reset. No production or external system touched.

## Residual attack surface
Administrator-level artifact replacement, dependency compromise, and filesystems without required atomicity remain outside the demonstrated controls.

## Conclusion limits
The fixture falsifies three protection claims for the modeled implementation. It does not establish exploitability in any live system until reproduced against the exact artifact.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Red Team output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Security Auditor, Implementer, and owner: rules of engagement, reproducible findings, evidence, impact, containment, cleanup, residual surface, and exact retest requirements.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Testing without explicit authorization
- production impact outside scope
- failed attempts omitted
- cleanup omitted
- theoretical attack presented as exploited

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
