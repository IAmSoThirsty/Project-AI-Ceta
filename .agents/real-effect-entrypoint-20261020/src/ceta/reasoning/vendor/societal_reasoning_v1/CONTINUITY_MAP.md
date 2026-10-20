# CONTINUITY_MAP — Societal Reasoning Core

## Canonical identity and invariant

**Version 1**, owner-set. Do not increment the version for intermediate development work. One standalone, offline-first, advisory engine; one canonical runtime inventory path: `src/societal_reasoning/resources/concepts.full.jsonl`. ZIP delivery: `Societal-Reasoning-Core-v1.zip`.

The later host integration target is CETA/Project-AI **only after** current host-scope completion and separate authorization. No host code or governance/execution authority is included here.

## Lineage and preserved previous work

- Earlier historical artifacts `Societal-Reasoning-Core-v0.1.0.zip` and `Societal-Reasoning-Core-v0.2.0.zip` remain outside this package; neither was overwritten.
- Existing 45 hypothesis relationships, 5 context rules, 10 Merriam-Webster-linked terms, and 18 behavior regression cases remain in Version 1.
- Earlier 134 starter descriptions and 16 excerpt transcriptions remain in repository resources **as legacy snapshots**, not competing authoritative runtime stores.
- Historical starter label for ID 1909 was erroneous ("Change-control procedures"); original full source assigns ID 1908 to change-control procedures and ID 1909 to **Release authorization**. The full inventory is canonical; tests preserve notice of correction.

## Current Version 1 implementation

- Source inventory: IDs 1-1000 and 1001-2000 preserved in full working Markdown files, 2,000/2,000 compiled in canonical JSONL, 0 missing and 0 independently fact-verified.
- Compilation: `scripts/compile_inventory.py` verifies two source volumes, exact stable IDs, all source metadata, and JSONL equivalence; `--write` deliberately recompiles. Required by the release builder.
- Runtime: caller-structured evidence/context -> rules -> lexical ambiguity check -> explicitly bounded interpretation, contest, or clarification. Read-only advisory, no tool execution.
- Source status: manual transcription from conversation; punctuation normalized in some entries. No independent export comparison or source-text fidelity certification. Hashes verify saved sources and derived resources only.
- Tests: canonical source-integrity, missing/duplicate/renumbered entries, graph relations, behavior contract and semantic boundaries.
- Dictionary: Merriam-Webster linked original glosses; no licensed dictionary corpus reproduced or silently fabricated.
- Reference standards: user work ethic and available Volume XXI design draft (unratified), without claiming full Codex ratification or compliance.

## Governance and operational boundaries

- No inferred user emotions, motives, preferences, requests, or consent.
- No proof/no claim; distinguish local transcription from factual verification.
- Preserve original source text and IDs; never silently reindex, replace, or fill missing records.
- Ambiguous material terms require clarification rather than unauthorized sense selection.
- Persist current behavior contracts and source checks across changes.
- External host integration remains deferred. No license, GitHub publication, credentials, cloud services, or other external effects introduced.

## Recovery and continued improvement

1. Inspect `verification-report.json` and `manifest.json` before relying on release claims.
2. Restore from the retained previous ZIPs if necessary; do not overwrite them.
3. To regenerate the same Version 1 ZIP, verify using `python scripts/compile_inventory.py`, then `python scripts/build_release.py <destination>`.
4. Preserve the fixed user-assigned version label unless explicitly authorized to change it.
5. Future work: independent original-conversation textual reconciliation, independently validated edges/evaluations, real-world field tests, and the owner-authorized eventual public repository.

## Version 1 — current human context / attribution development increment

- Owner-set mission: help AI adapt in complicated human circumstances without making claims on anyone's behalf, expanding explicit words, inventing presumptions, or reducing people to labels; consider possible effects on people.
- `docs/IMPLEMENTATION_PLAN.md` preserves the proposed 120-requirement engineering plan; `docs/TRACEABILITY.json` records **six bounded verified conditions, 48 partial, five externally blocked, and 61 not implemented or not verified** at this increment. These are progress labels, not overall completeness.
- New input boundary `input_boundary.py` preserves exact source text, session-scoped speaker IDs and SHA-256-verified spans; `claims.py` captures tentative surface markers and objective candidates without claiming actual NLP semantics.
- `semantics.py` now locates existing Merriam-Webster-linked words in prose and conditionally resolves two restricted context constructions; the ten-term registry is *not* full dictionary coverage.
- `context.py` preserves provenance-tagged reported context, flags incompatible reports and records relevant changes; model hypotheses do not become observed context.
- `response_review.py` checks selected unsupported person claims, exact misquotation, tentative commitment/negation changes, and first-person ghostwriting; it is **not** a full semantic entailment system. `effects.py` represents only possible effects prompted by detected issues.
- Public API added on the same `SocietalReasoner` facade: `assess_text` and `review_draft`; CLI `assess`/`review-draft`; all existing APIs and 2,000 records remain valid.
- **Current boundary:** deterministic advisory safeguards, not general context-aware free-text social reasoning. No temporal correction pipeline, model adapter, independent human evaluation, authenticated inventory source export, or enforceable host gate yet.
- Preserve the original `/mnt/data/Societal-Reasoning-Core-v1.zip` as rollback; new Version 1 ZIP stored in a separate delivery directory without overwriting the prior archive. The fixed release designation remains `1`.

