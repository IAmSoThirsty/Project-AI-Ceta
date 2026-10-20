# Truth Accountability — governed, source-preserving reference

**Scope:** Standalone **adapter/reference extension**, not an integrated release of Societal Reasoning Core Version 1, a replacement for Project-AI, or a second Project-AI governance path. The host-controlled entrypoint for new work is `GovernedTruthCore` together with `GovernedModelBridge`. The original `TruthLedger` remains inside this bundle exclusively for backward-compatible examples and its original 17 regression tests; do **not** expose both APIs as independent production authorization paths.

This implements mechanical parts of the four proposed increments from the truth/perspective/conceptual-limits conversation:

- A — **Source-preserving proposition proposals**: exact UTF-8 source bytes with SHA-256; exact Unicode character spans; typed, untrusted speech-act/modality/negation/quantifier/scope annotations; bounded drift warnings; material ambiguity records and externally checked dictionary/glossary sense references. Meaning-preservation **is not solved by lexical warnings**. Human/speaker review remains required for paraphrases; flagged drift requires source-speaker review.
- B — **Independent evidence path**: host-owned verifier registry; checker identity, independence-group and scoped source reference; support/refutation/inconclusive states; configurable standard and high-stakes independent-group thresholds; conflicting evidence yields `DISPUTED` rather than majority truth; stale checks cannot support facts; deterministic fact renderer.
- C — **Correction and dependent knowledge**: trusted speaker clarification only for attributed meaning, authorized factual review only after refuting evidence; withdrawal, qualified acknowledgement, verified-delivery receipts vs unpublished drafts, retrospective transcript reconciliation, transitive invalidation and append-only hash-linked audit events.
- D — **Conceptual limitation preservation**: anomaly records retaining failed categories and features, repeated-pattern research queue, and untested hypotheses that cannot be treated as findings.

**Additional**: multiple first-person perspectives are retained with distinct time/context/speaker instead of mechanically declared mutually exclusive or universally true. The optional loopback-only Ollama transport obtains model JSON proposals but has **no truth authority**.

## Run entirely offline

Requires **Python 3.10+**, standard library only. No model, database server, API key or internet connection is needed for deterministic tests and the demo.

```bash
cd truth-accountability-reference
python -m unittest discover -s tests -v
python demo_governed.py
python demo.py
```

To try a **local** Ollama model installed on your own computer, run an Ollama server locally and use:

```bash
python example_ollama.py --model YOUR_INSTALLED_MODEL --text "I am asking you to understand."
```

This optional real-model path was **not executed or evaluated** during package verification. A model proposal that is malformed or unsafe fails closed. A local model's fluency is not a verifier.

## Minimal guarded use

```python
import json
from truth_accountability import (
    GovernedTruthCore, GovernedModelBridge, VerificationRegistry,
    VerifierSpec, bounded_arithmetic, arithmetic_only_policy,
)

registry = VerificationRegistry()  # HOST-OWNED, not available to the model
registry.register(VerifierSpec("arithmetic", "arith-v1", bounded_arithmetic))
core = GovernedTruthCore("truth.db", registry)
bridge = GovernedModelBridge(core, arithmetic_only_policy)
source = core.preserve("authenticated-speaker-id", "I asked you to understand.")
proposal = json.dumps({"kind": "paraphrase", "text": "You demanded obedience",
                       "source_id": source, "span": [0, len(core.original(source))]})
result = bridge.process(proposal, current_source_id=source)
print(result.decision, result.text)  # no automatic false attribution
core.close()
```

`AuthenticatedActor` is a **host assertion**, not authentication implemented by this package. The caller must authenticate users, isolate tenants, protect verifier registration and require delivery receipts from the actual transport. A string or a model claiming to be the source speaker is insufficient.

## Meaning and truth are separate

- A verified quote proves its exact presence in the source record; it does **not** prove the quoted factual claim.
- A person's clarification can correct the AI's attribution of **their intended meaning**, not settle independent physical facts.
- An approved paraphrase means a bounded person/reviewer check took place, not that a semantic algorithm proved equivalence.
- `SUPPORTED_BY_CHECK` means registered checks support a scoped proposition; it never means absolute or universal truth.
- Evidence sources are not instructions. Text retrieved from a document must remain data, regardless of imperative wording.
- A completed test suite proves the deterministic fixtures behaved as tested, **not** reliable interpretation by a real AI.

