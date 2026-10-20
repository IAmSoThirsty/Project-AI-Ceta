# Exact owner-source binding, Version 1 (Increment F)

**Status:** Source-grounded integration of an *unchanged* owner-provided archive into a **separate** host accountability reference. This is a local reference and evaluation result, not owner ratification, full engine completion, model accuracy proof, or permission to redistribute Version 1.

## Authoritative input and checks

- Exact archive: `Societal-Reasoning-Core-v1.zip`, owner supplied, SHA-256 `b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5`.
- Original Version 1 packaging: 109 files, all matched its original `SHA256SUMS` through original `scripts/verify_release.py`; the source root and `__version__` are still `Societal-Reasoning-Core` and `1`.
- Original `scripts/compile_inventory.py` verified 2,000 sequential entries from two source-transcribed volumes with no source/compiled conflicts. This is **not** independent authentication of the earlier conversation transcription or any social claims in the inventory.
- Existing original Version 1 suite: 440/440 unit tests passed in this environment, using `PYTHONPATH=src python -m unittest discover -s tests -q` from the extracted original root.
- Canonical JSONL is `src/societal_reasoning/resources/concepts.full.jsonl` (within the Version 1 root), with numeric `id` 1–2000 and original source entry string `original_text`.
- Exact JSONL SHA-256: `96a39faf6e3f13f3d6377896ee495edcfd44065cd14d4e4643d247f734d4af2c`.
- The host-reviewed mapping is `configs/version1_canonical_mapping.json`. No model or societal-knowledge entry is permitted to choose its own corpus field mapping or fact authority.

## Actual API contract, verified by execution

The original library exports `__version__ == "1"`, `SocietalReasoner.starter()`, `assess_text(utterance, *, turn_id, speaker, ...)`, and `review_draft(assessment, draft, ...)`. These were executed from a clean extraction against the owner archive. They return `text_assessment.v1` and a `pass|review_needed|hold` draft status respectively. Their own documents explicitly say these surface checks do not establish general semantic correctness.

`truth_accountability.version1_runtime.Version1RuntimeAdvisor` consumes those **actual** APIs, verifies exact source/speaker preservation and source digest, and reports `ADVISORY_PASS` or `REVIEW_HOLD`. Incorrect schema, source substitution, exceptions, and unknown review statuses fail closed. The host can inject the adapter into **the same** `SocietalGatedPipeline`; there is no additional model-authoritative output route. A Version 1 `pass` is advisory only and never authorizes a factual claim.

The read-only ZIP inspector and its concept-matcher never import or execute the source. The runtime advisor is only enabled after the trusted host separately supplies and validates its extracted runtime. The demonstration verifies all 109 extracted files byte-for-byte against the owner ZIP before importing them.

### Reproduce locally

From the *accountability reference* directory, with an authenticated copy of the original Version 1 ZIP and its clean extracted root:

```sh
python demo_real_version1.py --archive /path/Societal-Reasoning-Core-v1.zip --runtime-root /path/Societal-Reasoning-Core
```

```sh
SOCIETAL_V1_SOURCE=/path/Societal-Reasoning-Core-v1.zip \
SOCIETAL_V1_ROOT=/path/Societal-Reasoning-Core \
PYTHONPATH=/path/Societal-Reasoning-Core/src:. \
python -m unittest discover -s tests -q
```

```sh
python evaluate_model.py --backend mock \
  --source /path/Societal-Reasoning-Core-v1.zip \
  --mapping configs/version1_canonical_mapping.json \
  --expected-source-sha256 b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5 \
  --report mock-report.json
```

The real-source smoke test proposed **"You demanded obedience"** after the source actually asked for understanding. The final gate returned `NEEDS_MEANING_REVIEW` and did not release the invented attribution. The source/runtime API preserved the exact original statement.

## Rectified findings from the independent A–E review

1. **Check verdict mutation:** Each factual check record is now sealed into its originating hash-linked event; an unsynchronized `refutes` -> `supports` SQL edit produces an audit-integrity failure. All decision renders and writes fail closed after a mismatch.
2. **Evidence policy mutation:** Proposal policy is included in the original row seal; lowering `high_stakes` to `standard` through raw SQL is detected and blocked.
3. **Unsupported personal motive hypothesis:** The model-facing `GovernedModelBridge` now **withholds all unreviewed hypotheses by default**, including unanticipated vocabulary. A host-supplied review callback can explicitly release a hypothesis with an *unverified* label, but is not model-controlled.
4. **Deleted corrections:** Correction rows are bound to audit events and their disappearance triggers integrity failure, so a withdrawn claim cannot be rendered as though its correction never existed.

The retained prior scenario S16 expectation was deliberately changed from `HYPOTHESIS_ONLY` to `HYPOTHESIS_HELD_FOR_REVIEW` to reflect the stronger policy. Corresponding baseline unit tests were updated, with extra regression tests for explicit host review. This is an **intentional interface behavior change**, not a proof that the old behavior passed.

### Tamper limits

- Without a host-held HMAC key, a database writer who can recompute every event and row digest can forge an entire unkeyed history. The row seals **do not prevent this**.
- An optional `audit_key` (at least 32 host-held secret bytes, never persisted to SQLite) signs subsequent audit events with HMAC-SHA256. The same key is required on reopen. Key custody, rotation, backup, and permissions are the host's responsibility.
- A full database rollback or deletion may look internally consistent. Store and check `audit_anchor()` results outside the database in an independent protected location; `integrity_report(expected_anchor=...)` detects a mismatch to a given external checkpoint. Automatic anchor persistence is **not implemented**.
- Existing *unsealed* pre-F databases cannot simply be treated as verified history. This implementation deliberately fails closed on old records. Any migration must authenticate original events and provenance under an owner-reviewed procedure; it must not backfill seals and present them as original independent evidence.
- Host identity, tenancy, delivery receipts, confidentiality, independent fact-verifier quality, HMAC key management, error recovery and real model accuracy remain outside this reference's proven guarantees.

## Evidence and evaluation boundary

- **Actual original source suite**: 440/440 deterministic tests passing.
- **Accountability/integration suite with actual source**: 167/167 deterministic tests passing; 9 of these directly require the owner ZIP and executed extracted V1 runtime. The 9 are skipped if the archive and runtime path are not supplied.
- **Synthetic host/mock protocol**: 24/24 status expectations pass with the *real inventory* attached, but the proposals are scripted. This is **not** a measure of social reasoning accuracy or reliable LLM correction.
- **Live Ollama/model-in-loop**: NOT RUN; must be executed with a running model and independently reviewed held-out cases.
- **Real human testimony**: None collected for tests; fixtures are synthetic.
- **Original 120-item Version 1 requirements plan**: Not comprehensively discharged by this narrow adapter. No claim of Version 1 product completion.

Owner approval for deployment, licensing, source publication, or Project-AI integration is **not inferred** from this research handoff.
