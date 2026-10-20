# 21-EXTENSIONS-AND-INTEROPERABILITY - architecture

## Responsibility

Enable optional native extensions and generic interoperability through versioned contracts, qualification, scoped authority, and isolated lifecycle management.

## Required invariant

Extensions are optional untrusted components until qualified. Installation, discovery, and compatibility do not grant execution authority.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [21.01 Extension Manifests](21.01-EXTENSION-MANIFESTS/README.md) | extension_id:text; version:text; artifact_digest:digest; exports:list; required_effects:list; compatibility:record | Define extension content and interfaces; validate manifest and dependencies; inspect required effects; stage qualification before activation. |
| [21.02 Extension Lifecycle](21.02-EXTENSION-LIFECYCLE/README.md) | installation_id:text; staged_revision:reference; active_revision:reference; lifecycle_state:enum; rollback_ref:reference | Stage verified artifacts; qualify in isolation; request activation; switch revisions atomically; revoke or uninstall with data and authority cleanup. |
| [21.03 Interoperability Contracts](21.03-INTEROPERABILITY-CONTRACTS/README.md) | peer_id:text; protocol_revision:text; schema_digest:digest; authenticated_channel:reference; capability_scope:reference | Negotiate compatible schemas; authenticate the peer; translate only declared semantics; enforce scope and message limits; reject incompatible or ambiguous operations. |
| [21.04 Extension Security](21.04-EXTENSION-SECURITY/README.md) | extension_principal:reference; granted_scope:record; isolation_ref:reference; integrity_generation:integer; revocation_ref:reference | Assign an extension principal; grant minimum capabilities; launch in qualified isolation; verify code integrity; monitor and revoke on boundary failure. |
| [21.05 Native Extension Kit](21.05-NATIVE-EXTENSION-KIT/README.md) | template_revision:text; contract_set:references; fixture_set:reference; documentation_manifest:reference | Provide native extension construction guidance and contract fixtures; generate only owner-requested templates in the future implementation; qualify extensions against the same runtime rules. |
| [21.06 Extension Catalog](21.06-EXTENSION-CATALOG/README.md) | catalog_entry:text; artifact_revision:reference; review_status:enum; compatibility_refs:list; distribution_scope:reference | Index inspectable extension metadata; verify integrity and review state; filter compatibility; present approval requirements; keep acquisition and activation separate. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
