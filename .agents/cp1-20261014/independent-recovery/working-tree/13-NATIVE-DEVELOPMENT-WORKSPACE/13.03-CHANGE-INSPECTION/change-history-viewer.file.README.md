# CETA-13.03.03 - Change History Viewer

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-13.03.03 |
| Subsystem | [13-NATIVE-DEVELOPMENT-WORKSPACE](../README.md) |
| Component | [13.03 Change Inspection](README.md) |
| Planned source basename | change-history-viewer |
| Logical source path | ceta/native-development-workspace/change-inspection/change-history-viewer |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Native presentation and interaction |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Show source revisions, agent and human attribution, verification results, and rollback references. Preserve history for projects without external revision services.

The required observable success is: **A historical change resolves to its exact artifacts and review evidence.** The specifically prohibited behavior is: **A deleted branch or renamed workspace makes accepted history unverifiable.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Provide a local project explorer, source editor, diff review, terminal, revision management, previews, and recoverable workspace state.

Subsystem invariant: **The interface presents and proposes changes; native services enforce authority and filesystem boundaries. Local projects remain usable without remote hosting.**

Component invariant: **Approval binds to the displayed diff and target identities, not a mutable staging label.**

The view may hold drafts and presentation preferences, but privileged effects are proposed through authenticated native commands. A disabled control is not enforcement. Never store reusable credentials in renderer state or expose restricted details through previews, tooltips, counts, or errors. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `ChangeHistoryViewerInput`, `ChangeHistoryViewerResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| change_set_id | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| before_ref | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| after_ref | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| staging_state | enum | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| decision_ref | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| loadView | ChangeHistoryViewerInput + validated operation context | ChangeHistoryViewerResult | Read authorized native state and construct an attributed view model with source generation and freshness. |
| handleIntent | ChangeHistoryViewerInput + validated operation context | ChangeHistoryViewerResult | Translate a user interaction into a typed native request bound to the visible proposal and current project. |
| reconcileView | ChangeHistoryViewerInput + validated operation context | ChangeHistoryViewerResult | Refresh after a native result, reconnect, or state invalidation while preserving safe local drafts and focus. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [desktop-command](../../INTERFACE-CONTRACTS/USER-INTERACTION/desktop-command.contract.md) | Native services authenticate and validate each command regardless of renderer state. Effectful commands resolve into approved execution requests. |
| [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | Invocation arguments are normalized before approval and immutable afterward. Every invocation goes through the common execution gate. |
| [human-decision-request](../../INTERFACE-CONTRACTS/USER-INTERACTION/human-decision-request.contract.md) | The request exposes exact scope and consequences and expires when its proposal changes. Approval is never inferred from viewing or silence. |
| [execution-result](../../INTERFACE-CONTRACTS/EXECUTION/execution-result.contract.md) | Complete requires declared outputs and observed effects. Cancellation and uncertainty preserve already committed effects; an exit code does not override contradictory observations. |
| [persistent-checkpoint](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md) | Checkpoints preserve observed effects and continuation, not reusable authentication. Resume validates current authority and target state. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-13.03.03` to `ceta/native-development-workspace/change-inspection/change-history-viewer` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Show source revisions, agent and human attribution, verification results, and rollback references. Preserve history for projects without external revision services.
5. Integrate that behavior into this component sequence: Compute exact changes; present text and binary summaries; stage selected modifications; obtain scoped approval; preserve revision history and recovery links.
6. Enforce the component invariant before publishing any accepted output: Approval binds to the displayed diff and target identities, not a mutable staging label.
7. Derive the view from authoritative state rather than optimistic success flags. Preserve loading, empty, running, blocked, failed, partial, uncertain, and verified outcomes distinctly. Bind interactive controls to exact object and proposal revisions. Validate deep links and payload bounds, support keyboard and assistive interaction, and refresh stale decisions before accepting input. Use bounded rendering for large histories and preserve full evidence through inspectable references.
8. Ignore or label stale results from a previous project or view generation. Keep user edits separate from incoming model or background updates and require reconciliation before overwriting drafts.
9. Restore presentation state without replaying actions. Reload actual task and process state after reconnect; a previous click or pending spinner is not proof that an operation started or completed.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Compute exact changes; present text and binary summaries; stage selected modifications; obtain scoped approval; preserve revision history and recovery links.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-13.03.01 / file-diff-presenter](file-diff-presenter.file.README.md), [CETA-13.03.02 / change-staging-controller](change-staging-controller.file.README.md).

Required subsystem construction prerequisites: [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [12-ENGINEERING-INTELLIGENCE](../../12-ENGINEERING-INTELLIGENCE/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

Use canonical interfaces to break runtime dependency cycles. Register the resulting implementation through the actual local application's composition mechanism. Exercise at least one real producer-consumer path after unit tests; a mock-only result does not qualify integration.

## 9. State, concurrency, and cancellation

Ignore or label stale results from a previous project or view generation. Keep user edits separate from incoming model or background updates and require reconciliation before overwriting drafts.

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


Restore presentation state without replaying actions. Reload actual task and process state after reconnect; a previous click or pending spinner is not proof that an operation started or completed. Reversing local state does not undo an external message, transfer, or independently committed operation. Compensation must be separately authorized and verified against current target state.

## 11. Security, privacy, and evidence

Treat external content, model output, filenames, tool payloads, and imported manifests as untrusted until their specific schema and scope checks pass. Never promote such content into constitutional rules or owner authority. Preserve exact-source attribution and minimize secret exposure. Record input and output digests, source revision, relevant policy and authority generations, actual observations, and result classification through the canonical evidence service. A digest establishes byte binding; it does not establish truth or complete effect coverage.

## 12. Required tests and observable acceptance

Every row is a construction obligation. Initial execution state for this package is **NOT EXECUTED**; replace it only with a real source-bound result during implementation.

| Acceptance ID | Case | Expected observation and procedure |
| --- | --- | --- |
| AT-CETA-13.03.03-01 | Required end-to-end behavior | A historical change resolves to its exact artifacts and review evidence. Procedure: Use a fixture containing valid change_set_id and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-13.03.03-02 | Specific prohibited behavior | A deleted branch or renamed workspace makes accepted history unverifiable. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-13.03.03-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-13.03.03-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-13.03.03-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-13.03.03-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-13.03.03-07 | Duplicate and concurrent use | Duplicate delivery and concurrent requests do not corrupt canonical state, repeat unapproved effects, or bypass exclusive ownership. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-13.03.03-08 | Recovery and reconstruction | Restart preserves committed state, drafts, known revocations, and unresolved effects; recovery does not blindly replay prior actions. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-13.03.03-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-13.03.03-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R11 Engineering Workspace Engineer](../../AGENT-ROLES/R11-ENGINEERING-WORKSPACE-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S01 Local Baseline Inspection](../../AGENT-SKILLS/S01-LOCAL-BASELINE-INSPECTION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S15 Desktop Interface Implementation](../../AGENT-SKILLS/S15-DESKTOP-INTERFACE-IMPLEMENTATION/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