## Version 1 — current retrieval and correction increment

- Core objective unchanged: contextual respect for human complexity; do not fabricate what someone said, intended, believed, or experienced. Knowledge concepts remain possibilities to consider, **not** labels assigned to people.
- New `relevance.py` searches all 2,000 canonical concepts for source-attributed, lexical relevance. `engine.assess_text` and `engine.analyze` expose `knowledge_considerations` containing source IDs, hashes, match tokens and unverified nearby edges; these are never interpretation premises. Model hypotheses and conflicting context categories are excluded.
- New opt-in `corrections.py`: in-memory per-session original/explicit-replacement linkage, same-speaker authorization, source-span verification, chain receipts, and purge. The optional draft reviewer catches only old exact user quotes incorrectly presented as current; not full correction-aware semantic reasoning.
- Existing classifier outputs, explicit clarification gate, 2,000-entry corpus, 45 hypothesis edges, 5 old rules and 18 behavior contracts remain unchanged. Prior saved Version 1 archives remain unchanged and available as rollback candidates.
- Tests and docs: `tests/test_relevance.py`, `tests/test_corrections.py`, `docs/RELEVANCE_AND_CORRECTIONS.md`; test count in `verification-report.json` after release packaging. Source authenticity and independent reasoning accuracy remain unresolved; no final 120-requirement completion is claimed.

## Latest continuation — Version 1 attributed-alternative evaluation

- New code: `src/societal_reasoning/deliberation.py` with the existing `SocietalReasoner` facade and offline CLI (`deliberate`, `compare-deliberations`); no second model, no alternate execution authority.
- Inputs: `DeliberationCase` includes a structured `Scenario`, proposed candidate readings and source-attributed pro/con warrants, optional conditions and context reports. Supplied warrant roles/reasons are unverified assertions.
- The engine checks which declared context conditions are supported by non-model reports, defers on missing/conflicting context, excludes evidence whose origin is solely `interpretation`, preserves both sides and source hashes; changing a contextual condition can change the set of active warrants.
- No automatic natural-language cue detection, semantic verification of warrants, invented personality judgments or causal truth claims. Existing 2,000 source records, 45 unreviewed edges, five original rules, attribution boundary and explicit correction ledger are preserved.
- Examples: `examples/deliberation_public.json`, `examples/deliberation_private.json`. Tests: `tests/test_deliberation.py`. Methods documented in `docs/ALTERNATIVE_READINGS.md`.
- All packaging and requirements progress remain **Version 1** with auditable release files; previous snapshots stay available for rollback. No GitHub publication and no autonomous external operations.

## Latest continuation — Version 1 bounded premise/source disagreement checks

- Canonical source and version remain unchanged. Added `semantic_support.py`, optional digest-bound `WarrantPremise`, `check_premise`, and a deliberately narrow unquoted declarative grammar. Existing APIs and no-premise warrants still work with their prior **unverified** status.
- Each checked premise either verifies exact source-word presence, records a literal source assertion, or is excluded/deferred for disagreement, stale digest, quote attribution, context, actor, action or modality mismatch. Proof of source wording is NOT proof of social inference, independent source authenticity, or real-world truth.
- New cross-report opposition detector surfaces two supplied records whose literal claims have opposite polarity. It does not adjudicate the underlying event, actor identity, speaker motives or trustworthiness.
- Sources: `docs/BOUNDED_PREMISE_VALIDATION.md`, `examples/bounded_semantic_premises.json`, `schemas/premise.schema.json`. Tests: `tests/test_semantic_support.py`. All release checks must run from extracted ZIP; previous Version 1 ZIPs remain available for rollback.
- Next: infer whether source *meaning* supports a social interpretation, acquire context with source anchors, evaluate against independent real-world scenarios. The 2,000 records and proposed 120 requirements do NOT become complete by passing these bounded tests.

## Latest continuation - Version 1 bounded source-to-reading alignment

- Scope and release designation unchanged. Existing corpus, schemas, APIs and earlier deterministic deliberation behavior preserved. New `reading_support.py` introduces independent **reading-source** checks, not just warrant-premise checks; all claims remain about supplied text, never independently validated facts or people's traits.
- Restricted literal source-report alignment can detect directly opposing *readings* and prevent a proposed warrant alone from driving single-conclusion response guidance. High-precision third-party private-state claims are also withheld as lone conclusions, while all evidence remains preserved. Absence of a matching literal statement is not treated as proof of a broader social reading's falsity.
- Two explicit textual surface forms can be recognized: universal-quantified group statements and work-product evaluations. Both can appear in one case, without exclusive social classification, implicit emotional inference or invented source credibility. The checks do not adjudicate ridicule vs critique.
- New tests: `tests/test_reading_support.py`; new fixtures: `examples/reading_source_alignment.json` and `examples/literal_reading_opposed.json`; design limits in `docs/BOUNDED_READING_ALIGNMENT.md`.
- Still missing: open-world reasoning whether cited social evidence semantically warrants a hypothesis; independently verified sources and human field evaluation. Preserve prior builds for rollback.
