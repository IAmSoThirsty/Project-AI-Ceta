# Role 05 - Security Auditor Expected Output

Role class: CHALLENGE
Source basis: *Thirsty's Agents 101*, Role 05, pages 151-156.

## Primary function

Evaluate systems, implementations, configurations, workflows, and evidence for security weaknesses, trust
violations, exposed attack surfaces, inadequate controls, and unsupported security claims.

## Core responsibility

Determine whether defined security requirements are implemented, enforceable, testable, and supported
by evidence.

## Non-negotiable output contract

1. Audit objective.
2. Scope.
3. Exclusions.
4. Assets.
5. Threat model.
6. Trust boundaries.
7. Security requirements.
8. Methods used.
9. Evidence examined.
10. Confirmed controls.
11. Findings.
12. Severity and confidence.
13. Attack paths.
14. Remediation requirements.
15. Verification procedures.
16. Residual risks.
17. Unsupported claims.
18. Accepted risks.
19. Unresolved questions.
20. Overall security posture, stated with appropriate limits.

## Completion conditions inherited from the source role contract

- Scope and exclusions are explicit.
- Security claims have been compared with evidence.
- Findings are reproducible or clearly marked as unverified.
- Severity is justified.
- Remediation and closure evidence are defined.
- Residual risk is visible.
- No absolute security guarantee is asserted.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | Security audit is limited to a synthetic design; no live penetration testing was performed.

## Audit objective
Determine whether the proposed local thermal-simulation service prevents unauthorized execution, path traversal, evidence tampering, and false promotion of unverified results.

## Scope
Request ingestion, local artifact storage, authority gate, solver process, evidence ledger, replay, and verifier interface. Excluded: operating-system hardening, physical access, supply-chain audit beyond dependency locking, and network perimeter controls.

## Assets
Input datasets, solver configuration, executable artifact, result arrays, evidence receipts, policy files, actor identities, and continuity records.

## Threat model
Adversary has an unprivileged local account or can submit crafted requests. It may attempt to read arbitrary files, overwrite evidence, replay an old authorization, inject non-finite values, substitute a result artifact, or cause resource exhaustion. Administrator compromise is outside scope.

## Trust boundaries
TB1 untrusted request -> validator. TB2 orchestrator -> sandboxed solver. TB3 solver output -> content-addressed store. TB4 claimant artifacts -> independent verifier. TB5 mutable policy configuration -> signed/versioned policy loader.

## Security requirements
SR1 canonicalize and confine all paths. SR2 deny missing or stale authority. SR3 bind authorization to actor, action, scope, artifact, and policy version. SR4 immutable evidence after finalization. SR5 resource ceilings. SR6 no secrets in source or logs. SR7 verifier cannot mutate the target. SR8 replay tokens are single-purpose or idempotently rejected.

## Methods
Design review, data-flow analysis, abuse-case enumeration, negative-test design, and manual inspection of the synthetic interface contracts.

## Confirmed controls
The design separates validation, authority, computation, storage, and verification. The solver is intended to run without network or arbitrary file access. Content addressing supports substitution detection.

## Findings
S-01 **High / high confidence:** authorization receipt lacks an explicit nonce or replay state. Attack path: capture an approved request and resubmit it after authority revocation. Remediation: bind a unique action ID, expiry, policy hash, and replay state; add denial tests.
S-02 **High / medium confidence:** "local path" is not yet defined as a canonical root-constrained path. Attack path: `../` traversal or symlink escape. Remediation: resolve against an approved root, reject escapes after canonicalization, and test symlink cases.
S-03 **Medium / high confidence:** evidence ledger append-only behavior is stated but no enforcement mechanism or integrity verification is defined. Remediation: immutable file permissions or append-only database semantics plus chained hashes and independent verification.
S-04 **Medium / medium confidence:** resource exhaustion controls are unspecified. Remediation: validate grid dimensions and time steps, estimate memory before allocation, impose CPU/time ceilings, and preserve a controlled failure receipt.

## Verification procedures
For each remediation, execute a negative test with a known prohibited input, capture the denial receipt, verify no protected state changed, and independently inspect the audit event. Retest under the exact release artifact.

## Residual risks
A privileged local administrator can still replace binaries or evidence unless platform attestation is introduced. Dependency compromise is only partially addressed by locking and hashes.

## Unsupported security claims
"Sandboxed," "append-only," and "replay-protected" remain design intentions until implementation and negative-test evidence exist.

## Overall posture
Conditionally promising architecture; not security-verified. High-severity authorization and path-boundary requirements must be implemented and retested before release.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded Security Auditor output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to Implementer and Tester: reproducible finding, attack path, affected trust boundary, remediation requirement, negative-test procedure, residual risk, and retest gate.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Absolute security guarantee
- scope or exclusions absent
- severity without attack path
- theoretical issue presented as reproduced
- remediation without retest

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
