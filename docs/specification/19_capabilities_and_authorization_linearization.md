# Capabilities and authorization linearization

**Document ID:** SPEC-19  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-19-01

Separate durable standing grants from single-operation permits. Grants authorize bounded preparation or classes of action under conditions; each consequential effect still gets current exact admission. Bind permits to principal, scope, task, operation/adapter version, resources, revisions, argument commitment, candidate outputs where known, review/policy evidence, relevant state generation, deadline, budget, and environment. A caller-authored dictionary is not positive authority.

### REQ-19-02

Specify linearization points for admission and irreversible execution. Recheck authority, revocation generation, resource state, worker identity, and preconditions at the relevant point. A revocation that wins the race prevents admission; one after an irreversible effect stops remaining work and triggers reconciliation rather than retroactive undo. Test both orderings. Never claim instantaneous reversal from a cancellation flag.

### REQ-19-03

Reserve budgets transactionally, commit intent before dispatch, and consume a permit at the defined boundary before mutation. A consumed permit is never revived after crash. New attempts need current permission and adapter-specific idempotency. Compare-and-set revisions must be combined with protected actual resource access to address races.

### REQ-19-04

Separate monotonic deadlines within a boot from durable time across restarts. Record boot/session identity, observed wall time and uncertainty, and security epoch/revocation basis. Define clock rollback, sleep/resume, witness loss, and offline expiry behavior without extending authority. Restrict time-dependent effects while required freshness is unknown.

### REQ-19-05

Human approval must originate through an authenticated, trusted approval channel bound to the actual request displayed. Bind the target, scope, candidate bytes, consequences, and authority lifetime presented to the owner to the accepted approval event. Model text, quoted permission, a forged UI callback, or a tool's assertion that the owner approved cannot create consent. Define which UI surface and OS principal are trusted for approval, and test a compromised worker's attempt to imitate them. Reconfirmation is required after a material proposal or target change.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B057, B058, B059, B060, B061, B062, B063, B064, B114. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
