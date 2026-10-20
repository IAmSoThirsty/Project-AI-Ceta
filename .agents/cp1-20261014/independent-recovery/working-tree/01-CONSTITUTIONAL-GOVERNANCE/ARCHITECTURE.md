# 01-CONSTITUTIONAL-GOVERNANCE - architecture

## Responsibility

Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions.

## Required invariant

Capability, authority, evidence, and preference remain distinct. Policy activation requires a traceable approved transition; untrusted text cannot amend governing rules.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [01.01 Constitutional Sources](01.01-CONSTITUTIONAL-SOURCES/README.md) | constitution_id:text; rule_id:text; rule_digest:digest; source_ref:reference; activation_generation:integer | Ingest authoritative rule sources; validate provenance and structure; stage a revision; obtain approval; activate atomically and retain earlier revisions. |
| [01.02 Policy Engine](01.02-POLICY-ENGINE/README.md) | subject_ref:reference; action_class:enum; resource_scope:record; policy_snapshot:reference; decision:enum | Normalize an action proposal; select applicable rules; evaluate typed predicates; resolve explicit precedence; emit a decision with its supporting rule trace. |
| [01.03 Governance Transitions](01.03-GOVERNANCE-TRANSITIONS/README.md) | proposal_id:text; input_digest:digest; effect_set:list; approval_refs:list; decision_generation:integer | Create a complete transition proposal; bind approvals to its digest; validate quorum and revocation; commit the decision and its evidence atomically. |
| [01.04 Thirsty Lang](01.04-THIRSTY-LANG/README.md) | source_span:range; syntax_node:record; value_type:enum; capability_type:record; compiled_digest:digest | Parse the locally reconciled language grammar; resolve names; type-check policy expressions; compile a bounded representation; retain source maps. |
| [01.05 Policy Assurance](01.05-POLICY-ASSURANCE/README.md) | invariant_id:text; rule_ref:reference; counterexample:record; amendment_ref:reference; coverage_status:enum | Check rule safety and traceability; exercise boundary fixtures; assess amendments; block activation when required evidence is absent. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
