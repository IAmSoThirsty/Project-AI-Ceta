# CETA-21.05.01 - Extension Template Generator

## 1. Identity, scope, and source placement

| Property | Construction specification |
| --- | --- |
| Logical unit | CETA-21.05.01 |
| Subsystem | [21-EXTENSIONS-AND-INTEROPERABILITY](../README.md) |
| Component | [21.05 Native Extension Kit](README.md) |
| Planned source basename | extension-template-generator |
| Logical source path | ceta/extensions-and-interoperability/native-extension-kit/extension-template-generator |
| Actual local filename and extension | Resolve through local inspection before editing; this package has not inspected the working application. |
| Implementation profile | Planning, extraction, and transformation |
| Design status | Specified. Runtime implementation, test execution, and release qualification are separate construction obligations. |


This document is the build instruction for one planned implementation file. It contains no implementation source. Preserve this logical identity when an existing local file is reused or when the established language requires the unit to be split into smaller files; record all resulting paths and ownership explicitly.

## 2. Exact responsibility and expected outcome

Specify a future native tool that creates extension project scaffolds with manifests, declared effects, lifecycle boundaries, tests, and documentation. Its generated implementation is a later construction task, not part of this documentation pack.

The required observable success is: **A generated extension project declares all required contracts and has no implicit privileges.** The specifically prohibited behavior is: **A convenience template embeds production secrets or bypass permissions.** These two cases are mandatory independent test oracles, not illustrative suggestions.

## 3. Ownership and component boundary

Subsystem purpose: Enable optional native extensions and generic interoperability through versioned contracts, qualification, scoped authority, and isolated lifecycle management.

Subsystem invariant: **Extensions are optional untrusted components until qualified. Installation, discovery, and compatibility do not grant execution authority.**

Component invariant: **Extension development conveniences cannot weaken production admission or verification.**

Planning and transformation produce proposals or derived artifacts; they do not grant authority or execute proposed external actions. Persist outputs through the designated state or artifact service with clear lineage. Never silently rewrite the original evidence or user requirement. Read [bootstrap and service-authority boundaries](../../00-MASTER-ARCHITECTURE/BOOTSTRAP-AND-TRUST-BOUNDARIES.md) before implementing internal writes or startup interactions. Do not introduce a second capability issuer, policy owner, task store, evidence signer, or resource scheduler in this unit.

## 4. Domain records and typed declarations

Define local `ExtensionTemplateGeneratorInput`, `ExtensionTemplateGeneratorResult`, and a stable domain error classification in the reconciled application language. The input combines only the fields required by this unit's responsibility with the following component record model. Shared contract fields are imported from their canonical owner, not redefined with different semantics.

| Component field | Type | Binding obligation |
| --- | --- | --- |
| template_revision | text | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| contract_set | references | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| fixture_set | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |
| documentation_manifest | reference | Resolve exact reference/version and enforce the component invariant; retain original source meaning. |


The result contains the domain output or exact artifact references, outcome state, accepted source and dependency revisions, findings with stable codes, and safe evidence references. Required values are never silently defaulted. Bound strings, lists, buffers, recursion, and work queues using the qualified local profile. Preserve missing, unknown, unavailable, rejected, and not-executed as distinct states. Consult [common type and serialization rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) for reference resolution, timing, content binding, and privacy.

## 5. Public operations to implement

These operation names define responsibilities rather than source syntax. Bind them to the existing application's naming and call conventions during reconciliation and record that binding.

| Operation | Input | Output | Required behavior |
| --- | --- | --- | --- |
| prepare | ExtensionTemplateGeneratorInput + validated operation context | ExtensionTemplateGeneratorResult | Validate sources, task requirements, access scope, and transformation configuration before work begins. |
| transform | ExtensionTemplateGeneratorInput + validated operation context | ExtensionTemplateGeneratorResult | Produce the specified derived artifact or plan with exact source membership and documented transformation decisions. |
| validateResult | ExtensionTemplateGeneratorInput + validated operation context | ExtensionTemplateGeneratorResult | Check output structure, semantic obligations, attribution, and unresolved assumptions before publication. |


