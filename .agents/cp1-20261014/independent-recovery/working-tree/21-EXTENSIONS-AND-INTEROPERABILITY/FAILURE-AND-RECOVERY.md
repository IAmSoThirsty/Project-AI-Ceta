# 21-EXTENSIONS-AND-INTEROPERABILITY - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-21.01.01 / extension-manifest-schema](21.01-EXTENSION-MANIFESTS/extension-manifest-schema.file.README.md) | An extension hides privileged startup actions outside its manifest. |
| [CETA-21.01.02 / extension-contract-validator](21.01-EXTENSION-MANIFESTS/extension-contract-validator.file.README.md) | An extension-specific schema bypasses required authority fields. |
| [CETA-21.01.03 / extension-dependency-resolver](21.01-EXTENSION-MANIFESTS/extension-dependency-resolver.file.README.md) | Resolving one extension silently installs another privileged component. |
| [CETA-21.02.01 / extension-installation-controller](21.02-EXTENSION-LIFECYCLE/extension-installation-controller.file.README.md) | Installation executes arbitrary hooks before authority review. |
| [CETA-21.02.02 / extension-version-manager](21.02-EXTENSION-LIFECYCLE/extension-version-manager.file.README.md) | A mutable latest-version label replaces the reviewed artifact silently. |
| [CETA-21.02.03 / extension-revocation-controller](21.02-EXTENSION-LIFECYCLE/extension-revocation-controller.file.README.md) | Uninstall deletes shared user data without an approved retention decision. |
| [CETA-21.03.01 / external-capability-adapter](21.03-INTEROPERABILITY-CONTRACTS/external-capability-adapter.file.README.md) | A remote capability claims broader authority than the owner's local grant. |
| [CETA-21.03.02 / interprocess-message-adapter](21.03-INTEROPERABILITY-CONTRACTS/interprocess-message-adapter.file.README.md) | Another local process invokes privileged commands by knowing the IPC endpoint name. |
| [CETA-21.03.03 / protocol-compatibility-validator](21.03-INTEROPERABILITY-CONTRACTS/protocol-compatibility-validator.file.README.md) | A peer lacks cancellation or scope enforcement but is treated as fully compatible. |
| [CETA-21.04.01 / extension-authority-controller](21.04-EXTENSION-SECURITY/extension-authority-controller.file.README.md) | Installing an extension gives it the owner's full session authority. |
| [CETA-21.04.02 / extension-isolation-controller](21.04-EXTENSION-SECURITY/extension-isolation-controller.file.README.md) | A missing isolation backend falls back to unrestricted in-process execution. |
| [CETA-21.04.03 / extension-integrity-verifier](21.04-EXTENSION-SECURITY/extension-integrity-verifier.file.README.md) | A trusted manifest is accepted while its referenced artifact bytes changed. |
| [CETA-21.05.01 / extension-template-generator](21.05-NATIVE-EXTENSION-KIT/extension-template-generator.file.README.md) | A convenience template embeds production secrets or bypass permissions. |
| [CETA-21.05.02 / extension-test-harness](21.05-NATIVE-EXTENSION-KIT/extension-test-harness.file.README.md) | A harness tests only successful invocation and ignores authority boundaries. |
| [CETA-21.05.03 / extension-documentation-builder](21.05-NATIVE-EXTENSION-KIT/extension-documentation-builder.file.README.md) | Generated documentation labels an unqualified feature as available. |
| [CETA-21.06.01 / extension-catalog-registry](21.06-EXTENSION-CATALOG/extension-catalog-registry.file.README.md) | A catalog entry changes its artifact behind an unchanged reviewed identifier. |
| [CETA-21.06.02 / extension-compatibility-evaluator](21.06-EXTENSION-CATALOG/extension-compatibility-evaluator.file.README.md) | A missing mandatory host capability is hidden by a broad compatibility label. |
| [CETA-21.06.03 / extension-review-controller](21.06-EXTENSION-CATALOG/extension-review-controller.file.README.md) | A favorable catalog description substitutes for qualification evidence. |


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
