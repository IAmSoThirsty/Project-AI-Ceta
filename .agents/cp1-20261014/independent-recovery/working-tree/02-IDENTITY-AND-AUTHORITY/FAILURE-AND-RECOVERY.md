# 02-IDENTITY-AND-AUTHORITY - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-02.01.01 / principal-registry](02.01-PRINCIPAL-IDENTITY/principal-registry.file.README.md) | Display-name equality merges two distinct principals. |
| [CETA-02.01.02 / identity-proof-verifier](02.01-PRINCIPAL-IDENTITY/identity-proof-verifier.file.README.md) | A captured proof is replayed against another audience or challenge. |
| [CETA-02.01.03 / identity-binding-controller](02.01-PRINCIPAL-IDENTITY/identity-binding-controller.file.README.md) | A reused process identifier inherits another process's authority. |
| [CETA-02.02.01 / authenticated-session-manager](02.02-SESSION-AUTHORITY/authenticated-session-manager.file.README.md) | A restored conversation record is treated as an authenticated session. |
| [CETA-02.02.02 / session-scope-validator](02.02-SESSION-AUTHORITY/session-scope-validator.file.README.md) | A request includes a second resource outside the session grant. |
| [CETA-02.02.03 / session-expiration-controller](02.02-SESSION-AUTHORITY/session-expiration-controller.file.README.md) | Clock rollback extends a previously expired session. |
| [CETA-02.03.01 / capability-token-issuer](02.03-CAPABILITY-TOKENS/capability-token-issuer.file.README.md) | A caller requests token issuance without a matching governance decision. |
| [CETA-02.03.02 / capability-token-validator](02.03-CAPABILITY-TOKENS/capability-token-validator.file.README.md) | A signature-valid token has been revoked and is still accepted from cache. |
| [CETA-02.03.03 / capability-scope-evaluator](02.03-CAPABILITY-TOKENS/capability-scope-evaluator.file.README.md) | A directory link redirects an approved path into an unauthorized location. |
| [CETA-02.04.01 / delegation-graph](02.04-DELEGATED-AUTHORITY/delegation-graph.file.README.md) | A delegation edge creates a cycle or implicitly unions unrelated grants. |
| [CETA-02.04.02 / delegation-boundary-checker](02.04-DELEGATED-AUTHORITY/delegation-boundary-checker.file.README.md) | A delegate grants write permission from a read-only parent. |
| [CETA-02.04.03 / authority-revocation-controller](02.04-DELEGATED-AUTHORITY/authority-revocation-controller.file.README.md) | A revocation race is hidden by reporting the entire operation as cancelled despite committed effects. |
| [CETA-02.05.01 / owner-recovery-controller](02.05-AUTHORITY-RECOVERY/owner-recovery-controller.file.README.md) | Possession of a copied data directory alone authorizes owner takeover. |
| [CETA-02.05.02 / authority-rotation-manager](02.05-AUTHORITY-RECOVERY/authority-rotation-manager.file.README.md) | A retired key continues issuing new capabilities. |
| [CETA-02.05.03 / authority-integrity-verifier](02.05-AUTHORITY-RECOVERY/authority-integrity-verifier.file.README.md) | A restored backup silently erases a later known revocation. |


## Mandatory response model

Validation and compatibility failures stop before privileged work. Authority failures deny the affected action and invalidate stale caches. Resource pressure preserves stop, evidence, and recovery capacity. A partial or uncertain effect is recorded explicitly. Missing evidence is not filled with narrative. Internal data writes use the canonical transaction owner; external actions have separately stated idempotency and compensation rules.

## Recovery sequence

1. Close new admission for the affected scope while preserving safe inspection.
2. Capture the last durable state, exact inputs, observed effects, process or target identity, and evidence gaps.
3. Inspect actual resources and receipts to distinguish committed, absent-confirmed, and uncertain effects.
4. Select safe continuation, authorized compensation, restoration, or a human decision using current authority.
5. Preserve later known revocations, deletion markers, corrections, identity records, conversations, and unsent drafts.
6. Requalify the repaired path and record a recovery report before reopening normal effects.

## Retry and compensation

Safe reads may be retried within the same bounded task. Confirmed idempotent operations preserve their operation key and current authority. Unknown outcomes require reconciliation first. Compensation is a new effect with its own scope and can fail; never describe an irreversible external action as undone because local state changed. For pure analysis and UI units, restart computation or presentation from pinned sources without replaying actions.

## Verification

Inject interruption, stale state, malformed input, resource exhaustion, and lost observations at meaningful boundaries for the units above. A recovery claim requires actual before and after observations and source-bound test records. See [the test matrix](TEST-MATRIX.md).
