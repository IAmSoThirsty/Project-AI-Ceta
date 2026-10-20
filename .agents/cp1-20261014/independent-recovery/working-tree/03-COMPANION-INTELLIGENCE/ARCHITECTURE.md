# 03-COMPANION-INTELLIGENCE - architecture

## Responsibility

Provide a continuous human-facing intelligence that deliberates, remembers, proposes work, and reports governed outcomes.

## Required invariant

Continuity, preference, confidence, and personality cannot confer execution authority. Human decisions remain attributable and task consent remains scoped.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [03.01 Companion Identity](03.01-COMPANION-IDENTITY/README.md) | companion_id:text; profile_revision:text; owner_scope:reference; preferred_interaction:record; capability_view:record | Create a persistent companion profile; bind it to approved identity and preferences; evolve it through recorded changes; expose only currently available capabilities. |
| [03.02 Dialogue Intelligence](03.02-DIALOGUE-INTELLIGENCE/README.md) | conversation_id:text; turn_id:text; intent_record:record; unresolved_question:list; response_basis:references | Accept a turn; preserve exact user wording; identify consequential ambiguity; assemble authorized context; generate a response plan; expose factual basis and proposed actions. |
| [03.03 Continuity And Adaptation](03.03-CONTINUITY-AND-ADAPTATION/README.md) | continuity_id:text; checkpoint_ref:reference; preference_source:reference; adaptation_version:integer | Load continuity records; apply explicit preferences; propose uncertain adaptations; reconcile interrupted sessions; restore task and dialogue references. |
| [03.04 Initiative And Deliberation](03.04-INITIATIVE-AND-DELIBERATION/README.md) | initiative_id:text; rationale_refs:list; proposed_effects:list; decision_state:enum; authority_ref:reference | Identify a useful initiative; state rationale and alternatives; assess authority; ask for decisions where required; create a governed task only after valid approval. |
| [03.05 Companion Operations](03.05-COMPANION-OPERATIONS/README.md) | task_ref:reference; action_proposal:reference; progress_event:record; observed_result:reference | Translate approved plans into tasks; request tools through orchestration; observe progress; present results and interruptions with evidence links. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
