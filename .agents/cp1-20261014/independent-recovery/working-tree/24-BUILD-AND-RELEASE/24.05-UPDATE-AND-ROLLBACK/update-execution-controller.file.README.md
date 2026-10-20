# CETA-24.05.02 - Update Execution Controller

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-24.05.02 |
| Subsystem | [24-BUILD-AND-RELEASE](../README.md) |
| Component | [24.05 Update And Rollback](README.md) |
| Planned source basename | update-execution-controller |
| Logical source path | ceta/build-and-release/update-and-rollback/update-execution-controller |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Controlled lifecycle and effectful coordination |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Stage the update, quiesce affected work, preserve drafts and data, execute migrations, switch artifacts, and run post-update checks. Recover interrupted stages without mixed-version execution.

The required observable success is: **A power interruption yields either a valid prior installation or a recoverable staged update.** The specifically prohibited behavior is: **New binaries run against a partially migrated schema.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence.

Subsystem invariant: **Release completion is determined by actual installed behavior and current evidence, not generated file volume, successful compilation, or a persuasive report.**

Component invariant: **Rollback preserves known revocations, deletion decisions, and user data created after the recovery point where required.**

Route worker-visible filesystem, process, network, message, and extension actions through the common execution gate. Canonical internal storage and trust operations use narrowly defined service authority from the bootstrap model, not ambient worker privilege. Declare every transitive effect and preserve current revocation, cancellation, and target identity checks. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `UpdateExecutionControllerInput`, `UpdateExecutionControllerResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| update_id | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| current_release | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| target_release | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| migration_plan | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| recovery_point | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| prepareOperation | UpdateExecutionControllerInput + validated operation context | UpdateExecutionControllerResult | Validate exact inputs, dependencies, target identity, authority requirements, and expected effects; persist a stable operation identity. |
| executeOperation | UpdateExecutionControllerInput + validated operation context | UpdateExecutionControllerResult | Acquire current admission and scoped resources, perform only approved effects, and capture actual results with cancellation support. |
| stopOrReconcile | UpdateExecutionControllerInput + validated operation context | UpdateExecutionControllerResult | Close new admission, stop owned work, inspect already committed and uncertain effects, and return a recoverable outcome. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. |
| [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md) | Receipts bind exact operation evidence within a declared trust model. Integrity, attribution, observation completeness, and functional success remain separate checks. |
| [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md) | Recovery reports actual restored and unresolved state, including drafts and identity preservation. Older backups cannot silently remove known security decisions. |
| [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md) | One canonical owner mutates the aggregate through expected-version checks. Historical corrections append rather than rewrite prior events. |
| [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | Each relation has a specific supported meaning and valid endpoints. Co-occurrence and visual proximity do not create a causal edge. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-24.05.02` to `ceta/build-and-release/update-and-rollback/update-execution-controller` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Stage the update, quiesce affected work, preserve drafts and data, execute migrations, switch artifacts, and run post-update checks. Recover interrupted stages without mixed-version execution.
5. Integrate that behavior into this component sequence: Validate the exact update; preflight compatibility and capacity; create a recovery point; apply staged changes; verify startup and data; roll back or forward-repair under declared rules.
6. Enforce the component invariant before publishing any accepted output: Rollback preserves known revocations, deletion decisions, and user data created after the recovery point where required.
7. Implement a durable lifecycle with explicit prepared, admitted, running, stopping, complete, failed, partial, and uncertain outcomes as applicable. Validate all domain preconditions before dispatch, pin input and target digests, acquire resource and ownership leases atomically, and recheck authority at the effect boundary. Persist intent before external effects and reconcile actual resource state before retry. Publish results only after the specified durable boundary and retain a distinct compensation plan for reversible effects.
8. Use stable operation identities, expected versions, single-use consumption where required, and lease fencing. A timeout does not prove an effect failed; never claim exactly-once external behavior without a verified target-side idempotency or reconciliation mechanism.
9. Inspect the durable intent, local commit, worker identity, target version, and external receipt before choosing continuation, compensation, or human decision. Restore data and drafts without silently rerunning actions or reviving expired authority.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Validate the exact update; preflight compatibility and capacity; create a recovery point; apply staged changes; verify startup and data; roll back or forward-repair under declared rules.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-24.05.01 / update-package-validator](update-package-validator.file.README.md), [CETA-24.05.03 / release-rollback-manager](release-rollback-manager.file.README.md).

