# Scope and acceptance: four increments in the reference package

| Increment | Demonstrated mechanisms | Explicitly unresolved |
| --- | --- | --- |
| A. Structured semantic proposals | exact UTF-8 source, Unicode spans, typed speech-act/negation/modality/scope labels, strict JSON schema, bounded drift flags, meaning review, ambiguity/sense record | complete semantic entailment; automatic, authoritative Merriam-Webster lookup; automated nuance and sarcasm detection |
| B. Independent check gateway | host-only registry, scoped checks, evidence hashes and locators, expired and conflicting checks, distinct source groups, standard/high-stakes thresholds, deterministic assertion renderer | real external web/source connectors; independent provider trust validation, source calibration, general fact checking |
| C. Corrections and revision | speaker vs external evidence correction, delivery receipt reconciliation, no fabricated 'I previously said', persistent withdrawal, transitive dependency invalidation, audit hash chain | host identity auth, signature/anchored audit, secure retrieval, protected database, automatic safe reinterpretation of entire dependency graph |
| D. Novelty handling | persistent anomalies, category-failure records, repeated-pattern research queue, hypotheses with specified tests | scientifically validated anomaly detectors, automatic conceptual expansion, test outcomes or discoveries |

## Conformance boundary

The phrase **implemented** refers to these mechanisms in this standalone reference only. Successful deterministic fixtures do not prove a real AI has adopted the behavior or that the separate 2,000-entry Societal Reasoning Core uses this implementation. The existing Core retains its Version 1 designation. Project-AI is unchanged.

## Operational sequence for the canonical new path

1. Trusted host authenticates caller and preserves exact input.
2. Untrusted model submits a structured proposal and source span; `propose_json` validates structure but not meaning.
3. Host checks possible drift and obtains source-speaker or authorized meaning reviews, or selects appropriate registered fact verifiers.
4. `decision` reports epistemic status; `render` refuses unsupported assertive claims. `GovernedModelBridge` returns safe qualified alternatives without unsupported paraphrases.
5. Host sends the deterministic text unchanged; it may record `confirm_delivery` only with an actual delivery receipt.
6. Verified corrections are appended and downstream claims invalidated; original statements and evidence history remain available (subject to later privacy/retention controls).
7. Unclassified observations enter the anomaly queue; no unsupported reclassification or discovery assertion is permitted.
