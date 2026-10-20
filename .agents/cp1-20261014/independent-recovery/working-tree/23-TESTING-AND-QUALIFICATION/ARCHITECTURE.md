# 23-TESTING-AND-QUALIFICATION - architecture

## Responsibility

Define and execute layered tests, adversarial checks, recovery probes, usability checks, and evidence-bound product qualification.

## Required invariant

Design completeness, test existence, test execution, and passed acceptance are separate states. Critical skipped or not-executed tests cannot satisfy release gates.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [23.01 Test Architecture](23.01-TEST-ARCHITECTURE/README.md) | test_id:text; requirement_ref:reference; fixture_revision:text; oracle:record; execution_state:enum | Register requirements and test oracles; build controlled fixtures; execute on pinned source and environment; normalize results without erasing failures or omissions. |
| [23.02 Contract Testing](23.02-CONTRACT-TESTING/README.md) | contract_ref:reference; producer_revision:text; consumer_revision:text; fixture_ref:reference; conformance_result:enum | Exercise canonical schemas and semantics on producers and consumers; test valid, invalid, stale, and adversarial inputs; bind results to exact contract revisions. |
| [23.03 Integration Testing](23.03-INTEGRATION-TESTING/README.md) | scenario_id:text; subsystem_set:list; source_manifest:reference; observation_plan:record; acceptance_ref:reference | Execute complete workflows across real subsystem boundaries; observe effects independently; interrupt at defined points; validate state, authority, and evidence continuity. |
| [23.04 Adversarial And Failure Tests](23.04-ADVERSARIAL-AND-FAILURE-TESTS/README.md) | attack_case:text; authorized_scope:record; injection_point:text; observed_boundary:record; containment_ref:reference | Construct bounded adversarial inputs and faults in isolated fixtures; attempt declared boundary violations; observe enforcement; preserve reproducible failures and recovery evidence. |
| [23.05 Product Qualification](23.05-PRODUCT-QUALIFICATION/README.md) | gate_id:text; required_tests:list; evidence_manifest:reference; unresolved_findings:list; qualification_state:enum | Collect current results; validate source and environment binding; evaluate mandatory gates; preserve existing local acceptance obligations; approve release only with complete evidence. |
| [23.06 User Experience Testing](23.06-USER-EXPERIENCE-TESTING/README.md) | flow_id:text; interaction_steps:list; accessibility_mode:record; viewport:record; performance_envelope:reference | Test real owner workflows through the native interface; inspect focus and assistive behavior; measure performance under representative load; verify state and evidence outcomes. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
