# 10-TOOLS-AND-CAPABILITIES - architecture

## Responsibility

Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts.

## Required invariant

Tools declare effects before execution and return observations after execution. Discovery or selection never grants authority.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [10.01 Tool Registry](10.01-TOOL-REGISTRY/README.md) | tool_id:text; version:text; schema_digest:digest; effects:list; implementation_digest:digest; qualification_ref:reference | Register a tool manifest; verify implementation binding and qualification; expose authorized discovery; pin the exact tool revision for each invocation. |
| [10.02 Tool Contracts](10.02-TOOL-CONTRACTS/README.md) | invocation_ref:reference; normalized_arguments:record; declared_effects:list; result_schema:text; validation_status:enum | Validate exact arguments; classify all intended effects; bind normalized input to approval; validate returned observations before consumers use them. |
| [10.03 Local Operations](10.03-LOCAL-OPERATIONS/README.md) | resource_identity:record; selected_root:text; content_digest:digest; process_binding:reference; operation_id:text | Resolve local targets within approved roots; validate stable identities; execute through isolated native adapters; observe actual changes; return exact results. |
| [10.04 Network Operations](10.04-NETWORK-OPERATIONS/README.md) | destination_identity:record; data_scope:reference; redirect_chain:list; request_digest:digest; response_ref:reference | Validate destination and payload scope; acquire explicit network authority; enforce redirects and size limits; record requests and observed outcomes; classify timeout uncertainty. |
| [10.05 Tool Execution Results](10.05-TOOL-EXECUTION-RESULTS/README.md) | dispatch_id:text; gate_decision:reference; raw_result_ref:reference; normalized_result:record; receipt_ref:reference | Validate invocation; obtain gate admission; dispatch once per stable operation identity; normalize observations; bind an evidence receipt; return a typed outcome. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
