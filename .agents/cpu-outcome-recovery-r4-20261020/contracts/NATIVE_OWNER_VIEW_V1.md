# Native owner view

This trusted composition unit observes the existing concrete Windows peer registry,
its original active request context, and exact retained native private-store objects.
It issues no authority. `NativeStoreBinding` opens the existing `history.sqlite3`
with read-attributes access, permits existing SQLite writes, denies delete sharing,
and retains every ordinary ancestor until explicit close. Full 64-bit volume and
128-bit file IDs, normalized volume-GUID paths, kinds, reparse absence and handle
inheritance are measured through Windows APIs. Missing files stay missing.

`NativeOwnerView` requires the concrete registry, native clock and store binding.
It revalidates the actual pipe peer, message token, process/image/token lifetime,
receiving native thread, original message and request-context lifetime. It emits
typed enrollment facts with exact zero values and full LUID bits. Returned data
does not create a grant, approve a ceremony or renew a context. A fresh observation
and canonical authority/currentness checks remain necessary at every transition.

The library bounds observed elapsed time; it cannot preempt a stalled Windows API.
The Windows stopwatch requires the QPC-backed `perf_counter_ns` implementation,
a monotonic nonadjustable source, and finite positive resolution. Each duration
includes twice the advertised resolution rounded up to nanoseconds. An elapsed
interval above the inclusive two-second bound, a reversed counter, an invalid
sample or an unavailable source is denied. No clock fallback or epoch equivalence
with the native session clock is assumed. Python 3.12's coarse GetTickCount64
counter is excluded from this duration check.
File handle retirement reuses the independently reviewed isolation library's
duplicate-object fence. Uncertain cleanup remains recoverable on the exact primary
exception through nonoverridable exception storage. Caller-owned registry and clock
lifetimes remain caller-owned. No configuration, ACL, profile, service or host
account changes occur here. Same-account/admin tampering and in-process privileged
mutation remain explicit trust boundaries.

Actual tests use disposable SQLite files, Windows file handles, existing native
pipe fixtures and the native clock. No native owner approval, enrollment, journal
authority issuance or governed real effect is accepted by these tests.