Required subsystem construction prerequisites: [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [03-COMPANION-INTELLIGENCE](../../03-COMPANION-INTELLIGENCE/README.md), [04-PERSISTENT-MEMORY](../../04-PERSISTENT-MEMORY/README.md), [05-CONTEXT-INTELLIGENCE](../../05-CONTEXT-INTELLIGENCE/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [12-ENGINEERING-INTELLIGENCE](../../12-ENGINEERING-INTELLIGENCE/README.md), [13-NATIVE-DEVELOPMENT-WORKSPACE](../../13-NATIVE-DEVELOPMENT-WORKSPACE/README.md), [14-AUTOMATION-AND-SCHEDULING](../../14-AUTOMATION-AND-SCHEDULING/README.md), [15-COMMUNICATION-AND-INTERACTION](../../15-COMMUNICATION-AND-INTERACTION/README.md), [16-KNOWLEDGE-AND-RESEARCH](../../16-KNOWLEDGE-AND-RESEARCH/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md), [21-EXTENSIONS-AND-INTEROPERABILITY](../../21-EXTENSIONS-AND-INTEROPERABILITY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md), [23-TESTING-AND-QUALIFICATION](../../23-TESTING-AND-QUALIFICATION/README.md).

Use canonical interfaces to break runtime dependency cycles. Register the resulting implementation through the actual local application's composition mechanism. Exercise at least one real producer-consumer path after unit tests; a mock-only result does not qualify integration.

## 9. State, concurrency, and cancellation

Use stable operation identities, expected versions, single-use consumption where required, and lease fencing. A timeout does not prove an effect failed; never claim exactly-once external behavior without a verified target-side idempotency or reconciliation mechanism.

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


Inspect the durable intent, local commit, worker identity, target version, and external receipt before choosing continuation, compensation, or human decision. Restore data and drafts without silently rerunning actions or reviving expired authority. Reversing local state does not undo an external message, transfer, or independently committed operation. Compensation must be separately authorized and verified against current target state.

## 11. Security, privacy, and evidence

Treat external content, model output, filenames, tool payloads, and imported manifests as untrusted until their specific schema and scope checks pass. Never promote such content into constitutional rules or owner authority. Preserve exact-source attribution and minimize secret exposure. Record input and output digests, source revision, relevant policy and authority generations, actual observations, and result classification through the canonical evidence service. A digest establishes byte binding; it does not establish truth or complete effect coverage.

## 12. Required tests and observable acceptance

Every row is a construction obligation. Initial execution state for this package is **NOT EXECUTED**; replace it only with a real source-bound result during implementation.

| Acceptance ID | Case | Expected observation and procedure |
| --- | --- | --- |
| AT-CETA-24.05.02-01 | Required end-to-end behavior | A power interruption yields either a valid prior installation or a recoverable staged update. Procedure: Use a fixture containing valid update_id and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-24.05.02-02 | Specific prohibited behavior | New binaries run against a partially migrated schema. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-24.05.02-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-24.05.02-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-24.05.02-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-24.05.02-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-24.05.02-07 | Duplicate and concurrent use | Duplicate delivery and concurrent requests do not corrupt canonical state, repeat unapproved effects, or bypass exclusive ownership. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-24.05.02-08 | Recovery and reconstruction | Restart preserves committed state, drafts, known revocations, and unresolved effects; recovery does not blindly replay prior actions. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-24.05.02-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-24.05.02-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R21 Build And Release Engineer](../../AGENT-ROLES/R21-BUILD-AND-RELEASE-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md), [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md), [S23 Release Qualification](../../AGENT-SKILLS/S23-RELEASE-QUALIFICATION/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
