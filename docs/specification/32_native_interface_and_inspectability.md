# Native interface and inspectability

**Document ID:** SPEC-32  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-32-01

Organize a coherent native experience around conversation, current work, approvals/actions, memory/evidence, models/resources, and recovery/settings. Preserve useful familiarity without preserving duplicate concepts. Users should start work without editing configuration or typing tags. Every enabled control calls a real use case and renders actual state.

### REQ-32-02

First launch shows storage, models, licenses, disk/memory, observation scope, and separate external-access choices. Support install/import, inspect/test, skip, pause/retry, and model-free use. Preferences can survive restart; current readiness cannot be restored merely from a saved flag. Show liveness, quality, and responsiveness separately.

### REQ-32-03

Expose objective, current phase, pending authority, observed context, last verified action, blockers, and consequential uncertainty. Link explanations to evidence/version. Keep audit details inspectable without flooding conversation. Warnings state what is blocked, why, what remains usable, and the smallest safe resolution.

### REQ-32-04

Support keyboard use, accessible names, screen-reader order, scaling, contrast, focus, and long paths. Never encode trust solely by color. Keep setup, hashing, loading, search, and migration off the UI thread as appropriate. Test drafts, double clicks, stale approvals, late callbacks, restarts, and multiple windows.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B026, B113, B114, B115, B116, B119. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
