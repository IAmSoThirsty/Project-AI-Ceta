# One executable system specification

**Document ID:** SPEC-04  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-04-01

Freeze a versioned contract for the complete target before building disconnected subsystems. Define actors, trust domains, authoritative state, events, external effects, authority issuance, policy, evidence, memory, request compilation, execution, verification, cancellation, recovery, migration, and release. Include authority and dependency maps with no hidden side channels. Every module must state what it owns, may request, may read, and may never decide for itself.

### REQ-04-02

Translate every source responsibility into the contract. Consolidate duplicated mechanisms while preserving distinct semantics. Classify each source capability as preserved, consolidated, rewritten, replaced by a named mechanism, historical-only, unresolved, or unavailable pending a stated prerequisite. No capability disappears because its name is inconvenient. No new service exists merely because a source names a role: roles, policies, records, processes, and hardware domains are different categories.

### REQ-04-03

Specify the whole cycle from observation to future retrieval, including lost observations, stale inputs, contradictions, denials, partial effects, missing outcomes, cancellation, crash, restore, and resumed interpretation. Model transitions and invariants before implementing each boundary. Version necessary contract amendments with their tests and migrations. Design choices must specify how they fail, not only how they succeed.

### REQ-04-04

The first end-to-end fixture must exercise all applicable governance boundaries together. Narrow the workspace and operations, not the integrity of the architecture. Construction gates do not justify deploying partial systems that bypass one another. Integration means a module's real result participates in the canonical cycle and its failure changes the legal next actions.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B055, B063, B128. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
