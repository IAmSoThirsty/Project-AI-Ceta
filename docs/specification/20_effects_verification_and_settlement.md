# Effects, verification, and settlement

**Document ID:** SPEC-20  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-20-01

Use one effect path: proposal validation, required review/consent, permit preparation, durable intent, bounded dispatch, consumption, execution observation, independent readback, and settlement. Keep proposed, authorized, dispatched, running, process-exited, observed, verified, failed, cancelled, and indeterminate states distinct. UI cannot reduce them to one green check. Fluent output never certifies a tool call.

### REQ-20-02

Every adapter declares schemas, permissions, risk class, environment, side effects, preconditions, idempotency, completion predicates, cancellation, and compensation limits. Registration is not qualification. Bind implementation and dependency identities to evidence and invalidate qualifications after relevant changes. Reject undeclared operations.

### REQ-20-03

File actions bind approved bytes and original revision, preserve applicable encoding/newline/metadata, use race-resistant handles, and verify actual output independently of the expected-result author. Commands bind executable identity, argument tokens, environment allowlist, directory, mounts, limits, and observations. Store actual exit/output separately from semantic outcome. Exit zero cannot prove arbitrary real-world success.

### REQ-20-04

Local transactions cannot atomically commit arbitrary external effects with the journal. Use durable intents/outbox, receiver idempotency where supported, observation, and reconciliation. Do not promise exactly-once arbitrary remote action through crashes. Audit replay reconstructs state without re-running commands, changing files, or re-sending communications.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B058, B060, B097, B098, B099, B100, B103, B104. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
