# Performance and resource integrity

**Document ID:** SPEC-34  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-34-01

Freeze measurable targets before tuning, based on the supported machine/profile. Proposed initial targets are ordinary UI acknowledgment within 250 ms at p95 and stop-admission acknowledgment within 250 ms at p95, with separate backend termination targets. These are engineering targets requiring measurement and ratification, not claims of achieved performance. A revision requires evidence and a recorded requirement change, never silent benchmark relaxation.

### REQ-34-02

Measure observation, retrieval, continuity validation, compilation, rendering, admission, loading, first token, generation, tool dispatch, readback, and settlement separately. Test cold/warm runs and growing histories. Use at least 30 measured repetitions for reported p95 and sufficient samples for p99, with counts explicit. Record failures, cache state, load, timeouts, and overhead. Fast incorrect answers cannot qualify responsiveness.

### REQ-34-03

Cover small profiles, the historically observed thousands-of-events regime, and larger isolated synthetic profiles such as 10,000 and 100,000 events. Label synthetic stress honestly. Bound queues, caches, residency, logs, temporary data, and evidence growth. Avoid full-history revalidation on every parser byte or keystroke while preserving the integrity guarantees relied on.

### REQ-34-04

Reserve stop, settlement, and recovery capacity. Apply backpressure before exhaustion destroys those functions. CPU/GPU claims require real placement evidence. Do not reduce memory pressure by dropping required context, bypassing verification, or using a hidden external provider.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B020, B080, B115, B125. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
