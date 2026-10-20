# 07-AGENT-ORCHESTRATION - architecture

## Responsibility

Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification.

## Required invariant

Agent consensus cannot create authority or factual proof. Builders and final verifiers have distinct assignments and evidence obligations.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [07.01 Agent Registry](07.01-AGENT-REGISTRY/README.md) | agent_id:text; role_id:text; model_binding:reference; capability_refs:list; qualification_state:enum | Register agents and roles; bind authenticated execution identities; match qualified capabilities; expose availability without granting new permissions. |
| [07.02 Agent Planning](07.02-AGENT-PLANNING/README.md) | plan_id:text; task_nodes:list; dependency_edges:list; write_sets:list; acceptance_refs:list | Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution. |
| [07.03 Agent Communication](07.03-AGENT-COMMUNICATION/README.md) | message_id:text; sender:text; recipient:text; task_ref:reference; sequence:integer; artifact_refs:list | Authenticate agent messages; validate task scope and sequence; deliver idempotently; acknowledge handoffs; reconcile missing or duplicate messages. |
| [07.04 Multiagent Execution](07.04-MULTIAGENT-EXECUTION/README.md) | assignment_id:text; lease_generation:integer; worker_state:enum; shared_resource:text; conflict_record:reference | Admit ready assignments; acquire scoped write leases; execute governed work; observe cancellation; resolve conflicts through recorded decisions; release leases. |
| [07.05 Agent Observability](07.05-AGENT-OBSERVABILITY/README.md) | progress_id:text; task_ref:reference; claimed_state:enum; observed_state:enum; evidence_refs:list | Collect authoritative lifecycle events; link agent claims to observed artifacts; evaluate outcomes; expose discrepancies and pending verification. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
