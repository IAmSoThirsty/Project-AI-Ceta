# 17-EVIDENCE-AND-PROVENANCE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-17.01.01 / execution-evidence-collector](17.01-EVIDENCE-CAPTURE/execution-evidence-collector.file.README.md) | Missing monitor events are silently ignored while completion is declared verified. |
| [CETA-17.01.02 / input-output-recorder](17.01-EVIDENCE-CAPTURE/input-output-recorder.file.README.md) | Normalized output overwrites contradictory raw evidence. |
| [CETA-17.01.03 / evidence-artifact-register](17.01-EVIDENCE-CAPTURE/evidence-artifact-register.file.README.md) | A path is reused for new content while retaining the earlier artifact identity. |
| [CETA-17.02.01 / artifact-digest-generator](17.02-CRYPTOGRAPHIC-INTEGRITY/artifact-digest-generator.file.README.md) | Different serialization order produces ambiguous signed content without a canonical rule. |
| [CETA-17.02.02 / evidence-signature-controller](17.02-CRYPTOGRAPHIC-INTEGRITY/evidence-signature-controller.file.README.md) | A signature for another message type is accepted as an execution receipt. |
| [CETA-17.02.03 / cryptographic-verification-engine](17.02-CRYPTOGRAPHIC-INTEGRITY/cryptographic-verification-engine.file.README.md) | A valid signature from an untrusted key is reported as trusted proof. |
| [CETA-17.03.01 / provenance-relationship-builder](17.03-PROVENANCE-GRAPHS/provenance-relationship-builder.file.README.md) | A verified-by link is created before any verification result exists. |
| [CETA-17.03.02 / evidence-lineage-index](17.03-PROVENANCE-GRAPHS/evidence-lineage-index.file.README.md) | A cached graph leaks the names of restricted evidence artifacts. |
| [CETA-17.03.03 / provenance-chain-validator](17.03-PROVENANCE-GRAPHS/provenance-chain-validator.file.README.md) | A valid internal chain is claimed to prove no earlier records were removed without an independent anchor. |
| [CETA-17.04.01 / evidence-frame-constructor](17.04-IMMUTABLE-FRAMES/evidence-frame-constructor.file.README.md) | An artifact changes after frame construction but before sealing without invalidation. |
| [CETA-17.04.02 / evidence-frame-sealer](17.04-IMMUTABLE-FRAMES/evidence-frame-sealer.file.README.md) | A writable local file is described as impossible to alter simply because it is hashed. |
| [CETA-17.04.03 / evidence-frame-verifier](17.04-IMMUTABLE-FRAMES/evidence-frame-verifier.file.README.md) | An unanchored shortened chain is reported as demonstrably complete. |
| [CETA-17.05.01 / deterministic-replay-controller](17.05-REPLAY-AND-VERIFICATION/deterministic-replay-controller.file.README.md) | A replay resends an email or repeats a file deletion to recreate history. |
| [CETA-17.05.02 / independent-result-verifier](17.05-REPLAY-AND-VERIFICATION/independent-result-verifier.file.README.md) | The verifier approves solely by reading the builder's completion summary. |
| [CETA-17.05.03 / evidence-gap-detector](17.05-REPLAY-AND-VERIFICATION/evidence-gap-detector.file.README.md) | A gap is filled with a model-generated plausible event. |
| [CETA-17.06.01 / evidence-query-engine](17.06-EVIDENCE-ACCESS/evidence-query-engine.file.README.md) | A count or error message leaks restricted artifact identities. |
| [CETA-17.06.02 / evidence-report-builder](17.06-EVIDENCE-ACCESS/evidence-report-builder.file.README.md) | A signed failed execution is summarized as a successful operation. |
| [CETA-17.06.03 / evidence-export-controller](17.06-EVIDENCE-ACCESS/evidence-export-controller.file.README.md) | Export includes private inputs outside the approved evidence-sharing scope. |


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
