# Architecture — Version 1

## Deliberately narrow vertical slice

This release demonstrates the full path from caller-declared factual context and supporting evidence to an auditable provisional interpretation. It is *not* a general-purpose autonomous reasoning agent or free-form social understanding model.

```text
Scenario JSON
    |
    v
Scenario/Evidence strict parser and provenance labels
    |
    v
Evidence cues (excluding items explicitly tagged interpretation)
    |
    v
Declarative rule prerequisites + positive/negative evidence + user-supplied context
    |
    v
Ranked candidates (support scores, not probabilities)
    |
    +--> competing frames / insufficient evidence --> clarification needed
    |
    v
Provisional interpretation + counter-evidence + unknowns + explicit trace
    |
    v
Read-only advisory result (no execution permission)
```

`KnowledgeGraph` exposes stable numeric concept IDs, indexed concepts, explicit typed edges, searchable summaries, and relation traversal. All concept and relationship metadata carries provenance. The engine requires that referenced concepts exist and rejects ambiguous duplicate IDs.

## Separation of responsibilities

- `models.py`: validates contracts for concepts, links, claims, and scenario evidence.
- `graph.py`: offline graph loading, validation, search, traversal, coverage audit.
- `ingest.py`: source-preserving parser for each full numbered 1,000-entry Markdown volume.
- `scripts/compile_inventory.py`: complete-source verification and deterministic canonical JSONL compilation.
- `merge.py`: fail-closed merge and status conflict checks; canonical compilation only combines the two nonoverlapping full source volumes.
- `engine.py`: rule evaluation and epistemic accounting.
- `cli.py`: explicit local IO and command routing.
- `resources/*.jsonl`, `rules.v1.json`: transparent knowledge and rules that can be reviewed without reading engine code.

## Reasoning evidence contract

Statements arrive labeled as direct observations, quotations, external records, user reports, or interpretations. Direct observations remain observations *reported by the caller*; they do not become independently verified by passing through software. User reports remain user reports. Prior interpretations are retained for reference but their cues are excluded from rule support.

A rule must meet all declared required cues before it is considered. Supporting and contrary cues determine ranking. Certain context attributes contribute only when supplied by the caller and are explicitly labeled as such. When strong contradictory frames coexist, the engine declines to force a single answer.

Private intention is never inferred as fact. Interpretations use terms such as "consistent with" and describe limitations. Scores are non-probabilistic rule support measures.

## Scope of authority

`SocietalReasoner.analyze()` returns JSON-compatible descriptive results. It cannot perform actions or grant permissions. A future CETA/Project-AI adapter, if requested after current scope completion, must remain advisory to the host's single, existing execution and governance chain. No host system is accessed by this repository.

## Failure modes explicitly tested

- A public group-directed mockery case must not be categorized as an engineering defect report merely because developers appear in the meme.
- A concrete test failure with reproducible evidence must not be reduced to a personal insult.
- Friendly teasing cannot be assumed to have hostile intent without contrary evidence.
- A lone ambiguous quote cannot support mind-reading.
- An interpretation containing cue keywords must not become evidence.
- Contradictory critique and ridicule evidence triggers a contested interpretation rather than false certainty.
- Text masquerading as an instruction inside evidence never changes program control.
- Dangling relationships, missing source provenance, conflicting import records, and duplicate IDs are rejected.

## Dictionary ambiguity gate and full source preservation

Caller supplies `material_terms` with optional explicit dictionary `sense_id`. The `LexicalRegistry` checks locally reviewed Merriam-Webster references. If a material term admits multiple reviewed senses without the caller selecting one, the final result is `clarification_required`, `primary=null`; no candidate is presented as a selected interpretation. This gate does not infer meaning from scenario prose.

The one canonical runtime graph now loads all 2,000 source-transcribed entries from `concepts.full.jsonl`, with full-volume and per-entry SHA-256 digests. Both original working Markdown volumes are retained, and `scripts/compile_inventory.py` verifies the derived files field-for-field. Legacy seed and excerpt files are preserved for history but do not participate in runtime loading. The 45 proposed edges are unchanged and remain curator hypotheses.

`evaluate.py` is a deterministic, developer-authored behavior-contract checker. It explicitly does not calculate empirical generalization accuracy. The release script refuses to package a failing contract or unit test. `verification-report.json` records bounded evidence and open gaps.

## Version 1 incremental context retrieval and corrections

`relevance.py` is the bounded, source-scoped lexical retrieval layer. It retrieves potential *topics* and nearby hypothesis edges from the canonical corpus for `assess_text()` and `analyze()` without silently promoting them into interpretation premises. User reports remain unverified; model hypotheses and incompatible reports cannot seed retrieval.

`corrections.py` provides opt-in in-memory session-specific supersession events. It requires an explicit corrected source span, the original speaker, and a recorded later turn. `engine.review_draft()` can consume that ledger to hold stale exact current-attribution quotes. It does not automatically revise the five-rule classifier or prove complex meaning. See `RELEVANCE_AND_CORRECTIONS.md` for contracts and limits.
