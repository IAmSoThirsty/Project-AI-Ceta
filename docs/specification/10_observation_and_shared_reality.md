# Observation and shared reality

**Document ID:** SPEC-10  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-10-01

Implement typed adapters for selected files, repository state, tool results, task events, runtime health, configuration, and resources. Establish access before reading. Record observer, resource identity/revision, time, scope, completeness, and validation. A filesystem notification is a hint, not proof of new contents. A process output is evidence of text, not proof of its semantic effect.

### REQ-10-02

Handle duplicates, lost notifications, reorderings, atomic-save renames, replacement, deletion, pauses, and storms. Coalesce hints without losing authoritative changes. Reconcile authorized resources through bounded scans. Time, size, permission, or resource limits require an incomplete observation status rather than a claim of full knowledge.

### REQ-10-03

Preserve recording time, observation time, applicability time, and invalidation. Use claim-specific freshness, not universal expiry guesses. Changed files, revoked sources, stale results, or invalid dependencies must invalidate affected plans and capabilities. Do not invalidate everything for an unrelated event without cause.

### REQ-10-04

Expose what is happening, last verified, inferred, unknown, changed, or awaiting action. Connect every operational statement to actual records. The model must not fill gaps with a plausible narrative. Partial observation remains partial through planning and authorization.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B017, B020, B024, B044. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
