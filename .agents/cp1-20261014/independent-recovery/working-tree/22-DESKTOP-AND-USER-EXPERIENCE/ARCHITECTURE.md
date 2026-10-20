# 22-DESKTOP-AND-USER-EXPERIENCE - architecture

## Responsibility

Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance.

## Required invariant

Visual state is derived from authenticated native state. A disabled button is not a security boundary; every command is validated again by the runtime.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [22.01 Application Shell](22.01-APPLICATION-SHELL/README.md) | window_id:text; route_id:text; session_ref:reference; view_generation:integer; persisted_layout:record | Launch a restricted shell; establish authenticated native communication; restore safe layout; activate routes from runtime readiness; preserve owner control during partial failures. |
| [22.02 Command Center](22.02-COMMAND-CENTER/README.md) | dashboard_snapshot:reference; task_counts:record; health_summary:record; last_observed_at:timestamp; pending_decisions:list | Query authoritative runtime summaries; show active work, health, and decisions; mark stale data; provide controlled navigation and stop actions. |
| [22.03 Agent Control](22.03-AGENT-CONTROL/README.md) | agent_ref:reference; assignment_ref:reference; capability_view:record; observed_state:enum; control_request:reference | Inspect agent identity and assignments; display current grants and actions; request bounded controls; confirm native outcomes; expose reviewer and handoff history. |
| [22.04 Governance Interface](22.04-GOVERNANCE-INTERFACE/README.md) | proposal_ref:reference; exact_effects:list; rule_trace:references; approver_binding:reference; decision_state:enum | Present exact proposals and rule traces; authenticate decisions; show delegation and revocation impact; preserve a source-linked decision history. |
| [22.05 Intelligence Interface](22.05-INTELLIGENCE-INTERFACE/README.md) | conversation_ref:reference; memory_query:record; context_snapshot:reference; attribution_view:record | Present conversation and source attribution; inspect authorized memory; inspect exact context selection; propose corrections or deletions through governed controls. |
| [22.06 Evidence Interface](22.06-EVIDENCE-INTERFACE/README.md) | evidence_query:record; timeline_range:record; provenance_selection:reference; verification_profile:text | Query authorized evidence; display causal timelines and lineage; inspect raw and normalized observations; distinguish integrity, functional, and completeness verification. |
| [22.07 User Controls](22.07-USER-CONTROLS/README.md) | settings_revision:integer; preference_scope:reference; accessibility_profile:record; notification_policy:record | Load owner-scoped settings; validate proposed changes; apply through native commands; preserve accessibility and privacy; recover from invalid configuration. |
| [22.08 Owner Onboarding](22.08-OWNER-ONBOARDING/README.md) | setup_id:text; ownership_state:enum; device_profile:reference; selected_data_root:record; qualification_ref:reference | Choose local data boundaries; establish owner identity; configure recovery; inspect hardware; qualify core local workflows; enable normal operation only after required checks. |
| [22.09 Native Maintenance](22.09-NATIVE-MAINTENANCE/README.md) | maintenance_id:text; backup_ref:reference; restore_plan:reference; update_ref:reference; verification_state:enum | Inspect current health and data; prepare backup, restore, repair, or update proposals; show consequences; execute governed maintenance; verify outcomes and recovery points. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
