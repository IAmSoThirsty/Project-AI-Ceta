# Security, validity, and trust boundaries

## What is enforced in this package

- Statement contents are captured as original UTF-8 bytes and SHA-256 digests; quote proposals must match a Unicode span exactly; original bytes are rechecked when retrieved.
- Model JSON is bounded and strictly parsed (duplicate key/NaN/unknown top-level fields rejected). Its labels and annotations remain **untrusted proposals**.
- Verifiers must be registered by the trusted host, carry independent-group identities and source locators, and return structured findings. Retrieved text never becomes operating instructions.
- Only deterministic `GovernedTruthCore.render` produces unqualified supported factual statements. If a host appends free-form model text, the safeguard is bypassed.
- Prior-delivery acknowledgements require host-delivery records. `reconcile_historical_delivery` must be called only after the host validates a genuine, previously published assistant transcript and receipt.
- Source-speaker meaning corrections and factual checks are separate, with role and type gates; corrections invalidate dependent conclusions transitively.
- Unrecognized anomalies persist rather than being forced into classifications. Pattern repetition creates **research candidates**, not discoveries.

## Not provided: do not mistake these for demonstrated guarantees

1. **Authentication or tenant isolation**. `AuthenticatedActor` has a role field, not cryptographic proof. The host must derive roles and identities from authenticated sessions. Untrusted callers may not instantiate or select privileged actors in a privileged process.
2. **Verifier independence and factual accuracy**. Independence groups are registered metadata, not a proof that data sources are independently generated. Quality, source calibration, correlation, conflicts of interest, evidence validity and replication all need external assessment.
3. **General semantic understanding**. Lexical risk warnings only catch examples of drift; silence from the checker is never a semantic PASS. Sarcasm, emotion, context, identity, implied language and subtle scope differences require evaluation and often the original speaker.
4. **Dictionary truth lookup**. `resolve_dictionary_sense` stores a selected sense and a source locator; it checks that a claimed Merriam-Webster link is syntactically on the official HTTPS domain, but does not fetch or verify the definition's accuracy, sense numbering, edition, or current applicability. A trusted host must check the actual entry; a specialized technical glossary must be scoped to its domain.
5. **Proof against malicious database operators**. A local SHA-256 hash chain detects ordinary modifications and corruption, but an attacker with write access can replace the database and recalculate the chain. For tamper resistance, use off-database anchored signed checkpoints, verified replay, secured keys, proper atomic backup and access control.
6. **Privacy/retention policy**. Exact personal statements are intentionally preserved; encryption-at-rest, consent, permissioned retrieval, key rotation, retention, legal deletion, and redaction require product decisions. Do not collect real personal data in this demo.
7. **Audited fact checkers**. Bounded integer arithmetic is a real computation for a tiny grammar, not a general truth engine. Unit-test fixture providers are not real sources of independent world knowledge.
8. **Transport guarantees**. Local Ollama transport is opt-in, loopback-only and disables redirects by default; model availability and actual generated model behavior were not tested in this environment.
9. **No public release or Project-AI integration**. No GitHub project or Project-AI executable path was changed. Increment F **did** read and test the owner-supplied Version 1 corpus and source APIs as a separate local adapter; the original archive was not edited or republished.
10. **Immutable conclusions**. Historical fact and interpretation corrections permanently withdraw the original record. Revised claims need new IDs and their own evidence; expiration and contradictory evidence can also downgrade current status without asserting the previous answer was conclusively wrong.

## Host integration rules

Host MUST NOT expose: `VerificationRegistry.register`, `AuthenticatedActor` creation, `review_meaning`, `clarify_attribution`, `correct_fact`, `confirm_delivery`, `reconcile_historical_delivery`, `resolve_dictionary_sense`, raw SQL, or evidence status setters to an untrusted model. It should present the model only a **propose** capability, with a constrained current source ID. The trusted host selects verifiers, enforces its own authority, and owns rendering and delivery receipts. High-risk deployment requires stronger controls than this reference.

## Increment F: stronger ledger integrity (2026-10-18)

The earlier event-only SHA-256 verification did not cover all decision-critical SQLite fields. Four reproducible problems were identified by an independent local review. The repaired gate now appends a fingerprint for every newly created row to the linked audit event, refuses unsealed/changed/deleted/injected rows, and invokes integrity checks before decision use and each authorized write. It also checks the acknowledgment, perspective comparison and research queue display paths.

**Threat limit:** This catches ordinary corruption and raw SQL modification where the attacker does not also reconstruct a valid event chain. It is **not** an authenticated external signature in unkeyed mode. Configure `GovernedTruthCore(..., audit_key=<host-secret-at-least-32-bytes>)` for HMAC-linked events, store the key independently, and persist `audit_anchor()` results in a separately protected append-only location. Compare the externally retained checkpoint with `integrity_report(expected_anchor=anchor)` before relying on evidence. Rotation, independent checkpoint transport, old-ledger migration and backup anti-rollback are **not** included.

**Backward compatibility:** Existing A–E SQLite DBs have unsealed historical events. New code correctly rejects them rather than labeling unobserved past records authenticated. Reconcile through a source-backed, authorized migration process; do not silently sign retroactive rows.

**Model bridge:** unreviewed hypotheses are withheld by default, regardless of their wording or whether a weak lexical person-motive filter recognizes them. Any host release callback must be authenticated and evaluate the proposed hypothesis's scope/evidence. Rendering an unreviewed raw `GovernedTruthCore` hypothesis without the bridge remains an unsafe integration bypass. Use only the canonical host-controlled pipeline.
