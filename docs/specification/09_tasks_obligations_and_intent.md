# Tasks, obligations, and intent

**Document ID:** SPEC-09  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-09-01

A durable task preserves original wording, clarified meaning, scope, exclusions, completion predicates, assumptions, unresolved questions, standing instructions, authority, budgets, and evidence. Preserve raw input separately from interpretation. Objective changes create explicit versions and invalidate affected plans or permits. New instructions must not silently rewrite an earlier request.

### REQ-09-02

Provide conversation, investigation, coding, monitoring, and maintenance profiles within one system. Ordinary conversation must not inherit coding-only output instructions or internal metadata. Project work receives applicable project context. An unresolved question can remain open without an endless loop. A status question must get status while pending actions respect the interaction pause contract.

### REQ-09-03

Standing grants bind purpose, resources, operations, duration, limits, triggers, notification, and revocation. Watching and preparing may be delegated while applying changes remains reserved. Renewal re-evaluates state and never revives a consumed permit. Budgets and expiry survive restart and cannot be expanded by clock manipulation.

### REQ-09-04

Treat promised checks, approvals, deferred research, expected results, and scheduled reviews as first-class obligations. Separate suggestions from accepted commitments. Never claim scheduling without runtime acceptance. Explain what is waiting, its dependencies, and any expired authority.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B022, B025, B027, B028, B064. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
