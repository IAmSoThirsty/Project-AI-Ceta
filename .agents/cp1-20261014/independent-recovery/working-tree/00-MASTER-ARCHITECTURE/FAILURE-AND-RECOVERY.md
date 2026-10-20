# 00-MASTER-ARCHITECTURE - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-00.01.01 / product-identity](00.01-PRODUCT-IDENTITY/product-identity.file.README.md) | A design revision is presented as an installed application version and must be rejected. |
| [CETA-00.01.02 / architecture-invariants](00.01-PRODUCT-IDENTITY/architecture-invariants.file.README.md) | Two subsystems claim final authority for the same invariant and the conflict is reported. |
| [CETA-00.02.01 / subsystem-registry](00.02-SYSTEM-TOPOLOGY/subsystem-registry.file.README.md) | Duplicate subsystem identities fail registration without overwriting the first entry. |
| [CETA-00.02.02 / component-ownership-map](00.02-SYSTEM-TOPOLOGY/component-ownership-map.file.README.md) | Concurrent agents attempt to acquire the same write lease and only one succeeds. |
| [CETA-00.02.03 / architecture-graph](00.02-SYSTEM-TOPOLOGY/architecture-graph.file.README.md) | A build cycle returns its complete path instead of silently dropping an edge. |
| [CETA-00.03.01 / application-bootstrap](00.03-RUNTIME-LIFECYCLE/application-bootstrap.file.README.md) | Missing trust material opens maintenance diagnostics while all effectful dispatch remains closed. |
| [CETA-00.03.02 / lifecycle-coordinator](00.03-RUNTIME-LIFECYCLE/lifecycle-coordinator.file.README.md) | A restarted component reuses a stale readiness generation and cannot receive work. |
| [CETA-00.03.03 / shutdown-coordinator](00.03-RUNTIME-LIFECYCLE/shutdown-coordinator.file.README.md) | A worker exceeds the shutdown deadline and its unfinished effect is recorded as uncertain. |
| [CETA-00.04.01 / existing-component-inspector](00.04-INTEGRATION-BASELINE/existing-component-inspector.file.README.md) | A selected path escapes through a directory link and is excluded with an explained boundary finding. |
| [CETA-00.04.02 / compatibility-mapper](00.04-INTEGRATION-BASELINE/compatibility-mapper.file.README.md) | A similarly named component with incompatible semantics is marked for reconciliation rather than assumed compatible. |
| [CETA-00.04.03 / integration-conflict-detector](00.04-INTEGRATION-BASELINE/integration-conflict-detector.file.README.md) | A conflict is marked resolved without a signed-off decision and supporting test evidence. |
| [CETA-00.05.01 / dependency-validator](00.05-ARCHITECTURE-ASSURANCE/dependency-validator.file.README.md) | An optional connected interface is required to start an offline-only deployment. |
| [CETA-00.05.02 / architectural-invariant-checker](00.05-ARCHITECTURE-ASSURANCE/architectural-invariant-checker.file.README.md) | An unexecuted runtime assertion is promoted to passed by an empty result set. |
| [CETA-00.05.03 / contract-ownership-validator](00.05-ARCHITECTURE-ASSURANCE/contract-ownership-validator.file.README.md) | A consumer silently widens a capability field without a canonical amendment. |


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
