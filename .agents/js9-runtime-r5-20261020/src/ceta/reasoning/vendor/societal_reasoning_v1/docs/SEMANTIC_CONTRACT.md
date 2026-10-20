# Dictionary-grounded semantics — Version 1

## Authoritative reference and honest limits

Merriam-Webster is the referenced dictionary for material English words in this project's reviewed registry. The registry contains 10 **source-linked, sense-indexed terms**. It does not reproduce the full dictionary and is not a substitute for consultation of the linked Merriam-Webster entries. A `gloss` is original project explanatory language, NOT a Merriam-Webster quotation and NOT evidence of the speaker's private intended sense. Sense references are editorial cross-references to dictionary sections reviewed while producing this release (2026-10-16), not a copied dictionary data license.

Source: https://www.merriam-webster.com/dictionary/context and related entry URLs in `src/societal_reasoning/resources/mw_lexicon.v1.json`.

## Contract

1. **Caller marks material words.** A scenario may specify `material_terms` as an array of `{ "term": "context", "sense_id": "setting" }`. This is metadata from the caller; the engine does not discover material words in natural-language text.
2. **Multiple possible senses:** Without a specified `sense_id`, the engine returns `clarification_required` and names the term. It never silently picks a dictionary sense from a guessed motive, tone, or social role.
3. **Unknown terms/senses:** If no reviewed entry or selected sense exists, the engine returns a bounded clarification. It does not invent a Merriam-Webster entry or assert an invented definition.
4. **Explicit sense:** A valid caller-supplied sense is recorded with the canonical entry link, editorial gloss, and dictionary sense reference. This is a *semantic agreement for the evaluation*, not independent confirmation of any scenario's facts.
5. **Evidence remains separate:** Selecting a sense does not generate evidence cues, grant action authority, establish someone's emotions, or transform reported context into verified observation.
6. **No hidden network:** Runtime is offline. External dictionary links are references for readers; no automated queries, scraping, or dictionary content redistribution occur.

## CLI

```sh
PYTHONPATH=src python -m societal_reasoning define context
PYTHONPATH=src python -m societal_reasoning reason examples/semantic_ambiguity.json
PYTHONPATH=src python -m societal_reasoning reason examples/semantic_resolved.json
```

A natural-language interpreter, external retrieval service, dictionary synchronization, and full Merriam-Webster corpus integration are **not** implemented.

## Why the boundary exists

`context` can refer to surrounding language or the situation in which something occurs. Those are distinct senses. In a consequential question, replacing one with the other without a basis changes the question being answered. A reasoner must surface that distinction rather than make a plausible but unauthorized substitution.
