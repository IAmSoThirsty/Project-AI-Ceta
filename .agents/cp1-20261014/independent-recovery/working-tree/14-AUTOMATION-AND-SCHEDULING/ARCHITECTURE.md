# 14-AUTOMATION-AND-SCHEDULING - architecture

## Responsibility

Create durable time- and event-triggered tasks with explicit authority renewal, concurrency, missed-trigger handling, and observable outcomes.

## Required invariant

A schedule grants no more authority than its approved scope and lifetime. Missed triggers are reconciled according to an explicit policy, not blindly replayed.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [14.01 Schedule Definitions](14.01-SCHEDULE-DEFINITIONS/README.md) | schedule_id:text; trigger:record; timezone:text; authority_ref:reference; missed_run_policy:enum; revision:integer | Define trigger and task binding; validate time and effect semantics; approve authority scope; register a durable schedule revision; expose next planned occurrences. |
| [14.02 Time Triggers](14.02-TIME-TRIGGERS/README.md) | occurrence_id:text; scheduled_instant:timestamp; local_time:record; clock_generation:integer; due_state:enum | Compute occurrences using declared calendar semantics; handle clock changes; acquire a durable occurrence claim; dispatch once per occurrence identity. |
| [14.03 Event Triggers](14.03-EVENT-TRIGGERS/README.md) | event_id:text; event_source:reference; resource_revision:text; condition_revision:text; deduplication_key:text | Observe scoped events; authenticate source; normalize and deduplicate; evaluate conditions; create a stable occurrence linked to the source event. |
| [14.04 Automation Dispatch](14.04-AUTOMATION-DISPATCH/README.md) | occurrence_ref:reference; task_ref:reference; authority_generation:integer; concurrency_key:text; admission_ref:reference | Claim an occurrence; validate schedule revision and current authority; acquire concurrency and resources; submit a durable task; record admission or blocking reason. |
| [14.05 Automation Continuity](14.05-AUTOMATION-CONTINUITY/README.md) | reconciliation_id:text; missed_occurrences:list; selected_policy:enum; outcome_refs:list; schedule_generation:integer | Reconcile downtime and event gaps; apply approved catch-up rules; renew authority where needed; recover task links; record actual outcomes and remaining uncertainty. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
