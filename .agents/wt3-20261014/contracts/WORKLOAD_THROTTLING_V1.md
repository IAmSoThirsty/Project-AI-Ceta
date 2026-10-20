# Workload throttling, version 1

CETA-20.04.02 extends `WorkloadThrottlingController` while preserving its
existing `recommend(ThrottleRequest)` method. The new `plan`, `execute` and
`stop` methods consume exact typed `WorkloadThrottleIntent` records. They
preserve canonical resource lease/budget, task revision, proposal digest,
process PID/creation/image, owned job identity, limit version, observation
sequence/content/times, safeguards and deadline in the complete input digest.
No record, digest, recommendation or Python protocol grants authority.

## Decisions and admission

Planning is pure with respect to canonical state. Local derived pressure
tracking uses the existing detector and its distinct-observation hysteresis.
Malformed nested quantities are revalidated; unavailable, stale, future,
incoherent, replayed or switched pressure closes the affected plan. Only an
effective CPU hard-cap reduction is supported in this native profile. Stream,
batch and concurrency recommendations retain their existing interfaces; this
profile does not invent their runtime enforcement owners.

Measured usage, canonical reservation and control reserve remain distinct.
The held lease must be represented in the supplied conserved budget, which
must retain the required control reserve. Verification, evidence, stopping
and recovery safeguards cannot be disabled. These data checks do not establish
that a caller's budget or pressure source is authentic; the captured owner
must resolve their exact current revisions before an effect.

`ThrottleExecutionOwner.admit_throttle(original_context, intent, owned_process)`
is the minimal retained execution seam selected with the integration owner.
The canonical execution owner must durably record and consume an exact
single-use intent, reserve evidence capacity, authenticate the original opaque
context, and retain cancellation/revocation/resource/target fences through
native observation. Its retained lease binds operation ID, complete input
commitment, durable intent and evidence references. Current predicates and
durable outcome recording return exactly `None` or raise a typed denial.
They are bounded and must coordinate mutations with that retained view.
Context-entry failure must preserve or settle any owner-held admission;
context exit must not suppress a primary control exception.

The default controller has no execution owner and denies effects. Existing
CMP-02 `require_runtime_admission` still denies; CMP-19 has specification only.
No production issuer, authenticated pressure/clock provider, durable throttle
intent writer or live execution composition is supplied by this increment.
Controlled context/evidence fixtures demonstrate conformance, not that missing
integration. The original twenty record schemas and canonical owners are
unchanged. This is no new store, scheduler, capability issuer or evidence ledger.

## Actual owned Windows enforcement

`WindowsOwnedProcess` queries and changes only its retained job using
`JobObjectCpuRateControlInformation` (class 15), the native eight-byte policy.
PID, creation time, image, job membership and an opaque job-lifetime digest
bind observations. No arbitrary PID or job is opened. Exact policy DWORDs and
supported original union modes are retained; only a lower hard cap is newly
applied. Existing CPU notification flags must be preserved; dropping or adding
that flag through a reduction is rejected. The rate is cycles per 10,000,
never a guessed ResourceVector mapping.
Nested-job quotas depend on their parent; no whole-machine capacity is inferred.
Unsupported native APIs/flags, failed queries or malformed results are explicit
unavailable observations, distinct from measured zero or disabled control.

Lifecycle locking serializes observation, expected-version checks, mutation
and recovery. A native attempt spends its local version before Set, retaining
one original/intent/recovery record before any possible effect. An uncertain
attempt requires read-only reconciliation, not blind replay. Changed external
limits invalidate the expected cut. Duplicate operations do not repeat Set;
canonical durable deduplication remains the execution owner's obligation.
This one bounded volatile recovery record is not restart-safe durable intent.

Restoration is a distinct currently admitted operation naming the original
change and exact original policy. The native owner checks that target before
Set and observes it afterwards. Cancellation and exit never automatically
restore a policy or revive authority. `NOT_APPLIED` records a failed native
attempt whose current observed limit is the original; it does not prove the
absence of every transient effect. Unobserved apply/restoration is `UNCERTAIN`
and retains the exact owner and original. Control exceptions remain primary
and expose owner/change custody when a native attempt was started.

The other job limits, including kill-on-close containment, are not rewritten.
Actual empty-job and exited-lifetime observations precede close; primary exit
alone does not establish that job accounting has settled.

## Timing, cancellation and outcome

Monotonic timestamps retain their public domain. Independent high-resolution
elapsed checks and the actual monotonic resolution conservatively fence
accepted query windows, expected-observation age and deadlines, including
time consumed by currentness checks. Rollback remains rejected after the clock
recovers. Synchronous native/callback occupancy is not preemptively bounded;
late results are rejected or classified uncertain. Stop closes new controller
admission; it does not claim a worker has stopped. Native termination/close
remain with the existing owned lifetime. Post-dispatch malformed output,
lost evidence, failed currentness or retained-lease exit keeps an uncertain
outcome, never a fabricated denial asserting no possible effect.

The optional native `dispatch_fence` is a Stop/currentness fence, not an
authority issuer. The controller retains the canonical admission while the
native owner finishes lifetime, expected-policy and clock checks and captures
the Set method and arguments. The fence completes the final captured owner,
input and elapsed-time callbacks, then orders Stop against logical dispatch
under a short lock containing no callback or native work. Stop takes only
this short lock; it never waits for the controller or native lifetime lock.
Stop winning before logical admission denies both apply and restoration
without spending a native version or changing the policy. Logical admission
and the subsequent irreversible class-15 Set are distinct events. Stop after
admission closes future work but cannot refund an admitted attempt or erase
an observed effect. Unobserved effects retain uncertainty and owned custody;
restoration remains a separately admitted exact operation. Direct trusted
owned-library calls keep their default behavior without this optional fence.

The pure post-callback native state guard also rejects an already requested
owned-lifetime termination. A retained job handle after worker exit does not
permit a newly prepared Set. This check makes no further clock or native call
after the dispatch fence and leaves the native version and original policy
unspent when the known termination request wins. Normal owner predicates remain
side-effect-free; the adverse recovery test deliberately exercises reentrant
owned termination and measures the actual empty job and unchanged policy.

## Acceptance evidence and remaining dependencies

AT-CETA-20.04.02-01/09: actual owned busy workload before/capped/recovered CPU
counter windows, native exact-limit restoration, and actual SQLite lease to
controller/native-owner conformance. Controlled pressure/execution approval
remain labelled. Real canonical admission/evidence integration stays open.
AT-02: each mandatory safeguard and unavailable evidence denies before effect.
AT-03/04: malformed nested inputs, lifetime/job/version mismatch, stale/future
and replayed pressure, clocks and restoration targets deny.
AT-05: original opaque context and exact current binding are required; this is
controlled conformance, not native principal isolation qualification.
AT-06/07/08: bounded elapsed rejection, primary interruptions, concurrent
version competition, read-only reconciliation and distinct authorized recovery.
AT-10 remains for the separate reviewer against the frozen source and raw IDs.

Physical observation authentication, native current authority, durable restart
recovery, model/stream/batch enforcement, provisioning and installed product
qualification remain mandatory separate integration work.

Primary Windows definitions: [CPU rate structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information),
[query](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject),
and [SetInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject).
