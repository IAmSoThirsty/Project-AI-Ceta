# Owned native CPU effect contract, version 1

The explicit `ceta-owned-real-effect-v1` profile binds one owner-directed CPU
hard-cap reduction or separately requested exact restoration to the canonical
kernel journey. `OwnedCpuRequest` is immutable typed request data. It binds the
scope, task/proposal/revision, principal/current session/nonce, PID/creation/image,
owned job identity, exact observed policy/version/time, original and target DWORDs,
policy/adapter/environment/source/observer commitments, one-effect operation
budget, outcome capacity, deadline, observation limits and declared consequences.
It supplies no grant, native custody or positive owner decision.

The strict decoder requires canonical bounded integer-only wire bytes, exact
fields and complete nested shapes. All Boolean integer substitutions, unavailable
preconditions, unsupported policy conversions, increases, notification changes,
inadequate budgets and wrong restoration links are rejected. Original disabled
policy union bits are retained exactly. A restoration refers to a different
original reduction request and its full commitment, same target/scope/task/owner,
and exact original policy. Current canonical ownership and fresh genuine approval
still decide whether that restoration can execute.

`approval_display_bytes` includes the complete request and its commitment in one
versioned renderable body. `NativeApprovalTranscript` records exact UI/helper
lifetimes/code, principal/session, challenge/nonce, displayed/request commitment,
clock sample and raw native HRESULT/result. The result numbers follow Microsoft's
[UserConsentVerificationResult definition](https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverificationresult?view=winrt-26100).
`REPORTED_VERIFIED` describes the supplied data. Only the captured live native
approval owner can authenticate its origin and consume the nonce through the
canonical kernel. Parsing a transcript or passing the pure binding predicate
cannot authenticate the user, mint a grant or satisfy the actual consent case.
No credential or biometric payload is collected by this contract.

`CpuEffectObservation` retains actual policy separately from target liveness and
membership. The expected method is query-only class15 observation by a separate
process. Shared OS/API implementation is the declared independence limitation.
Pure comparison rejects wrong request/target/job/code, replay, stale/future time,
boot/epoch/resume/rollback changes, missing trusted time and expiry. A matching
job policy after target exit or membership loss remains unavailable for a live
worker-effect claim. Measured disabled/zero values remain different from an
unavailable query. The comparison result is data until the captured independent
observer and canonical kernel authenticate, record and settle it.

RE-T02/RE-S1 is implemented as executable contract logic. Tests use controlled
data and exercise exact rejection/currentness/commitment behavior. Genuine
native consent, canonical single-use admission, physical execution, authenticated
independent observation, crash custody/reconciliation and public runtime
composition remain separate required implementation and acceptance work.
