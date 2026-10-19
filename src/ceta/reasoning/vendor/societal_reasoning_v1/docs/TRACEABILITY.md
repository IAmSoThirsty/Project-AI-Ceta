# Version 1 mission-specific requirements and evidence

The accepted project objective is in `OBJECTIVE_AND_BOUNDARIES.md`. The exact **proposed** 120 requirements A01–L10 and development sequence are in `IMPLEMENTATION_PLAN.md`.

`TRACEABILITY.json` is the mechanical register, regenerated using `python scripts/requirement_register.py`. It is a work-state report, **not a conformance certificate**. `verified_bounded` means a narrow, specifically tested contract is supported by local evidence. `partial` means the full requirement is not done. `blocked_external_or_independent_evidence` means evidence depends on absent authentic sources, independent evaluation, or owner release decisions. `not_implemented_or_not_verified` must not be assumed to have passed.

Reviewers should compare reported tests to the source test functions and independently rerun `PYTHONPATH=src python -m unittest discover -s tests -q`. Test author is not an independent social reasoning evaluator. Do not promote authored fixtures into population-level accuracy claims.

## Current increment evidence changes

New bounded implementation/test pairs: `relevance.py` / `test_relevance.py` (E05, E06, E09, selected D/G/I checks) and `corrections.py` / `test_corrections.py` (J01-J09 with explicit, opt-in semantics). These remain **partial**, not certified requirements. `scripts/requirement_register.py` generates the exact current status values. The additional tests are self-authored and do not replace independent evaluations.

## Current additional evidence: attributed alternative readings

`src/societal_reasoning/deliberation.py`, `tests/test_deliberation.py`, `schemas/deliberation.schema.json`, and the two context-variation fixtures demonstrate a bounded change of contextual warrant applicability with source attribution, counterevidence preservation, and no promotion of model guesses or earlier interpretations into facts. They provide **partial**, not full, implementation evidence for D04, D05, F03, F05, F07, F08, F09, F10 and G08. The algorithm DOES NOT independently verify that a proposed rationale semantically supports a reading. This limitation prevents stronger conformance claims.

**F02 remains unimplemented:** no automatic generation of novel interpretations from unstructured conversations; the caller supplies candidates.

## Version 1 — bounded literal support evidence

`src/societal_reasoning/semantic_support.py` and `tests/test_semantic_support.py` now provide source-digest-bound span checks, a restricted actor/modal/polarity/action/object comparison, and identification of some opposing source reports. This is partial evidence toward B03, F03, G03, G04, G05, G07 and G08, **not** proof of complete human-language interpretation, social entailment, or independent source validity. There is no automatic social-cue discovery or proof that the candidate's rationale supports its reading.

## Version 1 - bounded candidate-reading alignment

`src/societal_reasoning/reading_support.py` / `tests/test_reading_support.py` now provide narrow source-to-*reading* alignment checks without trusting proposed warrants. Explicit universal quantifier wording and limited work-product evaluation wording can be cited as *text features*, not as verdicts about people. The core can also keep a directly opposed literal reading out of single-conclusion response guidance. This is additional **partial** evidence toward F03, F06, G03, G07 and D04. It does not establish independent social inference, user-intent inference, factual source authentication or a full semantic-entailment capability.
