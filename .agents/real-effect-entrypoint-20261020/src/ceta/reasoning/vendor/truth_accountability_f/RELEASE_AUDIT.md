# Increment F — evidence-bounded local release audit

**Date:** 2026-10-18. **Purpose:** Reproduce original Societal Reasoning Core Version 1 source and add host-bound A–F reference adapter with independent defect repair. **Status:** LOCAL REFERENCE CANDIDATE, NOT PRODUCTION OR PUBLIC RELEASE AUTHORIZATION.

## Exact original source

- Input user-supplied ZIP SHA-256: `b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5`.
- Archive: 109 files; source release verifier `SOURCE_PACKAGE_VERIFIED_NOT_FACTUALLY_CERTIFIED` with 109 file checks, 2,000 contiguous entries, 1,000 per volume, no missing IDs.
- Original `PYTHONPATH=src python -m unittest discover -s tests -q`: **440 tests OK**.
- Original `python scripts/compile_inventory.py` verification: no conflicts and 2,000 included.
- Extracted original Python runtime: `__version__="1"`; actual `assess_text` and `review_draft` exercised in real-source integration tests. No source file changed.

## Separate Increment F reference checks

- `python -m unittest discover -s tests -q` with correct `SOCIETAL_V1_SOURCE`, `SOCIETAL_V1_ROOT`, and `PYTHONPATH` env vars: **167 tests OK**; includes 9 genuine-source integration cases, 13 new hostile integrity regressions, and retained / amended A–E tests.
- `python evaluate_model.py --backend mock ... --source ... --mapping ...`: **24/24** scripted status-matching checks, 21 with a source-linked contextual candidate. **NOT real model behavior**.
- `python demo_real_version1.py --archive ... --runtime-root ...`: **PASS**; byte-matched 109 source files, 2,000 records, real API schema and source preservation, fabricated attribution withheld.
- Against the four previously reproduced defects, tests now detect evidence-verdict drift, policy drift, correction deletion, and unreviewed person-intent speculation.
- The final release builder must be run after all documentation and tests are frozen; archive CRC, member digests, clean extraction and byte-for-byte reproducibility are recorded in `RELEASE_BUILD_RECEIPT.json` outside this project tree.

## Boundaries and known deficiencies

- The hash-linked local ledger has **no independent trust anchor unless the host provides one**, and an unkeyed hash chain is forgeable by a sufficiently privileged database writer.
- HMAC audit mode is optional; key management and protected external anchoring are product-level requirements, not implemented operational services.
- No license/redistribution decision made for the original Societal Reasoning Core; this package does **not** bundle its source archive. The original README's all-rights-reserved boundary is preserved.
- The 167 deterministic tests and 24 mock tests do not demonstrate statistical generalization, live LLM truthfulness or external social-fact verification.
- The original Version 1 corpus was manually source-transcribed: source integrity does not independently authenticate its historical original statements or societal truth claims.
- The host callback may still incorrectly approve a hypothesis; appropriate evidence and human review are necessary.
- Version 1's `review_draft` has known lexical false positives/negatives. It identified a possible modality issue in a quote; source-bound advisory `pass` must never be upgraded to proof of semantic correctness.
- Existing pre-F ledger databases are **not migrated**, and old events without row seals intentionally fail closed. There is no backward-compatible trust upgrade for those event histories.
- No GitHub push, deployment, Project-AI integration, live Ollama evaluation, independent third-party review, or owner-release authorization occurred.

## Next gates

1. Set up authenticated independent external checkpointing and protected audit secrets; test backup, rollback and recovery.
2. Test actual local model proposals against blinded human-rated held-out cases, including non-English, cross-cultural and adversarial paraphrase families.
3. Distinguish true ambiguity from quote false positives; audit real error-correction output and consistency across sessions.
4. Obtain rights and production authorization decisions before any public release or host integration.

See `docs/VERSION1_BINDING_AND_EVALUATION.md`, `docs/SECURITY.md` and `CONTINUITY_MAP.md` for exact procedures and qualified claims.
