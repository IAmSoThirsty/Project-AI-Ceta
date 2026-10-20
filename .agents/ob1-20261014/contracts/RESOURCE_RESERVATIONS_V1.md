# Kernel resource reservation profile v1

This internal profile implements resource accounting on the existing CMP02
`KernelTransactions` and CMP03 `SqliteJournal` transaction owner. It uses the
existing `budget` and `reservation` collections and the same history/transaction
ledger. It creates no scheduler, storage adapter, issuer, policy owner or evidence
ledger. Existing operation-budget units and all their transitions remain unchanged.

The current `ReservationPort.reserve(ReservationRequest) -> ReservationResult`
signature remains unchanged. Trusted composition may obtain a bound port through
`KernelTransactions.resource_reservations(original_proposal_wire, original_context)`.
The kernel retains that exact proposal and opaque context. Request fields are
selectors and resource quantities; they supply no principal, scope or authority.
Public application/IPC composition and runtime effect dispatch remain pending.

The `ceta-kernel-resource-reservations-v1` canonical budget record contains a
`BudgetEnvelope` and exact scope/task/subject/session/proposal/basis/grant/control
generation/policy/environment/deadline binding. Its envelope generation equals
the actual store cell generation and is bounded by the existing `MAX_GENERATION`.
Its limit, control reserve, measured use and reservations remain distinct. The
logical key is `resource-budget:<SHA256(budget_id)>` in the existing budget
collection. Serialization is data construction and does not certify approval.
This slice provides no budget provisioning endpoint.

The SAME captured `AuthorityOwners` object must implement the additional
`ResourceReservationCapabilities` predicates. Resource reservation approval
resolves the exact current proposal, basis, canonical budget, request, peer and
observation clock domain. Held capacity can be released or cancelled only after
that owner's cleanup predicate verifies the resources are no longer in use,
including uncertain native effects. A caller reason cannot certify cleanup.
Missing capabilities deny with `RESOURCE_AUTHORITY_OWNER_UNAVAILABLE`.

Predicates must return `None` or a typed denial, be bounded/repeatable and have no
side effects. They must never reenter the kernel/store, consume an approval or
wait for external work. They run before mutation, inside the existing SQLite
commit guard and before positive publication. Actual elapsed time is checked
after predicate, authentication and clock returns; an overlong result is rejected.
An unavailable OS observation becomes a typed unavailable denial. Positive
publication rechecks the owner and deadline after the final SQLite snapshot.
Each reservation guard observes its clock before checking prepared-basis and
resource approval and then authenticates the peer again. A context or approval
withdrawal observed during that clock call prevents a positive return. Budget
observation likewise checks the prepared basis and peer after its final clock.
Clock, approval and authentication call counts remain unchanged.

The SAME captured owner additionally supplies
`require_resource_current(proposal, basis_wire, budget_wire, request, peer,
request_context)`. It returns exactly `None` or a typed denial after resolving
the original opaque context, peer, prepared basis, approved canonical budget and
exact request under one owner-managed current view. Authority mutations must
coordinate with this decision point; a digest or caller flag supplies no view.
Preceding separate callbacks are compatibility preflights. After this combined
decision the adapter performs only pure record/time/elapsed validation; it calls
no independent clock or authentication provider before returning that decision.
Missing or noncallable capabilities deny, and Boolean allow values are rejected.

For budget disclosure `request` is `None`. That view authorizes the exact
peer/prepared-basis/canonical-budget observation and provides no allocation
approval. ResourceFixture uses an explicitly controlled `RLock` and exact
allowlists on its same captured owner. Its coordinated writers use that lock;
older direct fault injections remain uncoordinated test controls. This does not
qualify a native provider, provisioning, authentication, or effect dispatcher.

The measured local interval from clock-call entry through the final checks
conservatively consumes the sample's remaining monotonic and uncertain wall
deadline margins. The final admission-return guard also consumes the
reservation's remaining observation-age margin. Intermediate guards retain
their trusted-sample age checks and individual callback duration bounds;
they do not claim to project a new authenticated observation timestamp.
This interval issues no new authenticated time sample or epoch. The composed
time owner must supply the declared nanosecond clock domain; its live physical
and authentication qualifications remain pending. Sequential pure predicates
do not establish an atomic host-wide authority snapshot or prevent a later
revocation. A denial after COMMIT preserves the durable hold for peer-bound
historical inspection and separately verified cleanup; it never invents rollback.
This adapter cannot
preempt an arbitrary synchronous Python callback. Native authentication, approved
budget provisioning, actual cleanup implementations and authenticated observation
clock domains remain required production dependencies.

Reservation checks the canonical approved envelope, expected generation, grant,
current prepared dependencies, trusted deadline and observation age. The store
atomically appends the existing proposal payload under a resource event and
updates both the budget and request-bound lease. Existing transaction metadata
binds the exact changes to that event; the proposal payload is a selector and
does not claim an external effect occurred. Capacity is held only after COMMIT.

Within a canonical scope, request identity is unique across budgets. The lease
key is `resource-lease:<SHA256(request_id)>` in the existing reservation collection.
Exact replay returns the original held lease/generation after current authority
and freshness checks, with no extra mutation. Changed budget, quantities,
generation or observation fields conflict. Only the store's two explicit
pre-COMMIT rollback conflicts allow a coherent read of the same identity; the
adapter never automatically retries an allocation or an uncertain call.

Lease states are `HELD`, `RELEASED` and `CANCELLED`. Terminal states are durable
tombstones. Cancelling before reservation records a tombstone without holding or
refunding capacity, after resolving current approval of that exact request.
Cancelling/releasing held capacity requires verified cleanup
and atomically subtracts its exact quantities. Terminal command replay preserves
the exact state and reason; it never refunds twice or recreates a hold. Cleanup
can proceed under current subject authentication after grant revocation without
reviving admission. An owner denial after COMMIT retains the actual committed
state for inspection; it cannot invent a rollback.

`recover(request_id)` returns a coherent, peer-bound historical accounting
observation. It allocates nothing, dispatches no work and does not convert a held
record into current effect authority. Reopen uses existing journal/state
reconstruction rather than a new state store. Full worker lifecycle, queue
fairness, parent/child allocation provisioning, accelerator budgeting and native
resource consumption/settlement remain outside this finite profile.

Acceptance requires actual disposable SQLite tests for CAS concurrency, exact and
conflicting replay, currentness/negative cases, rollback/lost-result/reconstruction,
verified-cleanup denial and terminal tombstones. Existing resource admission must
execute against the real port/store. Synthetic resource-owner allowlists, seeded
budgets and clock/profile controls must remain labelled; they establish executable
accounting behavior and do not establish live authority. Independent review and
Root's exact Source application are separate obligations.
