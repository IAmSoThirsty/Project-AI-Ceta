# 18-SECURITY-AND-ENFORCEMENT - architecture

## Responsibility

Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity.

## Required invariant

Risk scores support decisions but cannot grant authority. Cryptographic operations use reconciled, established implementations and explicit threat models.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [18.01 Cryptographic Identity](18.01-CRYPTOGRAPHIC-IDENTITY/README.md) | key_id:text; algorithm:text; protected_handle:reference; device_binding:reference; rotation_generation:integer | Create or import authorized protected keys; bind intended uses and devices; sign or verify through handles; rotate with historical trust records; revoke compromised material. |
| [18.02 Secret Protection](18.02-SECRET-PROTECTION/README.md) | secret_id:text; encrypted_record:reference; access_scope:record; lease_expiry:timestamp; rotation_ref:reference | Store secrets under authenticated encryption through qualified facilities; issue short-lived scoped access; prevent context and log leakage; rotate and invalidate old references. |
| [18.03 Security Policy](18.03-SECURITY-POLICY/README.md) | boundary_id:text; protected_resource:record; required_control:enum; policy_generation:integer; enforcement_ref:reference | Define protected boundaries and controls; evaluate requests against the active policy; install qualified enforcement; verify actual activation before admitting effects. |
| [18.04 Risk And Anomaly](18.04-RISK-AND-ANOMALY/README.md) | observation_id:text; baseline_revision:text; anomaly_score:bounded-number; rationale_refs:list; response_class:enum | Collect authorized telemetry; compare against scoped baselines and explicit rules; classify anomalies; request or trigger only preauthorized responses; retain explainable evidence. |
| [18.05 Incident Response](18.05-INCIDENT-RESPONSE/README.md) | incident_id:text; affected_scope:record; containment_state:enum; evidence_hold:reference; recovery_decision:reference | Open an incident; preserve relevant evidence; apply authorized containment; assess scope; repair and requalify; reopen effects only after verified recovery. |
| [18.06 Security Assurance](18.06-SECURITY-ASSURANCE/README.md) | assessment_id:text; dependency_manifest:reference; trust_chain:reference; findings:list; verification_ref:reference | Inspect dependency and trust integrity; run boundary-focused checks; assemble evidence; classify open findings; gate release according to explicit acceptance rules. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
