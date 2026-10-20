# CETA-11.04.03 - Cancellation Evidence Recorder

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-11.04.03 |
| Subsystem | [11-EXECUTION-AND-ISOLATION](../README.md) |
| Component | [11.04 Stop And Cancellation](README.md) |
| Planned source basename | cancellation-evidence-recorder |
| Logical source path | ceta/execution-and-isolation/stop-and-cancellation/cancellation-evidence-recorder |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Observation, measurement, and evidence capture |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Record request time, admission closure, worker acknowledgements, observed termination, committed effects, and unresolved effects. Avoid describing already completed external effects as undone.

The required observable success is: **The cancellation report distinguishes prevented, completed, and uncertain effects.** The specifically prohibited behavior is: **A stop button click alone produces a successful cancellation receipt.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes.

Subsystem invariant: **Authorization is bound to exact inputs and target identity and rechecked at the effect boundary. Isolation is qualified on the actual operating environment.**

Component invariant: **Stop acknowledgement, worker termination, and effect completion are separate facts.**

Write observations only through the canonical evidence or state owner. Observation should not mutate the target. If a probe itself changes the target, model it as a separately authorized operation. Avoid recursive audit loops: recording an evidence event does not demand an infinite chain of new events. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `CancellationEvidenceRecorderInput`, `CancellationEvidenceRecorderResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| stop_id | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| target_scope | record | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| stop_generation | integer | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| deadline | duration | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| observed_stop_state | enum | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| startObservation | CancellationEvidenceRecorderInput + validated operation context | CancellationEvidenceRecorderResult | Bind a bounded observation session to the exact source, worker, task, or environment identity. |
| recordObservation | CancellationEvidenceRecorderInput + validated operation context | CancellationEvidenceRecorderResult | Validate sequence, time context, source authenticity, and size before storing or publishing an attributed observation. |
| finalizeObservation | CancellationEvidenceRecorderInput + validated operation context | CancellationEvidenceRecorderResult | Flush accepted records, report gaps and residual uncertainty, and close resources without inventing missing events. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [execution-request](../../INTERFACE-CONTRACTS/EXECUTION/execution-request.contract.md) | The normalized immutable request is approved before dispatch and is compared again at use time. Any changed input, effect, tool revision, or target requires reevaluation. |
| [intended-effect](../../INTERFACE-CONTRACTS/EXECUTION/intended-effect.contract.md) | Every transitive effect is declared. Reversibility describes an actual compensating mechanism, not merely local state rollback. |
| [isolation-context](../../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md) | Required restrictions must be qualified and observed active for the actual worker generation. Unsupported restrictions block the affected action. |
| [stop-signal](../../INTERFACE-CONTRACTS/EXECUTION/stop-signal.contract.md) | Stop closes new admission before waiting for worker acknowledgement. Requested, acknowledged, terminated, and effects-reconciled are separately observed stages. |
| [uncertain-operation](../../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md) | Uncertainty is a durable state requiring target inspection or authoritative receipts before replay. A new attempt or compensation requires current authority. |
| [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | Complete requires declared outputs and observed effects. Cancellation and uncertainty preserve already committed effects; an exit code does not override contradictory observations. |
| [capability-token](../../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md) | The token is a scoped grant, not a general role. Check its entire ancestry and current revocation at use time; consume single-use admission atomically with the durable operation record. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-11.04.03` to `ceta/execution-and-isolation/stop-and-cancellation/cancellation-evidence-recorder` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Record request time, admission closure, worker acknowledgements, observed termination, committed effects, and unresolved effects. Avoid describing already completed external effects as undone.
5. Integrate that behavior into this component sequence: Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome.
6. Enforce the component invariant before publishing any accepted output: Stop acknowledgement, worker termination, and effect completion are separate facts.
7. Identify the observation source and its qualified visibility first. Capture ordered events with correlation and generation, use bounded buffers and backpressure, and surface dropped ranges or stale samples. Keep raw observations separate from normalization and interpretation. Verify content references before finalization; redact sensitive values according to policy while retaining permitted integrity metadata. Measurement reports include method, units, sample window, and whether values were measured, estimated, or reported.
8. Use source sequence and process generation to distinguish duplicates, reorderable delivery, and actual gaps. Duplicate transport delivery cannot double-count usage or events.
9. Resume from the last durable cursor when the source supports it; otherwise record a gap and reestablish observation. Never infer absence of effects solely from a missing observer record.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-11.04.01 / stop-signal-controller](stop-signal-controller.file.README.md), [CETA-11.04.02 / running-operation-terminator](running-operation-terminator.file.README.md).

Required subsystem construction prerequisites: [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md).

Use canonical interfaces to break runtime dependency cycles. Register the resulting implementation through the actual local application's composition mechanism. Exercise at least one real producer-consumer path after unit tests; a mock-only result does not qualify integration.

## 9. State, concurrency, and cancellation

Use source sequence and process generation to distinguish duplicates, reorderable delivery, and actual gaps. Duplicate transport delivery cannot double-count usage or events.

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


Resume from the last durable cursor when the source supports it; otherwise record a gap and reestablish observation. Never infer absence of effects solely from a missing observer record. Reversing local state does not undo an external message, transfer, or independently committed operation. Compensation must be separately authorized and verified against current target state.

## 11. Security, privacy, and evidence

Treat external content, model output, filenames, tool payloads, and imported manifests as untrusted until their specific schema and scope checks pass. Never promote such content into constitutional rules or owner authority. Preserve exact-source attribution and minimize secret exposure. Record input and output digests, source revision, relevant policy and authority generations, actual observations, and result classification through the canonical evidence service. A digest establishes byte binding; it does not establish truth or complete effect coverage.

## 12. Required tests and observable acceptance

Every row is a construction obligation. Initial execution state for this package is **NOT EXECUTED**; replace it only with a real source-bound result during implementation.

| Acceptance ID | Case | Expected observation and procedure |
| --- | --- | --- |
| AT-CETA-11.04.03-01 | Required end-to-end behavior | The cancellation report distinguishes prevented, completed, and uncertain effects. Procedure: Use a fixture containing valid stop_id and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-11.04.03-02 | Specific prohibited behavior | A stop button click alone produces a successful cancellation receipt. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-11.04.03-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-11.04.03-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-11.04.03-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-11.04.03-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-11.04.03-07 | Duplicate and concurrent use | Duplicate delivery and concurrent requests do not corrupt canonical state, repeat unapproved effects, or bypass exclusive ownership. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-11.04.03-08 | Recovery and reconstruction | Restart preserves committed state, drafts, known revocations, and unresolved effects; recovery does not blindly replay prior actions. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-11.04.03-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-11.04.03-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R10 Tool And Execution Engineer](../../AGENT-ROLES/R10-TOOL-AND-EXECUTION-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
