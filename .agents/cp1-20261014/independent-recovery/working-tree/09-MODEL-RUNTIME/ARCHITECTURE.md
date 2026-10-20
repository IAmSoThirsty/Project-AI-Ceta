# 09-MODEL-RUNTIME - architecture

## Responsibility

Manage native model artifacts, qualified inference, optional owner-configured endpoints, routing, lifecycle, and controlled customization.

## Required invariant

Model output is untrusted proposed content. Local operation remains complete without a connected endpoint; fallback cannot silently transmit private data.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [09.01 Model Registry](09.01-MODEL-REGISTRY/README.md) | model_id:text; artifact_digest:digest; format_revision:text; capabilities:list; qualification_ref:reference | Register model artifacts and declared capabilities; validate format and content; qualify on the target environment; publish availability separately from configuration. |
| [09.02 Inference Runtime](09.02-INFERENCE-RUNTIME/README.md) | request_id:text; model_revision:reference; context_ref:reference; stream_sequence:integer; cancellation_ref:reference | Admit an inference request; pin model and context; stream ordered output; observe cancellation and usage; seal the response with provenance and outcome status. |
| [09.03 Model Routing](09.03-MODEL-ROUTING/README.md) | task_class:enum; candidate_models:list; data_boundary:enum; quality_threshold:record; routing_decision:reference | Match task requirements; evaluate qualified candidates and resource limits; select a model; request approval for changed data boundaries; record routing and fallback decisions. |
| [09.04 Model Admission](09.04-MODEL-ADMISSION/README.md) | hardware_profile:reference; peak_memory_estimate:integer; reserve:integer; qualification_result:enum; admission_lease:reference | Inspect actual hardware; estimate model and context working sets; reserve headroom; run qualification probes; admit only within tested limits. |
| [09.05 Model Interfaces](09.05-MODEL-INTERFACES/README.md) | adapter_id:text; transport_kind:enum; endpoint_scope:reference; request_schema:text; capability_result:record | Normalize inference contracts; validate transport and data scope; dispatch through the chosen adapter; normalize usage and errors; preserve native evidence. |
| [09.06 Model Evaluation](09.06-MODEL-EVALUATION/README.md) | evaluation_id:text; fixture_revision:text; model_digest:digest; metrics:record; environment_ref:reference | Run versioned representative fixtures; score task outcomes and boundary behavior; compare against declared qualification thresholds; retain full reproducibility metadata. |
| [09.07 Model Lifecycle](09.07-MODEL-LIFECYCLE/README.md) | acquisition_id:text; artifact_manifest:reference; staged_path:text; installed_revision:text; load_generation:integer | Acquire authorized artifact bytes; validate in staging; install atomically; configure; load under resource admission; unload and verify cleanup. |
| [09.08 Model Customization](09.08-MODEL-CUSTOMIZATION/README.md) | training_job_id:text; dataset_manifest:reference; consent_scope:reference; base_model_digest:digest; checkpoint_ref:reference | Approve a customization objective and data scope; validate datasets; admit a bounded training job; checkpoint; evaluate a candidate artifact; activate only after qualification. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
