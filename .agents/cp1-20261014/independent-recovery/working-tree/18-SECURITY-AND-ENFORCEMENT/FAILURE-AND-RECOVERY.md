# 18-SECURITY-AND-ENFORCEMENT - failure and recovery

## Domain-specific failure fixtures

| Unit | Adverse condition that must be handled |
| --- | --- |
| [CETA-18.01.01 / cryptographic-key-manager](18.01-CRYPTOGRAPHIC-IDENTITY/cryptographic-key-manager.file.README.md) | A caller requests raw private-key export through an ordinary diagnostic interface. |
| [CETA-18.01.02 / device-trust-binding](18.01-CRYPTOGRAPHIC-IDENTITY/device-trust-binding.file.README.md) | Possession of a device label alone passes a hardware-binding check. |
| [CETA-18.01.03 / signature-trust-verifier](18.01-CRYPTOGRAPHIC-IDENTITY/signature-trust-verifier.file.README.md) | An unknown self-signed key is accepted as owner authority. |
| [CETA-18.02.01 / encrypted-secret-vault](18.02-SECRET-PROTECTION/encrypted-secret-vault.file.README.md) | Vault files and their decryption key are exported together through ordinary backup output. |
| [CETA-18.02.02 / secret-access-controller](18.02-SECRET-PROTECTION/secret-access-controller.file.README.md) | A general search or model prompt can retrieve raw vault contents. |
| [CETA-18.02.03 / secret-rotation-coordinator](18.02-SECRET-PROTECTION/secret-rotation-coordinator.file.README.md) | A failed rotation leaves both credentials active indefinitely without a recorded decision. |
| [CETA-18.03.01 / security-boundary-registry](18.03-SECURITY-POLICY/security-boundary-registry.file.README.md) | An extension gains ambient host access through an unregistered boundary. |
| [CETA-18.03.02 / security-policy-evaluator](18.03-SECURITY-POLICY/security-policy-evaluator.file.README.md) | A low risk score overrides a missing mandatory security control. |
| [CETA-18.03.03 / security-enforcement-adapter](18.03-SECURITY-POLICY/security-enforcement-adapter.file.README.md) | A configuration write is mistaken for proof that the control is enforced. |
| [CETA-18.04.01 / behavioral-anomaly-detector](18.04-RISK-AND-ANOMALY/behavioral-anomaly-detector.file.README.md) | An unusual but authorized action is automatically treated as malicious without review criteria. |
| [CETA-18.04.02 / execution-risk-evaluator](18.04-RISK-AND-ANOMALY/execution-risk-evaluator.file.README.md) | A low numeric score permits an otherwise unauthorized action. |
| [CETA-18.04.03 / security-alert-controller](18.04-RISK-AND-ANOMALY/security-alert-controller.file.README.md) | Alert flooding prevents delivery of a more severe incident. |
| [CETA-18.05.01 / incident-state-controller](18.05-INCIDENT-RESPONSE/incident-state-controller.file.README.md) | A service restart automatically closes a security incident without verification. |
| [CETA-18.05.02 / containment-response-engine](18.05-INCIDENT-RESPONSE/containment-response-engine.file.README.md) | Containment erases the only evidence needed to investigate the incident. |
| [CETA-18.05.03 / security-recovery-verifier](18.05-INCIDENT-RESPONSE/security-recovery-verifier.file.README.md) | The same unqualified configuration is restored because the interface appears healthy. |
| [CETA-18.06.01 / dependency-integrity-checker](18.06-SECURITY-ASSURANCE/dependency-integrity-checker.file.README.md) | Matching filenames substitute for checking actual dependency bytes. |
| [CETA-18.06.02 / security-audit-generator](18.06-SECURITY-ASSURANCE/security-audit-generator.file.README.md) | A checklist of intended controls is presented as a completed security audit. |
| [CETA-18.06.03 / trust-chain-validator](18.06-SECURITY-ASSURANCE/trust-chain-validator.file.README.md) | A chain is accepted solely because every individual signature is mathematically valid. |


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
