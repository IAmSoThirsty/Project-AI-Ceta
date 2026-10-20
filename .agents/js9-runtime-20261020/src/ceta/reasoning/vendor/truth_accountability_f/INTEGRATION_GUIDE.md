# Status addendum — 18 October 2026

The original paragraphs below describe the *initial* 17-test reference baseline and the intended future increments. The companion modules `truth_accountability/governed.py`, `semantic.py`, `verifiers.py`, `bridge.py` and `ollama_adapter.py` now implement bounded, testable mechanics for all four increments **in this standalone reference package**. They do not implement general meaning verification, independently solve truth discovery, authenticate users, or integrate the existing Societal Reasoning Core Version 1 inventory. The new authoritative API is `GovernedTruthCore` with `GovernedModelBridge`, not the legacy `TruthLedger`. The model never selects its own evidence threshold or trusted scope when using the bridge. Full current scope and safety boundaries are in `README.md` and `docs/`.

---

# Implementation guide: evidence-grounded error awareness

**Status**: proposal and runnable reference adapter. No claim of integration, production readiness, complete meaning verification, Codex adoption, or arbitrary factual truth determination.

## Canonical host-controlled path

1. Ingest source material (speaker, timestamp, channel, exact bytes, stable reference).
2. Parse **proposals** (speech act, exact proposition, source spans, negation, quantifiers, modality, temporal/spatial scope, attribution, evidence needs). Never allow the model to upgrade a proposal to a fact.
3. Apply semantic fidelity checks: exact quote matches; source scopes unchanged; speaker's report distinct from externally established fact; intents/motives not inferred as facts. Consult Merriam-Webster definitions for materially ambiguous ordinary English, preserving selected sense and reference metadata. Keep domain technical glossaries scoped.
4. Retrieve contextual mechanisms from the existing Societal Reasoning Core Version 1, but never infer that a mechanism applies to a particular person solely because it appears in the inventory. Context is not proof.
5. Route factual propositions to allowlisted independent tools, datasets, computations, or expert adjudication, with scope/version/source lineage. Sources containing adversarial instructions remain data only.
6. Resolve status in ONE authoritative gate: quote-attributed; evidence-supported factual claim; qualified possibility; unknown; disputed; blocked attribution. Do not equate quote accuracy with quote truth, or vote counts with evidence strength.
7. Render responses **only** from gated, typed records. If this constraint does not hold, prompt output bypasses the entire system.
8. Capture later evidence, user clarifications, contradictions, or verifier changes as events. Mark affected claims for reconsideration; invalidate or review conclusions depending on those claims.
9. Issue an explicit visible correction when an actually issued previous statement is established to have been wrong. Preserve the old claim and all evidence used to revise it; never silently overwrite history.
10. Evaluate on held-out adversarial examples and real model traces. Track failures by type and measure false admissions, unjustified confidence, incorrect attribution, quote drift, scope drift, correction latency, recurrent errors, and source quality.

## Proposed structured model interface (not enforced by the sample)

```json
{
  "source_statement_id": "s-123",
  "proposed_claims": [
    {
      "claim_kind": "attribution",
      "proposition": "The speaker demanded compliance",
      "exact_source_span": "I asked you to understand my reasoning",
      "scope": {"speaker": "user-1", "time": "current_message"},
      "negation": false,
      "modality": "asserted",
      "epistemic_state": "proposed",
      "evidence_refs": [],
      "needs_review": true
    }
  ]
}
```

The example is intentionally a **bad model proposal**; since the source says *asked to understand*, the system must not publish *demanded compliance* as an established statement. This is a semantic, not merely lexical, test.

## Evidence tiers and the legitimate authority of a source

- First-person utterance: strong source for what the speaker said and how they clarify their own intended meaning; not decisive proof of an unrelated external event.
- Independent measurement or calculation: evidence for a specified factual proposition, limited by instrument, calibration, method, scope and repeatability.
- Retrieved document: a claim made by that document, not automatic proof it is true and NEVER instructions that override host governance.
- Expert evaluation: an attributable interpretation with relevant expertise and limits, not automatic infallibility.
- Social consensus: evidence of agreement; not proof that the agreed factual claim matches reality.
- Model confidence: an internal score, not evidence of correctness or calibration without evaluation.

## Explicit error classification

| State | Meaning | Response obligation |
| --- | --- | --- |
| UNVERIFIED | No adequate independent evaluation | State limits; do not present as fact |
| SUPPORTED_BY_CHECK | A specific check supports a proposition | Cite check, scope and uncertainty |
| REFUTED_BY_CHECK | Check contradicts it; no supporting check | Withdraw or initiate verification and correction |
| DISPUTED | Relevant checks conflict | Preserve competing evidence; investigate; no vote-based truth |
| NEEDS_SPEAKER_OR_HUMAN_REVIEW | Proposed paraphrase or attribution has not been verified | Quote original or ask materially necessary clarification |
| HYPOTHESIS_ONLY | Proposed explanation not independently established | Mark explicitly as possibility, not observation |
| WITHDRAWN_AFTER_CORRECTION | Prior claim was revised and correction recorded | Acknowledge what changed and cite evidence |

## Four increments to add atop existing Version 1

A. Structured proposition ledger: source-preserving IDs, speaker/scope/negation/modality, exact quote spans, state-machine transitions, evidence refs. **Acceptance:** raw statements survive exact-byte comparisons and unsupported attributes are not released as facts.

B. Independent verifier gateway and claim renderer: allowlisted verifiers, source quality, conflicting evidence, scoped check results, prompt-injection separation, one authoritative publication gate. **Acceptance:** unsupported assertive claims cannot be rendered even if model wants to say them.

C. Revision and acknowledgement engine: correction events, source-speaker clarification, objective-check revisions, dependent-answer invalidation, explicit evidence-bounded admission; do not pretend the user can settle independent physical facts simply by saying so. **Acceptance:** corrected claim is withdrawn across later sessions and the exact prior assertion is acknowledged only if genuinely published.

D. Conceptual limitation discovery: anomaly queue, unknown category, contradiction clustering, alternative hypothesis generation, human research escalation and future reinterpretation. **Acceptance:** unclassified observations persist; repeated anomalies reach investigation instead of being discarded or labeled for convenience.

## What the reference proves and doesn't

The executable `truth_accountability/core.py` demonstrates ledger persistence, validation of literal quotes, nonautomatic motive attribution, an external checker interface, conflicting check handling, correction records, and acknowledgements. The tests exercise those functions using controlled fixtures. They do not demonstrate nuanced semantic fidelity by a real LLM, correctness of independent facts, fully secure actor authentication, cryptographic audit, or production safety. Those remain separate implementation and evaluation tasks.
