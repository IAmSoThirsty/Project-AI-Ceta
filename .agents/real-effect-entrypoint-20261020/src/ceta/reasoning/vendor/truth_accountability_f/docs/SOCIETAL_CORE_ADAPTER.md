# Societal Reasoning Core Version 1 — source-bound adapter

**Current status (2026-10-18):** Increment F has verified the exact owner-provided source ZIP, its 109-file release manifest, 2,000 sequential corpus entries, and 440 original source tests. The canonical field mapping is explicit in `configs/version1_canonical_mapping.json`: `src/societal_reasoning/resources/concepts.full.jsonl`, fields `id` and `original_text`. The original ZIP SHA-256 is pinned and preserved in `docs/VERSION1_BINDING_AND_EVALUATION.md`.

**The connection is local and read-only**: the Version 1 ZIP is not bundled or republished. The adapter extracts contextual considerations with source and entry provenance, not personality labels or truth authority. The optional actual runtime advisor uses `SocietalReasoner.assess_text` and `review_draft` only as an additional conservative hold/review boundary. Neither passing an advisory review nor repeated societal concepts prove anyone's beliefs, intentions, experiences, or facts.

## Canonical host boundary

1. Exact original user statement and source span preserved in `sources_v2`.
2. Inspected Version 1 source inventory supplies optional source-linked context candidates, kept separate from independent evidence.
3. The optional actual V1 runtime produces source assessment and draft-review *advice*, never verifiers or assertions.
4. Untrusted model JSON flows only through `SocietalGatedPipeline` -> host-owned `GovernedModelBridge` -> `GovernedTruthCore`, with optional V1 review preventing unsafe output.
5. Speaker corrections and externally verified factual changes are distinct, logged, and used to invalidate dependent claims.
6. Project-AI remains a **separate owner-controlled system**; there is no code path or authorization to edit or integrate it here.

## Verified locally

- Version 1 source verifier and 440 original tests pass.
- Accountability combined suite: 167 tests pass, including nine genuine Version 1 integration cases.
- 24 scripted adversarial gate cases pass with actual Version 1 contextual retrieval, but those cases are NOT live-model accuracy evidence.
- The live original source review is a bounded lexical/surface analysis and can return false positives and false negatives; verified quotations of uncertain statements can still lead to `REVIEW_HOLD`. This remains a limitation, not a hidden success.

## Pending before any production or public release

Host authentication and protected keys/checkpoints, real independent fact-verifier quality, human-rated model-in-loop evaluation, owner decisions about Version 1 licensing, legacy DB migration, protected storage, and explicit authorization for any Project-AI integration. See `docs/VERSION1_BINDING_AND_EVALUATION.md` and `RELEASE_AUDIT.md`.
