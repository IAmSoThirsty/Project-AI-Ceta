# Societal Reasoning Core

**Version 1.** One offline-first Python reasoning prototype with a **complete, numbered 2,000-entry source inventory** (Volumes I and II). Python 3.11+; no mandatory runtime dependencies. Version 1 is deliberately held fixed by owner instruction: do not increment it merely for a development change.

This is intended as a standalone, eventually public GitHub repository, if and when the owner authorizes publication and selects a license. Any later CETA/Project-AI integration is separate and deferred. The current engine is read-only/advisory and does not execute actions or grant authority.

## What is actually delivered

- **2,000/2,000 source-transcribed concepts**, IDs `1..2000` with no gaps or duplicates: 1,000 per volume. Every record retains its source entry text, original numbered heading, a stable ID, a local source-file SHA-256, an entry SHA-256, a volume identifier and source line.
- The complete human-readable corpus is in `knowledge/volume-01-full.md` and `knowledge/volume-02-full.md`. The canonical runtime source is `src/societal_reasoning/resources/concepts.full.jsonl`. Two derived volume-specific JSONL files provide deterministic round trips.
- **45 proposed, provenance-labeled graph relationships**, not 2,000 independently vetted causal links. These are legacy curator hypotheses.
- Five auditable context rules; 18 developer-authored scenario regression cases. These are *tests of implemented behavior*, not empirical social-reasoning accuracy.
- Ten source-linked Merriam-Webster entries with multiple sense IDs when warranted. Descriptions are original editorial glosses, not copied dictionary definitions. Ambiguous caller-declared material senses require clarification.
- A single standard-library CLI, Python import API, Markdown importer, offline source compiler, provenance checks, and deterministic ZIP release generator.
- Source-attributed concept relevance integrated into `assess_text()` and `analyze()`, with graph links explicitly labeled as unreviewed hypotheses.
- Optional in-memory, session-scoped explicit corrections and stale-quote checks; no automatic persistence.
- **Source-linked multi-reading deliberation:** `deliberate()` and `compare_deliberations()` accept proposed interpretations, references to evidence, counterarguments, and context conditions. They preserve uncertainty and source provenance. Optional digest-bound checks can now validate exact text excerpts or narrowly parseable literal statements, reject opposed polarity, and surface conflicting source reports without deciding anyone's motives. **These are not proof of a proposed social reading or factual truth.** See `docs/ALTERNATIVE_READINGS.md` and `docs/BOUNDED_PREMISE_VALIDATION.md`.
- 2,000-entry release acceptance tests, including omission, duplicate, out-of-range, changed-record detection, and exact compiled-source comparison.

**Evidence boundary:** The Markdown source volumes were manually transcribed from the two inventories authored earlier in this conversation. Punctuation was normalized for ASCII-safe local capture; no externally authenticated original-chat export has been used for line-by-line comparison. The local import is complete; *independent textual fidelity and factual accuracy are not certified*. `source_transcribed` is not `independently_verified`.

## Run directly, offline

```sh
python run.py audit
python run.py concept 2000
python run.py search "context collapse"
python run.py neighbors 576 --depth 2
python run.py define context
python run.py reason examples/friendly_banter.json
python run.py deliberate examples/deliberation_public.json
python run.py deliberate examples/bounded_semantic_premises.json
python run.py compare-deliberations examples/deliberation_public.json examples/deliberation_private.json
python run.py evaluate evaluations/behavior-contract.v1.json
```

No installation required. The CLI also works with `PYTHONPATH=src python -m societal_reasoning` where setting `PYTHONPATH` is supported. The published installable distribution has not yet been validated in this offline environment.

## Check the complete corpus and run tests

```sh
python scripts/compile_inventory.py
PYTHONPATH=src python -m unittest discover -s tests -q
python scripts/build_release.py /mnt/data
```

`compile_inventory.py` without arguments **verifies without modifying files**, requiring all 2,000 records to match the Markdown sources. `--write` intentionally regenerates compiled JSONL from those sources. Both source volumes must have exactly 1,000 sequential IDs, complete records, and traceable hashes; duplicate IDs and missing entries fail the gate. Release-building runs this verifier and the tests before producing `Societal-Reasoning-Core-v1.zip` and its SHA-256 sidecar.

