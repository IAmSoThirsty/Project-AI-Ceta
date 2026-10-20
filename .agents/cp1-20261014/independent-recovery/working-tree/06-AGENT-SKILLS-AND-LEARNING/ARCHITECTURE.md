# 06-AGENT-SKILLS-AND-LEARNING - architecture

## Responsibility

Define, discover, qualify, invoke, revise, and revoke reusable native agent skills.

## Required invariant

A learned procedure is a candidate until independently qualified and approved. Skills request capabilities; they do not contain their own authority.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [06.01 Skill Definitions](06.01-SKILL-DEFINITIONS/README.md) | skill_id:text; version:text; inputs:record; outputs:record; required_effects:list; qualification_ref:reference | Define a versioned skill contract; declare dependencies and effects; validate its structure; bind approved instructions and qualification evidence. |
| [06.02 Skill Discovery](06.02-SKILL-DISCOVERY/README.md) | query_id:text; skill_candidates:list; scope:reference; compatibility_result:enum; reason_codes:list | Search approved skills; match task intent and declared requirements; filter unavailable or unauthorized choices; return explainable candidates. |
| [06.03 Skill Execution](06.03-SKILL-EXECUTION/README.md) | invocation_id:text; skill_revision:reference; input_digest:digest; authority_ref:reference; result_refs:list | Pin a qualified skill; validate inputs; obtain scoped task admission; execute through governed tools; validate outputs and evidence; finalize explicitly. |
| [06.04 Skill Learning](06.04-SKILL-LEARNING/README.md) | candidate_id:text; source_runs:list; generalized_steps:list; validation_set:reference; approval_state:enum | Extract a candidate from successful work; remove incidental secrets and authority; define applicability; test unseen cases; request approval; publish a new revision. |
| [06.05 Skill Lifecycle](06.05-SKILL-LIFECYCLE/README.md) | revision_ref:reference; supersedes:reference; revocation_generation:integer; affected_tasks:list; audit_refs:list | Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
