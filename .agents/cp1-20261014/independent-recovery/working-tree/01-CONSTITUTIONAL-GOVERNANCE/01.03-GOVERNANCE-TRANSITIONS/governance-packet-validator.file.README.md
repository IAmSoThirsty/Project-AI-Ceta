# CETA-01.03.02 - Governance Packet Validator

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-01.03.02 |
| Subsystem | [01-CONSTITUTIONAL-GOVERNANCE](../README.md) |
| Component | [01.03 Governance Transitions](README.md) |
| Planned source basename | governance-packet-validator |
| Logical source path | ceta/constitutional-governance/governance-transitions/governance-packet-validator |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Validation and evaluation |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Validate complete packets linking policy revision, proposal digest, identity proof, approval evidence, and validity period. Reject dangling references and unauthorized signers.

The required observable success is: **Every referenced approval resolves to the same proposal digest and active authority.** The specifically prohibited behavior is: **A genuine approval for a different proposal is included in the packet.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions.

Subsystem invariant: **Capability, authority, evidence, and preference remain distinct. Policy activation requires a traceable approved transition; untrusted text cannot amend governing rules.**

Component invariant: **Approvals authorize the exact proposal and cannot be reused for changed effects.**

Keep the decision core free of external effects. Return findings to the caller, which owns persistence and any proposed action. Do not mutate the object being verified to make it pass. Cache only with complete source, policy, and revocation generations; invalidate on any relevant change. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `GovernancePacketValidatorInput`, `GovernancePacketValidatorResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| proposal_id | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| input_digest | digest | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| effect_set | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| approval_refs | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| decision_generation | integer | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| evaluate | GovernancePacketValidatorInput + validated operation context | GovernancePacketValidatorResult | Accept the typed request and a pinned read-only dependency snapshot; return a complete decision with reasons and supporting references. |
| explain | GovernancePacketValidatorInput + validated operation context | GovernancePacketValidatorResult | Return the exact failed predicates or accepted constraints without exposing restricted input content. |
| verifyCompatibility | GovernancePacketValidatorInput + validated operation context | GovernancePacketValidatorResult | Check schema and dependency revisions before evaluating domain semantics. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [policy-decision](../../INTERFACE-CONTRACTS/AUTHORITY/policy-decision.contract.md) | Allow applies only to the exact proposal under the specified policy and authority generation. Missing required facts and evaluation errors do not allow execution. |
| [governance-packet](../../INTERFACE-CONTRACTS/AUTHORITY/governance-packet.contract.md) | Every approval binds the same proposal, eligible authority, and validity interval. Duplicate principal identities never count as distinct quorum votes. |
| [principal-identity](../../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md) | Identity is stable across credential rotation; display labels never determine identity. Credential references never expose secret values. |
| [capability-token](../../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. |
| [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | One canonical owner mutates the aggregate through expected-version checks. Historical corrections append rather than rewrite prior events. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-01.03.02` to `ceta/constitutional-governance/governance-transitions/governance-packet-validator` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Validate complete packets linking policy revision, proposal digest, identity proof, approval evidence, and validity period. Reject dangling references and unauthorized signers.
5. Integrate that behavior into this component sequence: Create a complete transition proposal; bind approvals to its digest; validate quorum and revocation; commit the decision and its evidence atomically.
6. Enforce the component invariant before publishing any accepted output: Approvals authorize the exact proposal and cannot be reused for changed effects.
7. Use an explicit ordered validation pipeline: shape and bounds, referenced-object existence, version and identity binding, domain predicates, then final outcome. Accumulate independent findings when safe; stop before expensive or privileged work when a prerequisite fails. Preserve the exact predicate that produced each result. Define deterministic tie-breaking and rule precedence; when semantic evaluation uses a model, label that assessment and preserve its input and output evidence rather than claiming deterministic truth.
8. Concurrent evaluations of identical pinned inputs must not corrupt shared caches or mix source generations. Where inference is involved, preserve each separate observed assessment and do not assert identical output.
9. Reevaluate a pure check from pinned inputs after interruption. A prior allow result must be revalidated before a later effect; replaying a check is not replaying the action it evaluated.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Create a complete transition proposal; bind approvals to its digest; validate quorum and revocation; commit the decision and its evidence atomically.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-01.03.01 / transition-proposal-builder](transition-proposal-builder.file.README.md), [CETA-01.03.03 / governance-quorum-controller](governance-quorum-controller.file.README.md).

