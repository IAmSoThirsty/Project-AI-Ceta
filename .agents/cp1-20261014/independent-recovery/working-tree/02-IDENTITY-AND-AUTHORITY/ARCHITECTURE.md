# 02-IDENTITY-AND-AUTHORITY - architecture

## Responsibility

Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities.

## Required invariant

Authority is explicit, bounded, attributable, and checked at use time. A model response or UI state is never an authentication proof.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [02.01 Principal Identity](02.01-PRINCIPAL-IDENTITY/README.md) | principal_id:text; principal_kind:enum; credential_ref:reference; binding_generation:integer; status:enum | Enroll a principal through an authorized process; verify credentials; bind device and process identities where required; rotate or revoke without losing attribution. |
| [02.02 Session Authority](02.02-SESSION-AUTHORITY/README.md) | session_id:text; principal_id:text; authentication_generation:integer; idle_deadline:timestamp; absolute_expiry:timestamp | Establish a session; calculate its permitted scope; refresh only through valid reauthentication; terminate and invalidate cached authority. |
| [02.03 Capability Tokens](02.03-CAPABILITY-TOKENS/README.md) | capability_id:text; subject_id:text; audience:text; scope:record; effect_digest:digest; expires_at:timestamp; revocation_generation:integer | Issue a capability from approved authority; bind exact scope and effect inputs; validate authenticity and current status; consume or revoke according to its usage rule. |
| [02.04 Delegated Authority](02.04-DELEGATED-AUTHORITY/README.md) | delegation_id:text; parent_ref:reference; child_principal:text; scope_subset:record; depth:integer; revocation_ref:reference | Construct a bounded delegation graph; verify parent-child attenuation; propagate revocation; reevaluate dependent work at admission and effect boundaries. |
| [02.05 Authority Recovery](02.05-AUTHORITY-RECOVERY/README.md) | recovery_request:text; recovery_policy_ref:reference; challenge_ref:reference; rotation_generation:integer; audit_ref:reference | Enter a restricted recovery flow; verify configured recovery proofs; rotate affected authority; invalidate old credentials; test restored control before reopening effects. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
