# 23.02 - Contract Testing

## Purpose and boundary

This component belongs to [23-TESTING-AND-QUALIFICATION](../README.md) and owns the coordinated behavior below. Primary construction role: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Exercise canonical schemas and semantics on producers and consumers; test valid, invalid, stale, and adversarial inputs; bind results to exact contract revisions.

**Component invariant:** Passing schema validation alone does not establish semantic compatibility.

**Subsystem invariant:** Design completeness, test existence, test execution, and passed acceptance are separate states. Critical skipped or not-executed tests cannot satisfy release gates.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-23.02.01 / interface-contract-test-runner](interface-contract-test-runner.file.README.md) | Test required fields, types, bounds, version negotiation, error semantics, idempotency, and producer-consumer behavior for each shared contract. Include real integration paths. | Both sides agree on denied, partial, and uncertain outcomes as well as success. |
| [CETA-23.02.02 / governance-invariant-test-runner](governance-invariant-test-runner.file.README.md) | Exercise rule precedence, authority separation, proposal binding, policy amendments, and fail-closed behavior under missing or conflicting facts. Capture counterexamples. | A changed proposal invalidates its earlier approval in every supported entry path. |
| [CETA-23.02.03 / authority-boundary-test-runner](authority-boundary-test-runner.file.README.md) | Test principal binding, token audience, expiry, revocation races, delegation attenuation, replay, target identity, and single-use admission. Use concurrent and interrupted fixtures. | Revocation before effect admission blocks the effect even under concurrency. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| contract_ref | reference |
| producer_revision | text |
| consumer_revision | text |
| fixture_ref | reference |
| conformance_result | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md), [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md), [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md), [workload-admission](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md).

Implement declarations and conformance fixtures before effectful behavior. Use the existing composition mechanism to connect producers and consumers. The internal file list is an ownership map, not a forced call order. Pure checks remain separate from controlled effects, authoritative storage remains with its designated owner, and UI components issue authenticated native commands rather than performing privileged actions themselves.

## Failure and recovery

A malformed record is rejected before privileged work. Missing references, stale versions, invalid authority, and unsupported environment capabilities produce explicit blocked or failed results. An interruption after possible dispatch preserves uncertainty and invokes canonical reconciliation before retry. Keep source and output versions distinct, preserve user drafts and known security decisions, and do not destroy original evidence during repair.

## Construction sequence and acceptance

1. Inspect the mapped local component and record reuse, extension, or creation decisions.
2. Freeze shared contracts and acquire file ownership for the assigned builder.
3. Implement each linked unit and its explicit positive and negative fixtures.
4. Connect the component flow above through real local interfaces and test adverse transitions.
5. Inject interruption, concurrent update, cancellation, and stale-authority conditions where applicable.
6. Hand exact source, output artifacts, and test records to the independent verifier; accept only current evidence.

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
