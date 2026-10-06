# Verification architecture

**Document ID:** SPEC-36  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-36-01

Create tests with implementation and bind reports to source and environment. Separate unit, property-based, transition-model, concurrency, fault, security, migration, UI, real-model, packaging, offline, performance, and endurance evidence. Use real public paths for integration claims. Mocks satisfy only their declared narrow contracts.

### REQ-36-02

Preserve existing tests as regressions or document intentional replacement under a changed requirement. Differentially compare intended-equivalent CETA semantics. Add every repaired defect and deny condition to tests. Use seeded randomized sequences and mutation testing for critical invariants. Passing counts cannot establish untested properties.

### REQ-36-03

Build a small independent verifier for bundles/history. It must not merely call the producer's accept() routine. Disclose shared libraries and correlated risks. Exercise malformed, truncated, reordered, replayed, cross-scope, stale, and forged evidence, plus mismatches to source, executable, model, policy, and fixture.

### REQ-36-04

Execute Appendix B and source-specific tests discovered through Codex reconciliation. Each scenario records precondition, invocation, injected condition, expected state/effect, observed result, evidence, and status. Distinguish skipped, blocked, timed out, failed, and not run. Source mutation during a gate invalidates its passing report.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B008, B086, B126, B128. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
