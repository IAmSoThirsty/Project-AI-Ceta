# CETA-06.05.02 - Skill Revocation Controller

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-06.05.02 |
| Subsystem | [06-AGENT-SKILLS-AND-LEARNING](../README.md) |
| Component | [06.05 Skill Lifecycle](README.md) |
| Planned source basename | skill-revocation-controller |
| Logical source path | ceta/agent-skills-and-learning/skill-lifecycle/skill-revocation-controller |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Controlled lifecycle and effectful coordination |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Revoke exact skill revisions or a lineage, prevent new admissions, and signal affected running tasks. Record already committed effects and safe stopping boundaries.

The required observable success is: **A queued invocation cannot start after its skill revision is revoked.** The specifically prohibited behavior is: **A cached invocation bypasses the updated revocation generation.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Define, discover, qualify, invoke, revise, and revoke reusable native agent skills.

Subsystem invariant: **A learned procedure is a candidate until independently qualified and approved. Skills request capabilities; they do not contain their own authority.**

Component invariant: **Rollback of skill content cannot restore previously revoked authority.**

Route worker-visible filesystem, process, network, message, and extension actions through the common execution gate. Canonical internal storage and trust operations use narrowly defined service authority from the bootstrap model, not ambient worker privilege. Declare every transitive effect and preserve current revocation, cancellation, and target identity checks. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `SkillRevocationControllerInput`, `SkillRevocationControllerResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| revision_ref | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| supersedes | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| revocation_generation | integer | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| affected_tasks | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| audit_refs | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| prepareOperation | SkillRevocationControllerInput + validated operation context | SkillRevocationControllerResult | Validate exact inputs, dependencies, target identity, authority requirements, and expected effects; persist a stable operation identity. |
| executeOperation | SkillRevocationControllerInput + validated operation context | SkillRevocationControllerResult | Acquire current admission and scoped resources, perform only approved effects, and capture actual results with cancellation support. |
| stopOrReconcile | SkillRevocationControllerInput + validated operation context | SkillRevocationControllerResult | Close new admission, stop owned work, inspect already committed and uncertain effects, and return a recoverable outcome. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [skill-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/skill-manifest.contract.md) | Candidate, qualified, approved, active, deprecated, and revoked states are distinct. Learned content never contains an implicit authority grant. |
| [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. |
| [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | Invocation arguments are normalized before approval and immutable afterward. Every invocation goes through the common execution gate. |
| [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. |
| [authority-revocation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md) | Revocation is durable, generation-ordered, and propagated to descendants and active admission checks. Known revocations survive restoration of older application data. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-06.05.02` to `ceta/agent-skills-and-learning/skill-lifecycle/skill-revocation-controller` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Revoke exact skill revisions or a lineage, prevent new admissions, and signal affected running tasks. Record already committed effects and safe stopping boundaries.
5. Integrate that behavior into this component sequence: Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence.
6. Enforce the component invariant before publishing any accepted output: Rollback of skill content cannot restore previously revoked authority.
7. Implement a durable lifecycle with explicit prepared, admitted, running, stopping, complete, failed, partial, and uncertain outcomes as applicable. Validate all domain preconditions before dispatch, pin input and target digests, acquire resource and ownership leases atomically, and recheck authority at the effect boundary. Persist intent before external effects and reconcile actual resource state before retry. Publish results only after the specified durable boundary and retain a distinct compensation plan for reversible effects.
8. Use stable operation identities, expected versions, single-use consumption where required, and lease fencing. A timeout does not prove an effect failed; never claim exactly-once external behavior without a verified target-side idempotency or reconciliation mechanism.
9. Inspect the durable intent, local commit, worker identity, target version, and external receipt before choosing continuation, compensation, or human decision. Restore data and drafts without silently rerunning actions or reviving expired authority.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-06.05.01 / skill-version-manager](skill-version-manager.file.README.md), [CETA-06.05.03 / skill-audit-recorder](skill-audit-recorder.file.README.md).

Required subsystem construction prerequisites: [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md).

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
| AT-CETA-06.05.02-01 | Required end-to-end behavior | A queued invocation cannot start after its skill revision is revoked. Procedure: Use a fixture containing valid revision_ref and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-06.05.02-02 | Specific prohibited behavior | A cached invocation bypasses the updated revocation generation. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-06.05.02-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-06.05.02-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-06.05.02-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-06.05.02-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-06.05.02-07 | Duplicate and concurrent use | Duplicate delivery and concurrent requests do not corrupt canonical state, repeat unapproved effects, or bypass exclusive ownership. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-06.05.02-08 | Recovery and reconstruction | Restart preserves committed state, drafts, known revocations, and unresolved effects; recovery does not blindly replay prior actions. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-06.05.02-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-06.05.02-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
