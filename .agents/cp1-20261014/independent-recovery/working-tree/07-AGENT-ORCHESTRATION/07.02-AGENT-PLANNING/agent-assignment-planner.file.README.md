# CETA-07.02.02 - Agent Assignment Planner

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-07.02.02 |
| Subsystem | [07-AGENT-ORCHESTRATION](../README.md) |
| Component | [07.02 Agent Planning](README.md) |
| Planned source basename | agent-assignment-planner |
| Logical source path | ceta/agent-orchestration/agent-planning/agent-assignment-planner |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Planning, extraction, and transformation |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Assign builders, reviewers, and integrators with explicit file ownership and resource budgets. Balance concurrency against conflicts and preserve independent review.

The required observable success is: **Concurrent agents receive nonoverlapping source ownership and named reviewers.** The specifically prohibited behavior is: **Two agents edit the same canonical contract without a shared change decision.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification.

Subsystem invariant: **Agent consensus cannot create authority or factual proof. Builders and final verifiers have distinct assignments and evidence obligations.**

Component invariant: **Parallelization requires disjoint writes or explicit serialized ownership.**

Planning and transformation produce proposals or derived artifacts; they do not grant authority or execute proposed external actions. Persist outputs through the designated state or artifact service with clear lineage. Never silently rewrite the original evidence or user requirement. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `AgentAssignmentPlannerInput`, `AgentAssignmentPlannerResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| plan_id | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| task_nodes | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| dependency_edges | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| write_sets | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| acceptance_refs | list | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| prepare | AgentAssignmentPlannerInput + validated operation context | AgentAssignmentPlannerResult | Validate sources, task requirements, access scope, and transformation configuration before work begins. |
| transform | AgentAssignmentPlannerInput + validated operation context | AgentAssignmentPlannerResult | Produce the specified derived artifact or plan with exact source membership and documented transformation decisions. |
| validateResult | AgentAssignmentPlannerInput + validated operation context | AgentAssignmentPlannerResult | Check output structure, semantic obligations, attribution, and unresolved assumptions before publication. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [agent-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-manifest.contract.md) | Reusable role and runtime agent identity are distinct. A role declaration cannot grant capabilities or establish independent review. |
| [agent-message](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-message.contract.md) | Messages are authenticated task-scoped claims. Delivery is deduplicated and does not create authority or establish factual truth. |
| [agent-handoff](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/agent-handoff.contract.md) | The receiver validates exact artifacts, remaining work, authority, and uncertainty before accepting ownership. Handoff does not revive expired authority. |
| [task-definition](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/task-definition.contract.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. |
| [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. |
| [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-07.02.02` to `ceta/agent-orchestration/agent-planning/agent-assignment-planner` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Assign builders, reviewers, and integrators with explicit file ownership and resource budgets. Balance concurrency against conflicts and preserve independent review.
5. Integrate that behavior into this component sequence: Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution.
6. Enforce the component invariant before publishing any accepted output: Parallelization requires disjoint writes or explicit serialized ownership.
7. Preserve canonical source bytes and normalize only a derived representation. Decompose the domain-specific operation into bounded stages, retain source-to-output mappings, and document tie-breaking, units, ordering, and unknown-value treatment. Use deterministic algorithms where required by the contract; for model-assisted work preserve method, configuration, observed output, and uncertainty. Validate the result against independent source obligations, including contrary evidence and omitted material, before it can guide an effectful action.
8. Pin inputs and configuration for each run. A source update invalidates affected derived outputs. Concurrent transformations must not overwrite each other under one artifact identity.
9. Resume only from a checkpoint that retains exact input versions and completed transformation stages. A repeated model assessment is a new observed result, not a deterministic replay of the previous answer.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-07.02.01 / agent-task-decomposer](agent-task-decomposer.file.README.md), [CETA-07.02.03 / agent-dependency-planner](agent-dependency-planner.file.README.md).

Required subsystem construction prerequisites: [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md).

Use canonical interfaces to break runtime dependency cycles. Register the resulting implementation through the actual local application's composition mechanism. Exercise at least one real producer-consumer path after unit tests; a mock-only result does not qualify integration.

## 9. State, concurrency, and cancellation

Pin inputs and configuration for each run. A source update invalidates affected derived outputs. Concurrent transformations must not overwrite each other under one artifact identity.

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


Resume only from a checkpoint that retains exact input versions and completed transformation stages. A repeated model assessment is a new observed result, not a deterministic replay of the previous answer. Reversing local state does not undo an external message, transfer, or independently committed operation. Compensation must be separately authorized and verified against current target state.

## 11. Security, privacy, and evidence

Treat external content, model output, filenames, tool payloads, and imported manifests as untrusted until their specific schema and scope checks pass. Never promote such content into constitutional rules or owner authority. Preserve exact-source attribution and minimize secret exposure. Record input and output digests, source revision, relevant policy and authority generations, actual observations, and result classification through the canonical evidence service. A digest establishes byte binding; it does not establish truth or complete effect coverage.

## 12. Required tests and observable acceptance

Every row is a construction obligation. Initial execution state for this package is **NOT EXECUTED**; replace it only with a real source-bound result during implementation.

| Acceptance ID | Case | Expected observation and procedure |
| --- | --- | --- |
| AT-CETA-07.02.02-01 | Required end-to-end behavior | Concurrent agents receive nonoverlapping source ownership and named reviewers. Procedure: Use a fixture containing valid plan_id and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-07.02.02-02 | Specific prohibited behavior | Two agents edit the same canonical contract without a shared change decision. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-07.02.02-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-07.02.02-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-07.02.02-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-07.02.02-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-07.02.02-07 | Duplicate and concurrent use | Repeated evaluation of the same pinned input does not mutate the source or mix generations; model-assisted assessments remain separately attributed. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-07.02.02-08 | Recovery and reconstruction | Reconstruction from pinned source and configuration preserves required lineage; a fresh nondeterministic run is labeled separately. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-07.02.02-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-07.02.02-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R07 Agent Orchestration Engineer](../../AGENT-ROLES/R07-AGENT-ORCHESTRATION-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md), [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
