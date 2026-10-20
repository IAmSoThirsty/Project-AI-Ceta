# 00-MASTER-ARCHITECTURE - architecture

## Responsibility

Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules.

## Required invariant

One canonical owner exists for every authority decision, state record, interface, and observable effect. Planning names never establish that a component already exists.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [00.01 Product Identity](00.01-PRODUCT-IDENTITY/README.md) | product_id:text; architecture_revision:text; invariant_id:text; owner_decision_ref:reference | Load the approved product baseline; resolve amendments; expose a versioned invariant set; make every change traceable to an owner decision. |
| [00.02 System Topology](00.02-SYSTEM-TOPOLOGY/README.md) | subsystem_id:text; component_id:text; dependency_id:text; edge_kind:enum; owner_role:text | Register components; validate unique ownership; distinguish build, runtime, data, and optional dependency edges; expose navigation and impact analysis. |
| [00.03 Runtime Lifecycle](00.03-RUNTIME-LIFECYCLE/README.md) | boot_id:text; readiness:enum; lifecycle_generation:integer; deadline:duration; last_safe_state:reference | Initialize minimum storage and trust prerequisites; activate policy and dispatch boundaries; advertise readiness; stop admission; drain or terminate work; close durable stores. |
| [00.04 Integration Baseline](00.04-INTEGRATION-BASELINE/README.md) | logical_unit:text; observed_path:text; source_digest:text; reuse_decision:enum; compatibility_evidence:reference | Inspect only the selected local root; capture a read-only baseline; map logical units to observed files; resolve collisions; approve reuse or extension before editing. |
| [00.05 Architecture Assurance](00.05-ARCHITECTURE-ASSURANCE/README.md) | check_id:text; baseline_digest:text; observed_edge:text; expected_owner:text; finding_severity:enum | Evaluate graph structure, invariant coverage, and contract ownership against the same baseline; produce findings before integration approval. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.

## Native CETA component bindings

These are logical integration responsibilities, not claims that the current local implementation was inspected. Reconcile each name to its actual local owner before constructing parallel services.

| Native component | Architecture responsibility | Integration rule |
| --- | --- | --- |
| CVM and constitutional governance | Subsystem 01 evaluates approved rules and produces version-bound policy decisions. | Preserve the existing constitutional semantics and source traceability; do not replace them with model preference. |
| TAAR | Subsystems 07 and 08 coordinate bounded agents and durable tasks; subsystem 11 controls actual effects. | Map the existing runner to these responsibilities and keep one canonical dispatch and task lifecycle. |
| Thirsty-Lang | Component 01.04 provides parsing, policy typing, and governed compilation. | Inspect and preserve the approved local grammar and compiler contracts before extending them. |
| State Register | Subsystem 19 owns canonical operational records and durable transitions. | Reuse the existing record owner and migrate explicitly rather than introducing conflicting state stores. |
| OctoReflex | Component 11.06 binds approved restrictions to qualified native enforcement and observation. | Verify the actual target-platform backend and report unsupported controls; do not assume a platform-specific mechanism exists. |
| Companion Intelligence | Subsystem 03 owns human-facing dialogue, continuity, deliberation, and governed task proposals. | Keep companion identity and preferences separate from the owner's authority and execution capabilities. |
| Evidence and immutable frames | Subsystem 17 owns receipts, exact-source binding, append-only frames, lineage, and verification. | Preserve existing evidence semantics and state the actual tamper-evidence, anchoring, and observation limits. |
