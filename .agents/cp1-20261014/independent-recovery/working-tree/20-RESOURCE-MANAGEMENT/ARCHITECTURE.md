# 20-RESOURCE-MANAGEMENT - architecture

## Responsibility

Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior.

## Required invariant

Resource estimates carry uncertainty and are checked against measurements. Stop, evidence, and recovery retain reserved capacity under pressure.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [20.01 Hardware Discovery](20.01-HARDWARE-DISCOVERY/README.md) | profile_id:text; cpu_capacity:record; memory_bytes:integer; accelerator_capacity:record; storage_bytes:integer; measured_at:timestamp | Inspect actual available hardware and runtime limits; measure usable capacity; monitor changes; publish a versioned capability profile with uncertainty. |
| [20.02 Resource Budgeting](20.02-RESOURCE-BUDGETING/README.md) | budget_id:text; task_ref:reference; compute_limit:record; memory_limit:integer; deadline:timestamp; reservation_generation:integer | Define per-task and shared budgets; reserve atomically; meter actual use; throttle or stop at limits; release reservations after verified cleanup. |
| [20.03 Workload Admission](20.03-WORKLOAD-ADMISSION/README.md) | workload_id:text; required_resources:record; reservation_ref:reference; priority:integer; admission_state:enum | Estimate requirements; validate budgets and environment; reserve capacity; queue or admit fairly; fence expired reservations; release only after cleanup. |
| [20.04 Resource Pressure](20.04-RESOURCE-PRESSURE/README.md) | pressure_event:text; resource_kind:enum; observed_level:integer; response_policy:reference; affected_tasks:list | Detect sustained pressure; prioritize control and evidence; throttle optional work; stop unsafe admissions; recover gradually after measured stability. |
| [20.05 Operational Diagnostics](20.05-OPERATIONAL-DIAGNOSTICS/README.md) | sample_id:text; task_ref:reference; measured_resources:record; environment_revision:text; diagnostic_ref:reference | Collect scoped resource telemetry; identify bottlenecks; compare against qualification envelopes; run offline and failure probes; report measured limits. |
| [20.06 Inference Accounting](20.06-INFERENCE-ACCOUNTING/README.md) | usage_id:text; request_id:text; input_units:integer; output_units:integer; measurement_kind:enum; budget_ref:reference | Meter observed inference usage; distinguish estimates and provider reports; charge parent and child tasks once; enforce budgets; reconcile interrupted streams. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
