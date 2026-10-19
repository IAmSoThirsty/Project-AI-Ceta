# Standards and work-ethic traceability — Version 1

## Authority of referenced materials

This record uses available project history and the accessible **Thirsty's Codex / Standards Edition — Volume XXI: Human–AI Interactions (design draft dated 2026-10-09)**, plus available operating directives about continuity, source authority, scope, fail-closed behavior, and **No Proof, No Claim**. The Volume XXI document explicitly states **DRAFTED / OWNER REVIEW PENDING / NOT RATIFIED**. It is treated here as a design reference, NOT a ratified or superseding governing standard. The complete source documents for Editions I–XX were not materialized and checked in this increment. **No claim of full Codex conformance is made.**

## Traceable implementation decisions

| Referenced principle / draft control | This increment | Evidence | Boundary |
|---|---|---|---|
| Literal meaning; Merriam-Webster source preference; V21-AU-04 | Source-linked `LexicalRegistry` and material sense IDs | `tests/test_semantics.py`, `sre define` | Only 10 reviewed terms; no full natural-language interpretation |
| Preserve expressed objective; V21-AU-02 | Does not replace caller scenario or select unresolved material senses | `clarification_required` cases | Caller still supplies structured facts, cues, and material terms |
| Distinguish sources, rules, interpretations; V21-AU-03 | Prior `interpretation` cues excluded from rule evidence | `test_engine.py`, evaluation case `prior_interpretation_not_evidence` | Caller-supplied `direct_observation` remains caller-provided |
| Evidence provenance; V21-AU-05 | All 2,000 records include local source and entry SHA-256; per-volume compilation and full-corpus invariants checked | `tests/test_full_inventory.py`, `scripts/compile_inventory.py` | Unsigned hashes; manual transcription not externally authenticated against a chat export |
| No proof, no claim; V21-AU-06 | Count/status separation and release-gated test and evaluation reports | `manifest.json`, `verification-report.json`, `docs/ACCEPTANCE.md` | Passing fixture tests do not establish general social-reasoning reliability |
| Resistance to narrative substitution; V21-AU-08 | Source records and interpretation kept distinct | `epistemic_record`, `rule_trace` | Does not independently decide whether caller descriptions are accurate |
| Resilience to pressure; V21-AU-11 | Quoted instructions never alter execution | `test_malicious_text_cannot_execute` | No model-level adversarial or prompt-injection certification |
| Govern authority; V21-AU-01 | Advisory-only outputs with no action permissions | `operational_boundary` checks | No execution gate is implemented in this standalone engine |
| User ethics: continuity, honest unknowns, smallest sufficient change, independent challenge | Historical archives untouched; one canonical graph of 2,000 entries; owner-fixed Version 1; explicit release gates | `CONTINUITY_MAP.md`, `tests/test_full_inventory.py`, `scripts/build_release.py` | Independent human review still pending |

## Host-system boundary

This is an independent project. No host code, CETA/Project-AI configuration, governance state, or decision rights have been modified. Integration is deferred until separately requested after host scope completion.

## Open challenges before broader claims

- The entire 2,000-entry source inventory **has** been manually transcribed and compiled. Independent comparison with a machine-readable original conversation export is not completed; local compilation is not external authentication.
- Semantic coverage of colloquial and culturally situated language is **not** established by 10 reviewed dictionary links.
- The 18 evaluation cases are **developer-authored regressions**, not held-out field evaluations.
- Independent testing, security assessment, runtime performance testing, and end-to-end deployment evidence remain open.
- Ratified Codex I–XX and Volume XXI status must be reconciled before claiming specific conformance.
- Source-release ZIP is locally generated; a public GitHub release and open-source license have not been authorized.

## Current context-retrieval and session-correction evidence

- Source-to-inference separation (draft V21-AU-03/AU-08): `KnowledgeRelevance` accepts caller-originated inputs only, excludes model hypotheses/conflicting context dimensions, and returns unverified topics rather than facts about anyone; tested in `tests/test_relevance.py`.
- Claim and evidence integrity (draft V21-AU-05/AU-06): topic leads link to source IDs and SHA-256; edges retain hypothetical provenance, and zero knowledge matches do not generate labels. This is not proof the source reports or claims are true.
- Source-preserving correction (draft V21-AU-02/AU-07): `CorrectionLedger` requires a same-speaker marked later correction, preserves old source history, supports a narrow stale-quotation checker, and provides a local purge operation; tested in `tests/test_corrections.py`. It is not automatic conversation understanding or persistent user memory.
- The referenced controls remain **draft design sources, not ratified obligations**; this local implementation does not constitute full Codex conformance.
