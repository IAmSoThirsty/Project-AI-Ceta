# Version 1 — Acceptance and evidence boundary

## Required, testable acceptance gates

- [x] Exactly 1,000 unique, contiguous entries from each of the two manually transcribed source volumes.
- [x] Exactly 2,000 unique IDs in the canonical runtime knowledge graph; the highest ID is 2000.
- [x] Full entry text, label, volume, source line and local source/entry SHA-256 retained in each canonical record.
- [x] Generated full JSONL records match *every* saved source entry field-for-field.
- [x] Runtime CLI loads all 2,000 entries; missing IDs and duplicates are rejected in the build and unit tests.
- [x] Per-volume JSONL and unified JSONL deterministic, no missing, blank, or placeholder records.
- [x] Historical 45 graph edges still reference existing IDs and preserve hypothesis status.
- [x] Merriam-Webster-linked 10-term registry, explicit sense handling, and clarification gate preserved.
- [x] Developer-authored contextual regression cases preserved and executed.
- [x] Source compilation verification and all unit tests required before deterministic release generation.
- [x] Version fixed to **1**, ZIP named `Societal-Reasoning-Core-v1.zip`.
- [x] Source ZIP includes SHA-256 manifest and checksum sidecar; independent extracted-copy checks performed before delivery.
- [x] No host/CETA/Project-AI changes, remote publication, or unauthorized license selection.

## Claims not supported / pending

- [ ] Independent text-by-text comparison with authenticated original chat export (punctuation normalized during manual capture).
- [ ] Independent validation of the 2,000 societal claims against sociological, historical, scientific, and legal references.
- [ ] Independently reviewed graph edge legitimacy, 2,000-entry relational coverage, or full semantic reasoning across the corpus.
- [ ] General free-form natural-language analysis, automated semantic labeling, or comprehensive Merriam-Webster coverage.
- [ ] Independent real-world accuracy, fairness, security, or production certification.
- [ ] Full ratified Codex I-XX traceability and owner ratification of draft Volume XXI.
- [ ] Open-source license decision and owner authorization to publish to GitHub.
- [ ] CETA/Project-AI integration; explicitly deferred until the host's current scope is finished.

## Verification commands

```sh
python scripts/compile_inventory.py
PYTHONPATH=src python -m unittest discover -s tests -q
python run.py audit
python run.py concept 1
python run.py concept 2000
python run.py evaluate evaluations/behavior-contract.v1.json
python scripts/build_release.py /mnt/data
```

Test completion and source coverage cannot be represented as proof of generalized reasoning or source factual truth. All release-claim evidence is saved in `verification-report.json`, `manifest.json`, and the test suite.

## Active Version 1 development acceptance (first increment)

- [x] Source capture stores exact words and verified Unicode-preserving spans, with direct-constructor bypass tests.
- [x] Heuristic utterance markers and objective candidates preserve the original source and avoid automatically assigning a task to bare statements.
- [x] Ten registry terms discovered in unstructured prose without treating mere occurrence as material ambiguity.
- [x] Narrow, inspectable context-of-paragraph / context-of-incident sense matches without unnecessary clarification; other material ambiguity remains explicitly unresolved.
- [x] Caller-supplied context tracked with provenance/status; conflicting reports and model hypotheses are not converted to observed fact.
- [x] Draft review reports selected misquotes, unsupported claims, tentative commitment strengthening and first-person drafting additions with an explicit advisory enforcement boundary.
- [x] 120 proposed requirements included with detailed in-progress/not-yet-verified statuses; no full conformance claim.
- [ ] Automatic context-sensitive free-text social interpretation with supported multiple hypotheses and usable knowledge graph traversal.
- [ ] Complete semantic preservation across arbitrary paraphrases and conversations.
- [ ] Independent demonstration of improved human-interaction performance.

A passing local test only establishes bounded code behavior. Public distribution and owner release authorization remain separate.

## Current Version 1 grounded-retrieval and correction increment

- [x] Both existing `assess_text()` and `analyze()` can retrieve source-attributed lexical topic candidates from the canonical 2,000-entry inventory.
- [x] Model hypotheses cannot seed candidate topics. Conflicting reported context fields cannot silently select a side for retrieval.
- [x] Curator relationship edges remain separately tagged as unverified hypotheses and cannot activate a reasoning rule.
- [x] Retrieval is bounded and may return zero topics; no individual is automatically assigned a topic as a trait.
- [x] A local explicit correction record can supersede earlier exact source text with its origin and session preserved, without erasing the original.
- [x] Optional facade draft review can flag exact old user quotes presented as current, after verifying matching source and session identifiers.
- [ ] General pragmatic and cross-cultural inference from raw input and independently validated knowledge graph reasoning.
- [ ] General semantic contradiction and paraphrase review.
- [ ] Automatic correction interpretation, conversation-scale revision, independent evaluation and production qualification.

## Current Version 1 alternative readings and context-comparison increment

- [x] Validate caller-supplied hypothesis records, referenced evidence, source identity and resource limits; reject malformed or dangling records.
- [x] Keep unverified pro/con warrants attributable to exact source reports without asserting their semantic validity or factual truth.
- [x] Exclude `interpretation`-origin premise records; model-proposed context cannot satisfy a condition.
- [x] Defer contextual warrants when required context is missing or unresolved; avoid manufacturing a winner from raw warrant counts.
- [x] Demonstrate that changing the reported setting can change applicable candidate arguments while an irrelevant day-of-week change does not.
- [x] Surface altered evidence, candidate provenance and unknowns when comparing declared scenarios; never call a case comparison observed causation.
- [x] Preserve the canonical 2,000-entry graph, older facade methods and Version 1 designation.
- [ ] Independently validate whether submitted warrant rationales logically support their candidate readings.
- [ ] Generate appropriate alternatives automatically from natural-language interaction without fabricating facts or person attributes.
- [ ] Independently demonstrate improved contextual judgment with unseen cases and qualified reviewers.

Evidence: `tests/test_deliberation.py`, `examples/deliberation_public.json`, `examples/deliberation_private.json`, `docs/ALTERNATIVE_READINGS.md` and the release report. These cases are implementer-authored, not independent performance certification.
