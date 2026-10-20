# Native CPU outcome producer and observer provenance

This component implements the retained producer and observer binding for RE-T23
and RE-T24. The source is an isolated integration candidate. The separate
`NativeOwnerView` forwarding change is proposed in the handoff and has not been
applied to this candidate's preserved dependency files. Public application
composition, native qualification, and canonical publication remain pending.

## Original producer

`NativeCpuOutcomeProvenance` belongs to one exact `NativeOwnerView` and one exact
`NativeCpuEffectObserver` using the view's native clock. It accepts only the
original active `_RetainedCpuExecution`, its active native owner retainer,
original request context and thread, same coordinator, kernel, journal and
store lock, consumed permit, and committed attempt. Dispatch must have been
admitted and the captured native dispatch invocation must have finished.

The owner retains original object references and immutable canonical bytes.
The consumed permit and attempt determine the receipt's operation and event
references. An available `CpuRateChange` is checked and retained as the actual
native dispatch result; absent native result data remains unavailable.
Replacing or mutating retained producer facts rejects subsequent use.

The first receipt is immutable across advancing reconciliation. Its effect
status is `MAY_HAVE_EXECUTED` for every native result state, including `APPLIED`
and `RESTORED`. Native change data alone does not establish independent
observation. Unavailable start/finish times, exit code and output remain null;
no invented measurement is used. Cancellation is `REQUESTED` when Stop is
already recorded at first receipt construction and otherwise `NONE`. A later
Stop does not rewrite the original receipt or prevent required bookkeeping.

## Independent observation

Collection invokes the captured actual `NativeCpuEffectObserver.observe`
implementation with the original request and captured native target. The
owner retains the original returned observation and validates it with the
captured `require_observation_origin` implementation. An advancing observation
must have a larger sequence and monotonic timestamp with the same observer
image. Each collection retires the previous local proof, including when the
new observation fails. Unavailable observation values retain their unavailable
state; they are never converted to measured zero.

The callback compares decoded observation bytes with retained original bytes
and invokes the origin predicate using the original object and captured target.
Caller DTOs, Boolean values, digests, copied captures, and opaque objects have no
standalone origin authority. The local proof is usable only with the same
retained producer, context, peer, request, consumed permit, receipt and current
observer state. The owner cannot be copied or serialized.

The callback performs only structural/byte checks and the existing pure origin
predicate. It uses a nonblocking lock and performs no SQL, native observation,
authentication, effect, wait, or durable write. The existing canonical 50 ms
gate remains responsible for the complete guarded operation. Controlled tests
record a measured callback duration; this is not a native latency qualification.

## Execution and failure

`NativeCpuOutcomeAdapter.execute` calls only the existing retained lease's
captured dispatch implementation. After its return, or an admitted dispatch
exception, it attempts observation and the existing canonical outcome writer
while the original lease and owner retainer remain active. It adds no callback
between the final dispatch admission decision and the native effect call.

An observer failure is retained exactly, with a null observation and an honest
uncertain receipt. The existing writer may commit that uncertainty; the adapter
then reraises the same observer exception. An original dispatch exception
remains primary while observation/write failures are attached as secondary
facts. Custody, captures, and committed outcomes are attached through canonical
`BaseException` storage, avoiding overridable attribute/formatting hooks. A
subsequent retained-state failure cannot replace the observer primary.

`reconcile` performs observation and canonical recording without redispatch. It
requires the same currently active admitted lease. The canonical kernel remains
the sole durable writer and sole outcome classifier. This helper creates no
new store, ledger, scheduler, authority issuer, or independent settlement rule.

## Composition and remaining dependencies

The proposed view constructor adds optional `cpu_outcome_observer`. Without it,
the provenance property returns `None`, preserving the existing owner session's
default denial. When composed, it returns the exact view-bound forwarding
method captured by `NativeCpuOwnerSession` at construction. The captured method
calls this same view's retained producer with the original owner retainer.

The adapter must run inside the original admitted lease's active context. This
cut does not provide an entry after retainer exit reaches `FAILED` or `PENDING`.
The separately assigned recovery implementation must establish that bookkeeping
custody before using these components. Denial after capacity marking but before
dispatch admission is also a separate negative-producer/recovery requirement;
this cut never labels it `NOT_STARTED` from flags or an old native change.

Physical outcome capacity and fresh reservation for advancing reconciliation
remain the capacity owner's responsibility. The helper cannot substitute a
mocked service for those interfaces. The controlled tests explicitly replace
native observation, dispatch and canonical writes and therefore establish
binding/failure behavior only. Native application composition and end-to-end
authorization-to-effect evidence remain required for product acceptance.
