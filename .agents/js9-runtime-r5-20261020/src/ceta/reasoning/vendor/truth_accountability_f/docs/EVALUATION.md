# Evaluation requirements: fixtures are not live-model evidence

**Increment E update (2026-10-18):** `evaluate_model.py` now runs 24 synthetic developer-authored adversarial fixtures through mock, replay, or optional local Ollama proposals. Mock/replay are NEVER classified as live-model evaluations; no Ollama service was reachable in this environment. See `VERSION1_BINDING_AND_EVALUATION.md` and `evaluations/mock_evaluation_report.json`. The original requirements below remain in force; 24 synthetic cases do not satisfy the independently authored / human-reviewed release targets.


Deterministic `unittest` cases check SQL state transitions, known lexical warning patterns, evidence lifecycle, restricted JSON proposals, provenance records, corrections, source replay, the discrepancy between publication and generation, and the unresolved anomaly queue.

They do **not** test whether an actual model consistently extracts semantics, identifies user meaning, avoids invented mental states, seeks sufficient external evidence, or notices conceptual gaps. Evaluate those separately before placing this path in front of real users.

## Recommended test methodology

Use a held-out, independently authored corpus with consent. Preserve an exact speaker statement, contextual ground truth, and source-authenticated review decisions. Include adversarial cases with negation, first-person reports, conditionals, temporal modifiers, estimates, quotation, modal distinctions, sarcasm, coded language, disagreement, power imbalance, corrections, unanswerable questions, external-source prompt injection and entirely novel phenomena. Record independent expert ratings and disagreements without treating majority vote as factual ground truth.

For each model+prompt+runtime version measure: (1) unsupported factual-assertion rate, (2) false attribution and meaning-distortion rate, (3) false admissions of prior publication, (4) evidence-insufficient abstention correctness, (5) correction detection and dependent-invalidation rate, (6) prompt-injection bypass rate, (7) misclassified unknown observations, and (8) unnecessary clarification rate.

Test model output bypass separately: the application must not append a raw generative completion after the trusted renderer. Inject malformed JSON, duplicate keys, network errors, bad evidence locators, forged speaker principals, stale and contradictory measurements, model requests to install verifiers, and attempts to declare facts based on quotations.

## Acceptance status

- **Deterministic code unit/adversarial tests**: runnable in this package; see current `RELEASE_AUDIT.md`.
- **Model-in-the-loop evaluation**: NOT RUN in this package.
- **Independent semantic reviewers**: NOT RUN on an external corpus.
- **Cryptographic signing and protected multi-user deployment**: NOT IMPLEMENTED.
- **Production readiness**: NOT ESTABLISHED.

Create and freeze a gold-test corpus before tuning the live model; prevent evaluation leakage, report both absolute counts and confidence intervals, and preserve failures with redacted source/replay IDs.