Internal helper functions must separate validation, pure domain logic, canonical state access, effect dispatch, and result presentation where those responsibilities apply. Dependency injection or the existing equivalent must let tests provide a controlled clock, state view, resource profile, and observation source without creating production bypasses.

## 6. Canonical interfaces

| Contract | Required use |
| --- | --- |
| [skill-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/skill-manifest.contract.md) | Candidate, qualified, approved, active, deprecated, and revoked states are distinct. Learned content never contains an implicit authority grant. |
| [tool-manifest](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-manifest.contract.md) | The manifest binds exact implementation and effects, including transitive actions. Discovery exposes availability, not permission. |
| [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md) | Invocation arguments are normalized before approval and immutable afterward. Every invocation goes through the common execution gate. |
| [isolation-context](../../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md) | Required restrictions must be qualified and observed active for the actual worker generation. Unsupported restrictions block the affected action. |
| [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md) | Delegated scope, duration, usage, and depth are contained by the parent. Multiple parents do not implicitly union privileges. |
| [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | A result identifies exact subject, environment, method, and verifier. Only admissible current evidence satisfies a mandatory gate; self-check is not independent review. |


Apply [application-error](../../INTERFACE-CONTRACTS/USER-INTERACTION/application-error.contract.md) for cross-boundary failures and [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) for acceptance evidence. A contract reference here is a semantic dependency; it does not authorize the unit to mutate the owning service's records directly.

## 7. End-to-end implementation sequence

1. Read this unit, [its component README](README.md), and the canonical contracts below. Inspect the actual local implementation before selecting reuse, extension, or creation.
2. Bind logical unit `CETA-21.05.01` to `ceta/extensions-and-interoperability/native-extension-kit/extension-template-generator` and then to the observed local language, module, filename, and source digest in the integration mapping. Acquire the assigned write scope; preserve unrelated owner changes.
3. Define the local typed input, result, and error declarations shown below. Keep shared authority and evidence records owned by their canonical services rather than duplicating them here.
4. Implement the file-specific behavior in full: Specify a future native tool that creates extension project scaffolds with manifests, declared effects, lifecycle boundaries, tests, and documentation. Its generated implementation is a later construction task, not part of this documentation pack.
5. Integrate that behavior into this component sequence: Provide native extension construction guidance and contract fixtures; generate only owner-requested templates in the future implementation; qualify extensions against the same runtime rules.
6. Enforce the component invariant before publishing any accepted output: Extension development conveniences cannot weaken production admission or verification.
7. Preserve canonical source bytes and normalize only a derived representation. Decompose the domain-specific operation into bounded stages, retain source-to-output mappings, and document tie-breaking, units, ordering, and unknown-value treatment. Use deterministic algorithms where required by the contract; for model-assisted work preserve method, configuration, observed output, and uncertainty. Validate the result against independent source obligations, including contrary evidence and omitted material, before it can guide an effectful action.
8. Pin inputs and configuration for each run. A source update invalidates affected derived outputs. Concurrent transformations must not overwrite each other under one artifact identity.
9. Resume only from a checkpoint that retains exact input versions and completed transformation stages. A repeated model assessment is a new observed result, not a deterministic replay of the previous answer.
10. Implement the exact acceptance cases below, exercise the real neighboring service path, preserve raw observations, and hand the pinned source and artifacts to the independent verifier. Update integration and documentation records only from observed results.

## 8. Component integration and adjacent files

Provide native extension construction guidance and contract fixtures; generate only owner-requested templates in the future implementation; qualify extensions against the same runtime rules.

Coordinate with these sibling units without assuming directory order is execution order: [CETA-21.05.02 / extension-test-harness](extension-test-harness.file.README.md), [CETA-21.05.03 / extension-documentation-builder](extension-documentation-builder.file.README.md).

Required subsystem construction prerequisites: [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md).

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
| AT-CETA-21.05.01-01 | Required end-to-end behavior | A generated extension project declares all required contracts and has no implicit privileges. Procedure: Use a fixture containing valid template_revision and all required referenced objects. Execute the primary operation and inspect real outputs. |
| AT-CETA-21.05.01-02 | Specific prohibited behavior | A convenience template embeds production secrets or bypass permissions. Procedure: Construct this exact adverse condition. The operation must reject, block, preserve uncertainty, or request the specified decision; it must not produce the prohibited result. |
| AT-CETA-21.05.01-03 | Malformed and incompatible input | Missing required fields, unsupported versions, excessive sizes, and invalid references produce the canonical safe error before privileged or expensive work. Procedure: Vary one input constraint at a time and assert the exact failure category and absence of unauthorized effects. |
| AT-CETA-21.05.01-04 | Stale source or generation | A changed source digest, state version, target identity, policy, or revocation generation invalidates the affected result or admission. Procedure: Change a relevant dependency between preparation and use, then observe conflict or reevaluation rather than silent reuse. |
| AT-CETA-21.05.01-05 | Access and sensitive content | A caller outside the permitted scope cannot read, modify, infer restricted identifiers, or obtain secret values through output, diagnostics, or caches. Procedure: Run equivalent requests with authorized and unauthorized principals; inspect outputs, logs, and derived records. |
| AT-CETA-21.05.01-06 | Bounds and interruption | The operation respects its input, memory, queue, and time limits; interruption yields an explicit partial, blocked, cancelled, or uncertain result as appropriate. Procedure: Cancel at a meaningful internal boundary and inspect cleanup, output status, and preservation of canonical inputs. |
| AT-CETA-21.05.01-07 | Duplicate and concurrent use | Repeated evaluation of the same pinned input does not mutate the source or mix generations; model-assisted assessments remain separately attributed. Procedure: Run duplicates and competing updates under controlled scheduling; inspect state versions, operation identities, and actual effects. |
| AT-CETA-21.05.01-08 | Recovery and reconstruction | Reconstruction from pinned source and configuration preserves required lineage; a fresh nondeterministic run is labeled separately. Procedure: Interrupt after an observed boundary, restore from recorded state, and compare before and after artifacts and authority. |
| AT-CETA-21.05.01-09 | Real integration path | The actual producer and consumer agree on schema, denied, failed, partial, uncertain, and complete semantics using the mapped local implementation. Procedure: Exercise the real neighboring subsystem boundary in an isolated integration environment, not only a mock. |
| AT-CETA-21.05.01-10 | Independent completion proof | A distinct reviewer reproduces required results against the delivered source and artifact digests; every unmet test remains explicitly unmet. Procedure: Provide raw evidence and exact fixtures to the independent verifier and compare its observations with the builder report. |


## 13. Construction agents and required skills

Primary builder: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Independent reviewer: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md). Integration owner: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Test coordinator: [R19 Test And Qualification Engineer](../../AGENT-ROLES/R19-TEST-AND-QUALIFICATION-ENGINEER/README.md).

Required skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).

The builder owns only the mapped source paths assigned in the change set. Shared contract amendments require the schema owner's review. The independent reviewer must inspect the exact delivered revision and cannot serve as the independent verifier for its own implementation. Consult [the construction handoff contract](../../AGENT-ROLES/CROSS-AGENT-HANDOFF-CONTRACT.md) for required evidence and unresolved-work transfer.

## 14. Completion and handoff

Deliver the mapped implementation, typed interfaces, domain and adverse-case tests, real integration evidence, updated local documentation, and exact source/artifact identities. Verify the specific positive and negative behavior in section 2 and every required case in section 12. Record any unavailable environment or unexecuted check honestly; those obligations remain open. A compile, generated file, empty test suite, or completion narrative does not satisfy this unit's acceptance.

The handoff includes requirement IDs, changed paths, before/after source digests, approved contract revisions, test fixtures, actual execution records, observed results, recovery behavior, and independent review findings. This specification is complete as a construction instruction; implementing and qualifying the actual application is the subsequent engineering work it defines.
