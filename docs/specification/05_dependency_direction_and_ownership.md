# Dependency direction and ownership

**Document ID:** SPEC-05  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-05-01

Use this dependency direction: UI and optional local interfaces call application use cases; use cases request kernel operations; the kernel validates typed transitions and admits work; supervised adapters perform bounded work; independent observations return through evidence admission; projections serve authorized reads. Core contracts and serialization depend on no presentation, inference, unrestricted filesystem, network client, or test harness. Infrastructure implements interfaces declared by the core.

### REQ-05-02

Assign one authoritative owner for task state, identity status, effective authority, accepted policy, canonical commits, operation admission, and evidence identity within each scope. Graphs, conversation views, dashboards, search, notifications, and model context are projections or payload stores, never alternate permission issuers. A tool cannot call another tool to bypass admission. A UI cannot write success directly. A model cannot set readiness or verification flags.

### REQ-05-03

Authenticate local IPC with actual peer identity and process lifetime rather than a caller-supplied role. Bound message size, schema, deadlines, and replay. Localhost is not authentication. Expose no general SQL, shell, file, signing, or plugin-loading endpoint from the trusted kernel.

### REQ-05-04

Keep production dependencies acyclic apart from explicit runtime feedback through defined interfaces. Ban imports from retained legacy application modules into the new core. Move or adapt reusable algorithms into their new owner with attribution and tests. Temporary compatibility belongs only at import/export or provider boundaries, with an owner and removal criterion, never as parallel live authority.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B037, B063, B068. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
