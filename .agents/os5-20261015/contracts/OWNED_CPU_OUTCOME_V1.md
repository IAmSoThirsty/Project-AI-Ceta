# Canonical owned CPU outcome transactions v1

This component delegates to the existing `KernelTransactions`, its captured
owners and the same `SqliteJournal` writer. It dispatches no native operation and
creates no authority, refund, replacement ledger or automatic restoration.

`begin_owned_cpu_attempt(request_wire, permit_wire, native_proof, original_context)`
requires the exact approved typed `OwnedCpuRequest`, canonical consumed permit,
verified consumption event/index and unchanged charged reservation. It records
one stable `kernel.owned-cpu.attempt` event and reserved outcome projection. This
is an authorized dispatch attempt/reservation; it proves no native Set occurred.
Repeated exact requests authenticate the same proof/current peer and return
historical state. They do not reissue a permit or dispatch anything.

`record_owned_cpu_outcome(request_wire, permit_wire, receipt_wire,
observation_wire_or_None, native_proof, original_context)` commits the canonical
`ExecutionReceipt`, optional `EffectObservation` and settlement `PolicyDecision`
in order, within one real SQLite transaction and CAS. The receipt binds the
consumed permit's complete input commitment and exact attempt event, task,
operation and executor session. A distinct immutable projection retains each
typed native observation; its commitment and record reference remain resolvable
after later reconciliation. The operation's current outcome and task outcome
projections change in the same transaction. Existing task revision, intent,
consumed permit, charged reservation and charged allocation remain unchanged.

The kernel captures this optional predicate when constructed:

```
owners.require_owned_cpu_outcome_current(
    phase, request, consumed_permit, execution_receipt_or_None,
    native_observation_or_None, native_proof, authenticated_peer,
    original_context,
) -> exactly None
```

`phase` is `ATTEMPT` or `OUTCOME`. This private canonical owner must resolve the
retained native attempt, exact job/process lifetime, current source/adapter and
observer binding, original context and evidence capacity. It must authenticate
producer and independent observer origins; typed DTOs, a digest, Boolean or
caller-created proof object establish none of those facts. Missing capability
or malformed result denies. The callback is bounded, repeatable, side-effect
free and must not reenter the journal/kernel, allocate authority, wait for a
native operation or ask for human input. It runs before, inside and after the
short writer transaction. No SQL transaction spans native work or human wait.

The final external callback is this coordinated predicate. Clock/peer calls
precede it, followed by pure input and conservative high-resolution elapsed
checks. Attempts additionally require a current deadline. Late outcome evidence
does not revive permission: it may be recorded after a deadline to preserve
historical uncertainty under current authenticated bookkeeping ownership.

`ATTEMPT_COMMITTED` means no receipt is committed. `UNCERTAIN` preserves missing,
unavailable, stale, future, epoch-incompatible or lost-target observations.
`DISCREPANCY` records an authenticated current mismatch. `SETTLED_OBSERVED`
records exact policy agreement from the separately authenticated observer. The
schema independence class remains `SEPARATE_PROCESS`, and causal attribution
remains `UNESTABLISHED`: matching a queried policy alone does not establish
exclusive causality. Exit zero and adapter success do not supply independent
verification. Unsupported `OBSERVED_EFFECT` claims without a matching independent
observation are rejected. Missing telemetry never establishes no effect.

Uncertain/discrepant outcomes can accept a strictly advancing observation from
the same observer lifetime without replacing the original receipt. Settled
outcomes cannot be overwritten. Exact retries return existing evidence without
another journal commit. Restoration needs a separate approved request, consumed
permit, native proof and attempt against the latest current policy. A recovered
attempt, original limit or supplied DTO cannot authorize restoration.

The reserved request capacity bounds cumulative logical canonical evidence
writes for the entire consumed request: its durable attempt, first outcome and
every subsequent reconciliation. Each batch charges the exact serialized event
and payload wires plus every outcome/task/native-evidence projection value
written by that batch. Replacing a projection charges its new serialized value
again. Old immutable evidence remains charged. Exact retries charge no bytes.
The bound counts logical values once per canonical write; SQLite's internal
transaction-provenance metadata, duplicate storage copies and index/page/WAL
overhead are separate physical storage obligations.

`stored_bytes` is the cumulative total, `prior_stored_bytes` is its authenticated
preceding total, and `attempt_stored_bytes` retains the initial attempt charge.
The initial count is bound into the canonical attempt decision; settlement
decisions bind the current total, preceding total and original attempt count.
Recovery verifies these commitments and independently recomputes the latest
batch from its exact indexed event/payload wires and deterministic projection
values. The preceding count was already recovered under its decision before
the update, and the same transaction CAS retains that cell revision. Counts
therefore never reset, decrease or refund when observations advance or a
kernel/journal is reopened. Legacy rejected parent rows without the accounting
fields are refused, rather than silently adopted or assigned a new allowance.

The charged operation allocation already covers the declared capacity. Capacity
overflow before dispatch leaves no durable attempt; overflow during outcome or
reconciliation rolls back the entire new batch and retains the preceding
historical uncertainty and charged liability. Physical SQLite
page/WAL overhead, free-space guarantees and failures after a native effect are
separate infrastructure obligations; this component claims no filesystem-space
guarantee. Unexpected storage loss retains consumed liability and requires
reconciliation. It never refunds a consumed effect or silently retries it.

`recover_owned_cpu_outcome(request_wire, permit_wire, original_context)` performs
only authenticated reads. It checks canonical consumption, exact indexed events,
receipt, observation, immutable native-evidence projection and settlement before
returning frozen historical bytes. A consumed permit without an outcome remains
`CONSUMED_UNRESOLVED`; a durable attempt without a receipt remains unresolved.
Read-only reopened databases support this inspection. Recovery does not grant a
new service session ownership or replay a Set. Canonical context/session handoff
and surviving native custody remain composition requirements.

The original controlled8KiB request cannot fit a complete cumulative outcome:
the first repaired measurement required10,786 bytes for its2,655-byte attempt
and first measured outcome, before the separately retained attempt-count field
was added. The normal success fixture now explicitly enrolls65,536 written
bytes with32,768 reserved for restoration/evidence and declares32,768 bytes per
operation. These finite controlled inputs are allowed by the unchanged contracts;
production constants and defaults are unchanged. The8KiB request remains a
real atomic-overflow test. Final exact serialized measurements accompany each
qualification receipt rather than a universal minimum-size claim.

Tests use disposable real SQLite databases, writer fault injection, concurrent
connections and real child-process before/after-COMMIT exits. Positive native
proof predicates are explicitly controlled fixtures. Actual native effect and
independent observer integration, protected store composition, physical
power-loss behavior and public runtime activation require distinct qualification.
