# Version 1 - knowledge relevance and explicit session corrections

## Purpose and verified boundary

The owner-defined purpose is contextual restraint: help an AI consider complex human circumstances without converting a person's actual words into invented claims, character labels, feelings, motives, or consent. The 2,000-entry corpus provides *topics to consider*, not diagnoses or a classification of humanity.

This development increment integrates **bounded lexical retrieval** with the existing text and structured-scenario interfaces, and provides an **opt-in, in-memory correction ledger**. Neither component establishes general social understanding, semantic entailment, mind reading, independent factual verification, or reliable causal inference. The release remains **Version 1**.

## Input-to-knowledge path

`SocietalReasoner.assess_text()` records the exact utterance and reports/suggested context as before, then uses `KnowledgeRelevance.suggest()` to identify potentially relevant topics in the canonical 2,000-entry graph. Only exact input text and caller-attributed context reports can seed retrieval. A `model_hypothesis` cannot seed retrieval. A context category with contradictory reported values is excluded from context-derived retrieval until resolved; those conflicts remain visible in the context record.

The output `knowledge_considerations` has two separate channels:

- `topics`: bounded lexical candidates, each carrying an inventory ID, original label, source ID, original origin, SHA-256 of the exact source text, matched tokens, source status, and a **lexical score that is not confidence or truth**.
- `related_relationship_hypotheses`: one-hop, provenance-labeled **unverified** connections from up to three selected concepts. Relationships do not activate rules, certify causes, or imply facts about human participants. There is no recursive propagation of relationship truth.

`SocietalReasoner.analyze(Scenario)` exposes the same optional knowledge leads, based only on non-interpretation evidence and explicitly caller-reported scenario context. The existing five rules and their existing result criteria are unchanged. The question itself is **not** treated as observational evidence in the structured path.

Retrieval uses reproducible token matching, filtered common terms, label/alias coverage requirements, and a rarity-weighted ranking; it does **not** implement contextual language understanding or synonym reasoning. It may omit relevant topics. It may suggest a broadly related topic without establishing that topic applies to a situation. A false-positive **topic** is not a fact about a person, but is still a retrieval-quality defect to evaluate later.

Resource bounds: 64 source records, 131,072 characters total across sources, 20 returned topics maximum, 30 associated edge hypotheses maximum. Missing matches return an explicit empty result. There is no forced category assignment or inferred private state.

## Correcting session history without rewriting it

The `CorrectionLedger` explicitly requires: one validated session ID, two existing turns in that session, the *same speaker*, a later correction turn with an explicit correction marker, and a nonempty exact span selected from the corrective utterance. Ordinary disagreement is not treated as a correction automatically.

An accepted correction generates a digest-linked event with the original and replacement turn hashes and an exact source span. The prior statement remains recorded but becomes **superseded** in that session. Another correction may supersede the current replacement. The local event records report what the speaker said, **not** independent factual truth or a machine-verified interpretation of the new meaning.

`CorrectionLedger.review_current_attributions()` can hold a *verbatim* superseded utterance explicitly presented as the user's **current** statement. Crucially, it allows both qualified and unqualified historical quoting such as `You said "..."`; a statement was still said even if later corrected. This is intentionally narrower than detecting all semantic paraphrase errors. The facade `SocietalReasoner.review_draft(..., correction_ledger=ledger)` enforces source-hash and session-ID matching before adding these findings to the existing draft review.

No session state is automatically persisted. `ledger.purge()` deletes the in-memory references held by this ledger instance and closes it. This does not erase copies held elsewhere by the calling application, runtime, user, logs, or archive. The caller controls its own retention, access, and session lifecycle. There is no cross-conversation store and no automatically created personality profile.

## Example usage

```sh
python run.py assess examples/sample-utterance.txt
PYTHONPATH=src python examples/session_correction.py
PYTHONPATH=src python -m unittest discover -s tests -q
```

Python interface:

```python
from societal_reasoning import CorrectionLedger, SocietalReasoner
from societal_reasoning.input_boundary import Utterance

reasoner = SocietalReasoner.starter()
assessment = reasoner.assess_text("Explain humor.", turn_id="u1")
possible_topics = assessment["knowledge_considerations"]["topics"]

ledger = CorrectionLedger("local-session")
ledger.add_turn(Utterance.capture("I might attend.", turn_id="u1"))
corrected = Utterance.capture("Correction: I will not attend.", turn_id="u2")
ledger.add_turn(corrected)
ledger.correct("u1", "u2", start=12, end=len(corrected.text))
source = reasoner.assess_text("I might attend.", turn_id="u1", session_id="local-session")
review = reasoner.review_draft(source, 'Your current position is "I might attend."', correction_ledger=ledger)
assert review["status"] == "hold"
ledger.purge()
```

## Acceptance evidence

- `tests/test_relevance.py`: record admissibility, no forced category, source identity and digest, model-hypothesis exclusion, conflict filtering, stable ranking, edge provenance, input limits, and integration behavior.
- `tests/test_corrections.py`: explicit correction authority, original preservation, source spans, event chain, follow-up corrections, speaker/session separation, dismissal of unmarked disagreement, deletion, stale-current-quote checks, and facade behavior.
- `tests/test_text_contract.py`, `tests/test_engine.py`, and `evaluations/behavior-contract.v1.json`: the previous interfaces and behavior regressions continue to run.
- `verification-report.json`, `manifest.json`, and ZIP-sidecar checksum: local reproducibility and bounded completed checks.

## Outstanding capabilities (not completion claims)

A general-language interpreter that finds socially relevant evidence without prelabels, reviewed semantic retrieval, independently validated graph relations, semantic entailment of arbitrary paraphrases, automatic explicit-correction discovery across conversation, contextual interpretation after correction, independent blinded evaluation, and actual host enforcement remain open. The local original-chat transcription has not been independently authenticated and the knowledge claims have not been independently fact checked.
