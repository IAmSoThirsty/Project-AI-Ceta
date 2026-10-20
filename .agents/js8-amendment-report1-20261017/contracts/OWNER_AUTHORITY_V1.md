# Canonical owner authority v1

This module implements the RE-T06/T13/T14 canonical transitions on the existing
captured `KernelTransactions`, codec, owners and `SqliteJournal`. It creates no
store, scheduler, independent policy evaluator or alternate issuer. Existing
operation-budget methods and `require_runtime_admission()` retain their behavior.
Default runtime admission remains closed. The module never launches a process,
changes a native CPU policy, waits for a human, or settles a native outcome.

The additive kernel methods are:

* `begin_owner_enrollment(request_wire, request_context)`
* `enroll_owner(request_wire, transcript_wire, native_proof, request_context)`
* `approve_owned_cpu(enrollment_id, request_wire, transcript_wire, native_proof, request_context)`
* `stop_owner_authority(enrollment_id, request_context, reason_ref)`
* `revoke_owner_authority(enrollment_id, request_context, reason_ref)`
* `recover_owner_enrollment(enrollment_id, request_context)`

Mutating methods return the existing `KernelResult`, whose primary record is a
real admitted `PolicyDecision`. Additional same-transaction StandingGrant and
ActionProposal events bind their exact projections. Recovery returns immutable
`OwnerAuthorityState` historical metadata and does not issue, refresh or dispatch.
`owned_cpu_proposal(codec, request)` is deterministic proposal data, not approval.

The same captured owners must provide both optional capabilities:

```python
owner_enrollment_expected(original_context) -> EnrollmentRequest
require_owner_authority_current(
    phase, enrollment, effect_request, transcript, native_proof, peer, original_context
) -> None
```

Finite phases are `CHALLENGE`, `ENROLL`, `APPROVE_CAP`, `APPROVE_RESTORE`, `STOP`,
`REVOKE` and `RECOVER`. Missing/noncallable capabilities, wrong expected types,
Boolean decisions, or exceptions deny. The provider returns exactly `None` or
raises a typed denial. It must resolve the original opaque context, exact native
root/database handles and file identities, current source/policy/environment,
principal/session/lifetimes, clock, and private ceremony proof under one current
owner-managed view. A DTO, label, digest, `REPORTED_VERIFIED` field or object
supplied by a worker is insufficient. The provider owns genuine native proof
origin. Kernel and provider must be composed against the same designated store;
the pure EN1 path codec does not open or authenticate the filesystem.

Human interaction completes before the command. The predicate is pure,
repeatable and bounded, and must not reenter the store, allocate authority,
consume proof, start I/O or wait for user/model work. It runs initially,
immediately before COMMIT, and before result publication. The final external
callback is this combined predicate. Subsequent validation is pure and charges
actual QPC-backed `perf_counter_ns` elapsed time conservatively against
deadline/observation bounds, including two measured resolution units for endpoint
quantization. An unavailable/nonmonotonic/adjustable stopwatch, invalid counter
or counter rollback denies. Python3.12 `monotonic_ns` uses coarse GetTickCount64
on this host and is not the guard stopwatch. Only elapsed durations are added to
the captured owner sample; absolute clock origins are never compared or equated.
Returns exceeding 50ms are rejected; arbitrary synchronous Python callbacks
cannot be preempted. Clock pairs are privately reconstructed and revalidated;
guard high-water prevents an internally valid pair from rolling back an earlier
guard. Native owner clock/currentness mutations require coordinated locking.

Enrollment uses the exact EN1 request and domain-specific transcript wrapper.
The canonical 128-bit ceremony nonce differs from the native transport's
256-bit nonce. Neither domain is converted into the other. Enrollment's helper
and UI lifetimes exactly match EN1. Later CPU ceremonies may have freshly
prepared lifetimes; approved code commitments remain equal and the native owner
must authenticate each actual proof/lifetime/request/display binding.

This bounded bootstrap supports one designated installation/profile/session in
an initially unprovisioned canonical control/registry. Both request generations
start at zero. An unregistered project scope, conflicting existing control,
registry or profile, old pending record, replayed challenge or nonce is rejected.
CHALLENGE commits a `SEEK_AUTHORITY` decision, exact pending request, reserved
tombstones and control generation0; no StandingGrant exists. ENROLL requires
genuine captured proof and atomically consumes the ceremony, records the exact
EN1-domain transcript and enrollment,
and advances authority/fence generations to1. A stopped/revoked profile is not
automatically recreated. New installation/session renewal is a separate explicit
transition, outside this unit.

The first cap approval creates one nondelegable StandingGrant for the exact
principal/task/process lifetime/job, only cap+restore operation classes, the
enrolled source/policy/adapter/environment and finite declared budget. The
resource ID binds process and job; each prepared basis carries the exact current
resource revision. Grant resource revision is wildcard only within that one
lifetime/job, allowing a separately approved restore to bind a new observed CPU
policy. No other resource/task/proposal may be projected through this unit.
The canonical owner predicate still must authenticate physical preconditions.

All grant, budget, basis, task/resource revisions, exact request/transcript,
challenge/nonce tombstones and policy/proposal/grant events share one SQLite
transaction and CAS read set. No development auxiliary allocation decision is
used as approval. The recovery allocation is withheld during cap. Restore
requires its separate fresh ceremony and exact cap-parent link, canonical
consumed cap permit/intention resolved through the existing durable event,
index, payload and peer checks, zero held liability, exact charged cap cost and
the untouched recovery allocation. Only then is that allocation made available
to the already existing prepare/consume methods. Canonical consumption is not
proof of a native effect: the captured native predicate must additionally
resolve the independent actual state and restoration precondition. Durable
native outcome/settlement and retained dispatch admission remain separate.

Stop/revoke atomically increment both generations and revoke any issued grant.
Unknown held/charged liabilities and consumed permits are retained; no speculative
refund, cleanup or effect replay occurs. The native owner must authorize the
original enrolled peer. These deny operations and historical recovery do not
refresh an expired enrollment; they still require current authenticated peer,
provider and valid advancing clock pair. Existing historical rows remain exact.

Before COMMIT any denial/control exception rolls back the entire transaction.
After COMMIT a changed owner/currentness/elapsed bound denies publication while
retaining the exact committed grant and consumed tombstone. Explicit recovery
reports that state; retry cannot reuse the ceremony. Results are evidence at
their linearization points, not effect capabilities retained after return.
Future dispatch must retain a qualified native authority/Stop/revocation lease.

Qualification in this candidate uses actual disposable NTFS SQLite databases,
two real connections, CAS races, rollback/reconstruction and existing kernel
prepare/consume. Positive native proof and clock fixtures are controlled and
provide no Windows Hello, OS owner enrollment, isolation, observer, public route,
native effect or production acceptance. The genuine provider/composition,
retained authority lease, live provisioning, separate native observation,
durable outcome and final human ceremony remain explicit dependencies.