## Files

- `truth_accountability/governed.py` — canonical new evidence and correction gate
- `truth_accountability/semantic.py` — typed annotations and limited risk heuristics
- `truth_accountability/verifiers.py` — host registry and bounded arithmetic example
- `truth_accountability/bridge.py` — JSON proposal -> registered evidence -> deterministic response
- `truth_accountability/ollama_adapter.py` — optional local model transport, proposals only
- `truth_accountability/core.py` — original legacy reference API, not the new gate
- `schemas/model_proposal.schema.json` — inspectable proposal contract
- `docs/SECURITY.md` — threat boundaries and remaining engineering obligations
- `docs/EVALUATION.md` — requirements for actual behavioral validation
- `docs/ACCEPTANCE.md` — implemented/incomplete controls by increment
- `docs/SOCIETAL_CORE_ADAPTER.md` — future integration boundary, no modification performed
- `tests/` — deterministic unit/adversarial fixtures

See `INTEGRATION_GUIDE.md` for previous integration rationale. The new documentation supersedes its description of A–D as merely proposed **for this reference package only**, not for the separate Societal Reasoning Core repository.

## Increment E: Source-bound adapter staging and evaluation runner (2026-10-18)

- `truth_accountability/societal_v1.py`: read-only ZIP/directory inspector, explicit structural corpus mapping, contextual retrieval with provenance and source-mutation detection.
- `truth_accountability/societal_pipeline.py`: bounded contextual candidates enter **only** the host-owned `GovernedModelBridge`, never a new fact/approval route.
- `inspect_societal_v1.py`: inspect an owner-supplied Version 1 source archive without importing its Python code.
- `evaluate_model.py`: 24 developer-authored adversarial protocol cases, supports mock, replay and actual loopback Ollama, with explicit inference-class labeling.
- `demo_societal.py`: fully offline synthetic demonstration.

**Source status (superseded staging restriction):** Increment E originally had synthetic sources only. Increment F now verifies the uploaded owner ZIP against its source manifest, runs the original suite, maps all 2,000 actual records, and calls its real runtime API. This is an adapter for the separately supplied Version 1 source, not incorporation of Version 1 into the ZIP or evidence of live-model accuracy. See `docs/VERSION1_BINDING_AND_EVALUATION.md`.

## Increment F: actual Version 1 source binding and defect repair

The earlier Increment E statement that the real Version 1 source was inaccessible has been superseded. On 2026-10-18 the exact owner ZIP was attached, hash-verified, safely extracted, checked with Version 1's original verifier, and its 440 tests run. `configs/version1_canonical_mapping.json` reflects its **actual** `id` and `original_text` fields, not the prior synthetic fixture.

The original Societal Reasoning Core **Version 1 remains unchanged and is NOT included in this new archive**. No redistribution license has been selected for it. The source is required as a separately owner-provided ZIP, never downloaded or inferred from a filename. To reproduce original-source binding, run:

```sh
python demo_real_version1.py --archive /path/to/Societal-Reasoning-Core-v1.zip --runtime-root /path/to/Societal-Reasoning-Core
```

The new behavior advisor is injected by the trusted host only after verifying the extracted source. It calls original Version 1 `assess_text`/`review_draft`, and can hold a proposal; it never grants a fact's truth or independently determines someone's private intentions. The model cannot write the evidence, approve its own hypotheses, or substitute quotes.

**Security update:** Audit events now bind decision-critical SQLite rows; four independently reproduced tampering/person-hypothesis defects have new regressions. A host-held HMAC key and off-database anchor are needed for stronger tamper evidence. There is no safe automatic migration for pre-F unsealed ledgers. Refer to `RELEASE_AUDIT.md` and `docs/VERSION1_BINDING_AND_EVALUATION.md`. Live-model accuracy and production readiness are NOT established.
