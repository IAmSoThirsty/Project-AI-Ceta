# 11-EXECUTION-AND-ISOLATION - architecture

## Responsibility

Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes.

## Required invariant

Authorization is bound to exact inputs and target identity and rechecked at the effect boundary. Isolation is qualified on the actual operating environment.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [11.01 Execution Gate](11.01-EXECUTION-GATE/README.md) | operation_id:text; proposal_digest:digest; capability_ref:reference; target_identity:record; admission_generation:integer | Validate immutable operation inputs; verify current authority; reserve resources and evidence capacity; atomically record admission; dispatch through qualified isolation. |
| [11.02 Execution Sandbox](11.02-EXECUTION-SANDBOX/README.md) | isolation_id:text; worker_identity:reference; filesystem_scope:record; network_scope:record; process_limits:record | Construct a least-authority worker environment; verify actual restrictions; launch the bound worker; observe effects; terminate and verify cleanup. |
| [11.03 Effect Control](11.03-EFFECT-CONTROL/README.md) | effect_id:text; expected_target:record; expected_change:record; before_digest:digest; observed_change:record | Declare intended effects; bind target and preconditions; observe actual operations independently; compare expected and actual effects; contain deviations. |
| [11.04 Stop And Cancellation](11.04-STOP-AND-CANCELLATION/README.md) | stop_id:text; target_scope:record; stop_generation:integer; deadline:duration; observed_stop_state:enum | Accept an authenticated stop; prevent new admissions; signal workers; escalate termination by policy; observe residual effects; persist the final cancellation outcome. |
| [11.05 Execution Transactions](11.05-EXECUTION-TRANSACTIONS/README.md) | transaction_id:text; intent_ref:reference; local_commit_state:enum; external_effect_state:enum; compensation_ref:reference | Persist intent; stage reversible local changes; perform authorized effects; commit observations; reconcile interrupted transactions; compensate only with explicit scope. |
| [11.06 Octoreflex Boundary](11.06-OCTOREFLEX-BOUNDARY/README.md) | policy_generation:integer; platform_capabilities:record; monitor_identity:reference; observation_sequence:integer; attestation_ref:reference | Reconcile the existing native enforcement boundary; translate approved restrictions; qualify enforcement and observation on the target platform; attest actual installed policy. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