The `KnowledgeGraph.canonical()` API loads the full inventory; the former `starter()` name is a compatibility alias **to the same canonical path**, not another partial database.

## Source status and limitations

- **Inventory coverage:** 2,000/2,000, source-transcribed, zero independently fact-verified.
- **Graph connectivity:** 45 curator-hypothesis relationships, not all 2,000 concepts interconnected.
- **Semantic coverage:** ten linked dictionary terms, not general Merriam-Webster coverage or automatic sense discovery in free text.
- **Interpretation:** caller-provided cues, evidence, and context. The free-text path retrieves topics lexically but does not automatically infer justified social explanations, emotions, motives, intentions, or consent.
- **Authority:** advisory outputs, no external operations. No host governance or execution path added.
- **Professional verification:** no external review, certification, or measured generalization accuracy.

See `knowledge/README.md`, `CONTINUITY_MAP.md`, `docs/ACCEPTANCE.md`, `docs/ARCHITECTURE.md`, `docs/RELEVANCE_AND_CORRECTIONS.md`, `docs/STANDARDS_TRACEABILITY.md`, `docs/SEMANTIC_CONTRACT.md`, and `LICENSE-STATUS.md` for the precise scope and outstanding decisions.

## Human statement / attribution increment — Version 1 (in progress)

The development plan is in `docs/IMPLEMENTATION_PLAN.md`; implementation progress is tracked honestly in `docs/TRACEABILITY.json`. This **does not** declare the 120-requirement engine complete.

A standard-library-only interface now captures source words and offsets, proposes speech acts without attributing psychological states, searches the narrow Merriam-Webster-linked registry for candidate ambiguities, and runs limited proposed-answer checks. Caller-provided context is recorded as reports, not independently established social facts. The engine can identify possible effects of its *own draft misquotations* as hypotheses without making claims about what somebody felt.

```sh
python run.py assess examples/sample-utterance.txt > assessment.json
python run.py review-draft assessment.json examples/sample-draft.txt
# On the second command, exit 1 signifies a review finding; exit 0 means only surface checks passed.
```

The earlier `reason`, `search`, `neighbors`, `audit`, `define`, `ingest`, `merge` and `evaluate` commands are preserved. `assess` now includes optional **knowledge considerations** from the full corpus, not claims about the speaker. Explicit session corrections are available in the Python API (`PYTHONPATH=src python examples/session_correction.py`). The text assessment does **not** yet infer reliable social explanations from arbitrary text, and `review-draft` is not complete semantic entailment verification. Proposed-alternative deliberation is an explicitly separate capability within the **same** reasoner and does not validate whether submitted arguments actually justify their conclusions. A host must enforce its verdict for it to function as a gate. All source and corpus verification limits described above still apply.

## Latest Version 1 increment — bounded source-to-premise checks

New code: `semantic_support.py`, `tests/test_semantic_support.py`, and `schemas/premise.schema.json`. An optional `premise` attached to a deliberation warrant can establish a literal source span or a narrow grammatical proposition **as reported in the supplied source**. A changed source digest, unsupported wording, negation reversal, misattributed speaker, or incompatible modal cannot silently count as verified support. Opposed literal source reports remain unresolved and visible. Proposer-supplied rationales and social readings remain unverified. See `docs/BOUNDED_PREMISE_VALIDATION.md` and `examples/bounded_semantic_premises.json`.

## Version 1 - source-to-reading alignment increment

New source-bounded candidate-reading analysis in `reading_support.py` independently compares a proposed reading against available literal source reports. For explicit grammatical statements it can report source support or direct polarity opposition. It also recognizes two *textual* forms without classifying human beings: explicit universal quantification about a named group, and a narrowly described work-product evaluation. Both can coexist; neither establishes the quoted description as true, the author's motive, or an audience's feelings. A narrow third-party private-state attribution guard also stops clearly ungrounded internal-state readings from becoming sole-answer recommendations. Deliberation retains all evidence and qualified alternatives; directly opposed bounded literal readings are excluded from sole-conclusion response guidance.

```sh
python run.py deliberate examples/reading_source_alignment.json
python run.py deliberate examples/literal_reading_opposed.json
PYTHONPATH=src python -m unittest tests.test_reading_support -v
```

See `docs/BOUNDED_READING_ALIGNMENT.md` and the release evidence. Arbitrary social interpretation and independent source authentication **remain incomplete**.
