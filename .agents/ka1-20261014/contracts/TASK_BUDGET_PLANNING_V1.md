# Task budget planning profile v1

Logical units CETA-20.02.01, CETA-20.02.02 and CETA-20.02.03 map to the existing
`ceta.resource.budget` module. Its controller and child-assessment signatures
remain intact. Task IDs and revision digests are input selectors; resolving
their current authorization remains with the task and canonical kernel owners.

`plan_task_budgets` evaluates at most 128 child proposals against one exact
parent `BudgetEnvelope` and generation. It sums every proposed child limit
across CPU, memory, storage and declared wall-time units. The sum must fit after
the parent's existing control reserve, measured use and reservations. Each child
retains its explicit control reserve and distinct measured/reserved quantities.
Duplicate task/budget identities, self-parent identities and differing parent
snapshots or generations close the projection. Unsupported physical
provisioning, accelerator accounting and inference accounting requests return
UNAVAILABLE with exact dependency codes.

The result is a detached PROPOSED, BLOCKED, CANCELLED or UNAVAILABLE data view.
Cancellation produces no child proposals and reports no physical worker stop.
Concurrent pure evaluations can produce equal proposals; only the existing
canonical state/lease owner can atomically approve and reserve them. The
`parent_reservation_request` method constructs the existing typed request from
the aggregate without calling a service, issuing authority, provisioning child
records or changing a generation. A stale selector requires current owner
validation; construction and a digest do not certify approval.

The execution-time controller uses the smaller remaining monotonic deadline
and uncertain wall deadline, rounded down to whole milliseconds. Every typed
envelope/vector is revalidated before arithmetic, including reconstructed or
mutated nested values. Projection recovery rebuilds from supplied current
snapshots; it preserves reservations and performs no replay or refund.

Native task-reference authentication, physical provisioning, canonical child
budget issuance, accelerator/inference consumers, real cleanup/effect fencing
and full controlled workload execution remain separate dependencies. Tests of
these pure controllers qualify numeric containment and actual neighboring
domain/request types with controlled budgets/time; they do not qualify live
resource approval, native scheduling, worker termination or full-unit release.