Required subsystem construction prerequisites: [00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md).

Use canonical interfaces to break runtime dependency cycles. Register the resulting implementation through the actual local application's composition mechanism. Exercise at least one real producer-consumer path after unit tests; a mock-only result does not qualify integration.

## 9. State, concurrency, and cancellation

Concurrent evaluations of identical pinned inputs must not corrupt shared caches or mix source generations. Where inference is involved, preserve each separate observed assessment and do not assert identical output.

State that is authoritative is versioned and owned by the designated subsystem. Derived state is rebuildable and has source-generation invalidation. Long-running work accepts cancellation, checks deadlines at bounded intervals, and preserves already observed effects. Pure checks stop safely without mutating the source. Presentation components cancel subscriptions and rendering work without claiming the underlying operation has stopped unless native evidence confirms it.

## 10. Failure and recovery behavior

| Condition | Mandatory handling |
| --- | --- |
| Malformed or incompatible input | Return a stable validation or compatibility error before privileged work; retain safe diagnostic context. |
| Missing, stale, or contradictory dependency | Return blocked, conflict, or unresolved as appropriate; identify the exact dependency and preserve canonical source records. |
| Expired or revoked authority | Prevent the affected effect or restricted read; invalidate stale decisions; request a new scoped decision where needed. |
| Resource pressure or cancellation | Close new admissions or bounded computation; preserve control, evidence, drafts, and recoverable state; report partial results accurately. |
| Interruption after possible effect | Persist uncertainty and inspect the actual target before retry; use the canonical recovery owner. |
| Evidence or storage failure | Do not fabricate a success record. Block new effects when required durable evidence cannot be reserved; preserve known observations for recovery. |


Reevaluate a pure check from pinned inputs after interruption. A prior allow result must be revalidated before a later effect; replaying a check is not replaying the action it evaluated. Reversing local state does not undo an external message, transfer, or independently committed operation. Compensation must be separately authorized and verified against current target state.

## 11. Security, privacy, and evidence

Treat external content, model output, filenames, tool payloads, and imported manifests as untrusted until their specific schema and scope checks pass. Never promote such content into constitutional rules or owner authority. Preserve exact-source attribution and minimize secret exposure. Record input and output digests, source revision, relevant policy and authority generations, actual observations, and result classification through the canonical evidence service. A digest establishes byte binding; it does not establish truth or complete effect coverage.

## 12. Required tests and observable acceptance

Every row is a construction obligation. Initial execution state for this package is **NOT EXECUTED**; replace it only with a real source-bound result during implementation.

| Acceptance ID | Case | Expected observation and procedure |
| --- | --- | --- |
| AT-CETA-01.03.02-01 | Required end-to-end behavior | Every referenced approval resolves to the same proposal digest and active authority. Procedure: Use a fixture containing valid proposal_id and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-01.03.02-02 | Specific prohibited behavior | A genuine approval for a different proposal is included in the packet. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-01.03.02-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-01.03.02-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-01.03.02-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-01.03.02-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-01.03.02-07 | Duplicate and concurrent use | Repeated evaluation of the same pinned input does not mutate the source or mix generations; model-assisted assessments remain separately attributed. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-01.03.02-08 | Recovery and reconstruction | Reconstruction from pinned source and configuration preserves required lineage; a fresh nondeterministic run is labeled separately. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-01.03.02-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-01.03.02-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R03 Constitutional Governance Engineer](../../AGENT-ROLES/R03-CONSTITUTIONAL-GOVERNANCE-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S06 Constitutional Policy Implementation](../../AGENT-SKILLS/S06-CONSTITUTIONAL-POLICY-IMPLEMENTATION/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
