# Migration and coherent cutover

**Document ID:** SPEC-31  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-31-01

Implement migration separately for every supported discovered schema. Inventory legacy source, data, archives, identity, settings, tasks, uncertainty, model catalogs, and training artifacts. Preserve original IDs, hashes, bytes where relevant, and mappings. Conversion cannot claim the new runtime performed historical actions.

### REQ-31-02

Run dry imports against verified snapshots. Validate records by category, not just total counts. Keep unknown/unsupported material in a navigable provenance-preserving quarantine/archive. Corruption is explicit, never silently skipped. Missing documents or keys cannot be reconstructed from conversational guesses.

### REQ-31-03

Create new-store genesis referencing legacy evidence. Old grants remain historical; issue new positive authority explicitly. Carry unresolved effects forward until reconciled. Remeasure model/hardware readiness against the new executable. Never transfer green status without fresh qualification.

### REQ-31-04

Cutover requires quiesced writers, backup verification, rehearsal, restoration plan, and explicit approval to replace normal data or installation. Use robust atomic activation and health checks. Retain the prior compatible executable and data snapshot under policy. An older executable must never open an incompatible newer database.

### REQ-31-05

Retire old live entry points after cutover while preserving source/history/migration readers. Verify shortcuts, services, environment variables, model endpoints, and helpers cannot revive the old authority path. There must be one active interpretation of state and permissions, with historical code available only as history or a bounded migration boundary.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B105, B106, B107, B108, B109, B110, B111, B112. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
