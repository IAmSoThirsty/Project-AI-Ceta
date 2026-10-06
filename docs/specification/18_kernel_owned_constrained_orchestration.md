# Kernel-owned constrained orchestration

**Document ID:** SPEC-18  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-18-01

Compile typed graphs for multi-step work, preserving execution dependency, communication, review, authorization, and evidence as different relations. Unknown edge types fail. Define source discovery, explicit overrides, bounded parsing, directory scope, duplicate handling, references, cycles, and fingerprinting. Repository instructions can constrain a task or propose a graph but cannot expand the owner/install authority ceiling.

### REQ-18-02

Pin graph snapshots separately from live state, using the canonical kernel store for events, leases, claims, receipts, and transitions. Standalone historical state.json or JSONL writers do not become rival production authorities. Compute READY from actual prerequisites. Models request claims or submit results; they cannot set SUCCEEDED or bypass validation.

### REQ-18-03

Acquire claims atomically with executor identity, capacity, scope, lease/fencing generation, graph fingerprint, and input revision. One node has one active owner. Admit concurrent reads and provably disjoint writes within budgets; serialize ambiguous scope. Prevent dangerous out-of-scope access before effects, not merely through final diff rejection.

### REQ-18-04

Verify receipts against run, node, executor, inputs, artifacts, observed outputs, scope, and required validations. Enforce no-self-review where required. Propagate stale approvals and failed dependencies. Existing runs remain pinned or migrate explicitly to a new graph. Agent messaging is a bounded data channel, not authority transfer by prose.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B049, B050, B051, B052, B053, B054, B055, B056. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
