# Reconcile with the actual local CETA application

## Starting point

The owner stated that current CETA development is local and the existing working repository was not available for this package. No source inspection or implementation-state claim is implied. The logical architecture is approved; actual language bindings, module paths, storage schemas, native backends, and existing tests are established by local inspection during integration.

## Required inventory

Inspect only the selected local root and explicitly permitted related data locations. Identify entry points, processes, native IPC, models, tools, policy sources, identity and capability services, state stores, evidence records, UI routes, build configuration, tests, packaging, and recovery mechanisms. Capture exact source digests and inaccessible ranges. Include relevant uncommitted or locally generated source; remote hosting and source-control metadata are optional.

## Mapping decision

For every logical unit, record one of reuse, extend, create, or blocked-by-decision. Reuse requires observed behavior and evidence satisfying the specification. Extension preserves the current canonical owner and adds missing behavior. Creation requires a genuinely absent capability or an approved separate ownership boundary. Replacement requires explicit compatibility, migration, data preservation, rollback, and acceptance justification. Multiple logical units may map to one cohesive existing module, or one unit may require several idiomatic files; preserve all identities and coverage in the mapping.

## Required mapping fields

Record logical unit ID, logical source path, actual local path or paths, language and module, current source digest, canonical owner, existing interfaces, existing tests, reuse decision, required changes, contract compatibility, data migrations, reviewer, and evidence references. The package's initial mapping status is LOCAL-INSPECTION-REQUIRED, which is an honest input prerequisite rather than an empty implementation template.

## Constitutional and platform decisions

Load the actual owner-approved constitutional sources and reconciled language grammar. Do not invent rule text or replace the language because this package names a parser. Inspect the actual native enforcement capabilities and qualify the required effect restrictions on the target platform. Unsupported enforcement blocks the affected effect; it is not described as active. Pin cryptographic, storage, model-format, and transport profiles through explicit local decisions.

## Preserve and verify

Preserve conversations, identities, memory, unsent drafts, project files, evidence, known revocations, deletion markers, and existing acceptance obligations. Establish recovery points before migrations. Test real existing workflows before and after each integration change. Bind the final mapping and results to the exact delivered source and artifacts.
