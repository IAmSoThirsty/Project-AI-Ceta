# Workload admission decisions and dependency boundary

Mapped units: `CETA-20.03.01`, `CETA-20.03.02`, `CETA-20.03.03`.
Implementation: `src/ceta/resource/admission.py`; budget projections:
`src/ceta/resource/budget.py`. The shared `resource_management.py`, temporal
contracts and canonical owners are unchanged.

`WorkloadRequirementEstimator.estimate` derives conservative bounds from at most
64 measured samples for a pinned profile revision. Peak requirements, supplied
steady measurements, confidence and uncertainty margins are distinct. Missing
steady measurements remain `None`. `MEASURED` names the input provenance; the
conservative vector remains an estimate. No model is executed or qualified by
this transformation.

An optional `WorkloadShape` binds workload class, model revision, configuration
digest, input size with an explicitly named unit, and concurrency. A shaped profile requires an exact expected
shape; a changed input shape is unresolved and is never extrapolated by a guessed
multiplier. Legacy profiles retain their original v1 snapshot commitment and
legacy call semantics. They do not establish a model/input/concurrency envelope.
Profiles with explicit shape or steady measurements use the v2 commitment.
Calibration validates the exact preceding profile, peak, steady values, timestamp,
confidence, headroom policy and shape. It returns a new immutable profile and
never changes a profile registry. A missing new steady observation makes the
extended steady history unavailable. The 64-sample history bound is preserved.
An uncertainty margin beyond the canonical integer bound is unresolved.

`WorkloadAdmissionController.admit` checks current capacity, pressure, profile
age, positive qualified confidence and conservative budget fit before calling
the injected canonical `ReservationPort`. The default profile age is 300 seconds;
the configurable confidence floor is 1/1000 and can be raised by composition.
It reads the clock again before dispatch and closes admission after elapsed
freshness or clock rollback. All monotonic profile/capacity times must originate
from the same current trusted owner clock; the current profile shape has no
boot/resume epoch field, so this transformation cannot authenticate that binding.

The controller forwards request identity, budget identity, expected generation,
observation sequence/time and conservative demand unchanged. It validates the
typed owner result. The current `ReservationPort` gives no generation-advance
postcondition; equality with the requested generation is accepted. It does not
retry a failed dispatch or malformed post-dispatch response. Such an exception
can follow a committed reservation; the canonical owner must reconcile using the
original request identity before another operation. This controller never
launches, releases, cancels or claims rollback of work.

`plan_concurrency` preserves its capacity-only FIFO signature. It accepts at most
256 unique workload identities, retains explicit control capacity and compares
remaining capacity before addition. A repeated identity is invalid; unknown or
unrepresentable demand closes the prefix. This older API has no current clock,
budget generation or owner readiness inputs. Its output is a capacity proposal.

`plan_budget_concurrency` also takes the exact `BudgetEnvelope`, expected budget
and owner generations, owner-supplied `WorkloadPlanningFacts`, and trusted
`ClockSample` values. It preserves measured use and existing reservations, checks
profile freshness/confidence and canonical deadlines, and evaluates explicit
cancellation, authority readiness and shared-file conflict identities. Readiness
is a declared owner fact and never an authority grant. File keys are exact opaque
canonical identities; this module does not resolve or normalize filesystem paths.
Unknown readiness/conflicts are blocked. Mixed owner generations invalidate the
whole cut; a changed profile snapshot invalidates the affected workload.

Oldest eligible queue time comes first, then higher priority, earlier deadline
and exact workload identity break ties. An eligible head that cannot fit defers
newer workloads, preventing repeated small arrivals from bypassing it. Cancelled,
unready, stale and incompatible entries have explicit per-workload decisions.
This bounded pure function owns no queue, fairness-aging state, reservation
store, scheduler, authority issuer or evidence ledger. Repeated concurrent
evaluation of the same pinned facts produces the same proposal.

`project_workload_budget` validates expected generation and returns separate limit,
control reserve, measured use, reserved use, estimated use and remaining capacity.
An accepted projection conserves all dimensions. Estimates are neither charged
measurements nor published reservations. A rejected/stale projection has no
remaining-capacity success value. Neither this projection nor a plan grants
capacity or execution authority.

## Open canonical integration obligations

The present shared port has only `reserve(ReservationRequest) -> ReservationResult`.
The actual source contains no concrete canonical reservation owner implementation.
Its request/result lack workload/profile response binding, reservation expiry,
queued/cancelled/released states, lease fencing, release-after-cleanup and recovery
operations. Those fields and operations require coordinated owner/consumer review,
an actual state transaction and native producer-consumer qualification. No local
replacement owner or mocked service has been introduced. Controlled-port tests
prove only domain wire behavior; they do not prove atomic reservation or a
cancelled queued task's native lifecycle. Mandatory architecture acceptance for
real simultaneous reservation, cancellation, restart, restricted-principal access
and independent completion remains open until those interfaces and evidence exist.

The new tests cover measured calibration/shape lineage; malformed inputs;
duplicate, stale, future and mixed-generation inputs; uncertainty and overflow;
control/measured/reserved conservation; cancellation decisions; canonical temporal
checks; file conflicts; deterministic concurrency; and exact owner-port forwarding
with no automatic retry. Existing native resource/diagnostics tests remain intact.
New source is a review candidate until separate review and Root application.
