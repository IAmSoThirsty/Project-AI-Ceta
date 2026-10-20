# 16-KNOWLEDGE-AND-RESEARCH - architecture

## Responsibility

Ingest and retrieve authorized sources, extract knowledge, compare evidence, and produce attributable research outputs.

## Required invariant

Source integrity, source credibility, claim support, and claim truth are different assessments. Contrary evidence and unknowns remain visible.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [16.01 Source Ingestion](16.01-SOURCE-INGESTION/README.md) | source_id:text; source_kind:enum; original_digest:digest; acquired_at:timestamp; published_at:optional-timestamp; access_scope:reference | Acquire authorized source bytes; preserve originals; classify format and trust; extract through bounded parsers; record dates and transformations; index after commit. |
| [16.02 Knowledge Extraction](16.02-KNOWLEDGE-EXTRACTION/README.md) | extraction_id:text; source_span:range; entity_id:text; relation_type:enum; confidence:bounded-number; method_revision:text | Parse structure; extract attributed entities and relationships; normalize identifiers without losing originals; validate against source spans; retain uncertainty and conflicts. |
| [16.03 Knowledge Indexing](16.03-KNOWLEDGE-INDEXING/README.md) | index_id:text; source_revision:reference; chunk_boundaries:record; relation_refs:list; access_filter:record | Index committed authorized source versions; preserve citation boundaries; apply access controls; retrieve lexical, semantic, and graph candidates; rebuild reproducibly. |
| [16.04 Research Reasoning](16.04-RESEARCH-REASONING/README.md) | claim_id:text; supporting_sources:list; contradicting_sources:list; independence_groups:list; assessment:enum | Decompose research questions; compare sources and chronology; assess independence and support; seek disconfirming evidence; state supported findings and unresolved gaps. |
| [16.05 Research Output](16.05-RESEARCH-OUTPUT/README.md) | report_id:text; claim_refs:list; citation_refs:list; source_cutoff:timestamp; unresolved_items:list | Build source-linked findings; validate every citation; separate observation and interpretation; preserve research state; export an inspectable report with exact evidence references. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
