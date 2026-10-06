# Blockers and final handoff

**Document ID:** SPEC-42  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-42-01

Blocker records state ID, requirement, observed cause, evidence, impact, minimum resource/decision, dependencies, and safe continuing work. Missing access, secure hardware, enforcement support, independent review, quality, or elapsed duration must be represented accurately. Difficulty is not a blocker by itself. Relevant historical defects cannot be dismissed as merely pre-existing.

### REQ-42-02

Before delivery, attack bypasses, duplicate authority, false independence, loops, fake completion, migration loss, hidden egress, invalid security claims, dead controls, stale evidence, and unusable commands. Repair within scope and rerun affected gates. Preserve recoverability. Improve the evidence rather than the adjective attached to status.

### REQ-42-03

Final report fields: Mode; Baseline; Architecture decisions; Created; Modified; Retired production paths; Preserved history; Migration result; Commands executed; Tests passed; Failed; Skipped; Not run; Independent review; Hardware evidence; Installed qualification; Endurance; Remaining mandatory work; Risks; Artifact paths/hashes; Continuity; Safe to continue. State exactly what the installed result enables. Begin with workspace inspection and implementation, not another request to plan this same rebuild.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B001, B008, B111, B128. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
