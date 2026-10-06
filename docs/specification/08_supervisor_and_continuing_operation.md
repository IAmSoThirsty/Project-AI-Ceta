# Supervisor and continuing operation

**Document ID:** SPEC-08  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-08-01

Implement a CETA-owned supervisor for health, durable event admission, scheduling, worker lifetimes, observation subscriptions, budgets, and recovery. Give it exact lifecycle states, including STARTING, READY, ACTIVE, PAUSED, DEGRADED, RECOVERING, STOPPING, and STOPPED. Separate a live process from a qualified model and a qualified tool. Green status cannot conceal invalid policy, corrupt state, unavailable broker, or an unresolved hazardous effect.

### REQ-08-02

Make operation event-driven. User input, scoped file changes, tool completion, expired grants, failed checks, scheduled owner-approved work, and recovery can enqueue bounded work. Each event needs stable identity, deduplication, causation, lease, retry policy, expiry, priority, and disposition. Use bounded queues and backpressure. Internal feedback must not recursively trigger unbounded model calls or fill disk.

### REQ-08-03

Delivery may be at-least-once; effects need separate duplication control. Fence stale workers with a durable generation checked at effect admission. Worker death, missed heartbeat, or expired lease cannot mean completion. Reconcile on restart before retrying. Restore observation subscriptions only under still-valid grants and fresh checks.

### REQ-08-04

Background-service operation is an explicit setting. Define whether closing UI stops work or leaves an opted-in supervisor active. Do not install autostart, hidden persistence, remote reachability, microphone capture, or screen capture to create an impression of presence. After downtime, explain the observation gap and reconcile reality. Implement continuity through state and events, not unsupported claims of uninterrupted awareness.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B017, B018, B019, B020, B021, B023, B024. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
