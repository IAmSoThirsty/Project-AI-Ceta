# Native session clock — NC3 current-platform qualification

Ownership is CMP-04 identity, additive to the existing pure temporal contract.
Mapped requirements: SPEC-19 REQ-19-04; RE-S2/T11–12; RE-12–15/32/33.
`NativeSessionClock.clock()` returns the same exact `(ClockSample, ClockSample)`
shape already consumed by `KernelTransactions._clock`. Existing identity owners,
temporal predicates, issuer, store, kernel and closed runtime composition are
unchanged. This module provides no grant, consent, epoch mint/reset or permit
revival. Trusted composition must supply the existing canonical owner's actual
durable security epoch. An integer supplied by a fixture is no owner credential.

## Observations and trust

The provider loads Windows system DLLs through the system-directory search flag
and checks their actual loaded module paths. It records Windows version, module
file hashes and measured x64 structure sizes. On the observed Windows host,
the precise interrupt APIs resolve through the SDK realtime API-set to System32
KernelBase; the initial Kernel32 export failure is preserved. No arbitrary DLL,
interpreter, report, caller clock sample or wall-trusted Boolean is accepted.

Each acquisition brackets paired precise wall FILETIMEs, QueryPerformanceCounter
and frequency, precise biased/unbiased interrupt times and two native boot
observations. FILETIME conversion and QPC scaling use bounded exact integers.
The native time increment is queried without setting timer resolution. Integer
uncertainty includes wall pairing, entire native acquisition occupancy, observed
end-to-end acquisition/lock-return occupancy, counter rounding and a conservative
native resolution allowance. Overlong returns after a narrow native bracket are
also rejected. This measures
observation uncertainty relative to the trusted host clock; it provides no
external UTC accuracy/attestation against a hostile OS, administrator or time
source. Host OS, interpreter/library and privileged owner remain explicit trust
assumptions. Image file hashes do not attest loaded memory or confer authority.

Boot-information class90 has **EMPIRICALLY_OBSERVED_NATIVE_ABI** status. The
installed SDK10.0.26100.0 declares NtQuerySystemInformation but omits class90 and
its returned struct; Microsoft's public function documentation warns of future
change. NC1 checks current native status0, exact32-byte return, GUID at0,
firmware at16, flags at24, supported measured firmware1/2 and nonzero repeated
GUID consistency. It refuses missing/malformed/changed observations. Current
Windows10.0.26300 returned a stable native GUID. The exact observed OS build and
four system DLL file hashes are enforced by the pinned native API; changed
platform pins deny before registration. This is an OS-returned value,
not a random or arithmetic boot substitute, documented portable ABI guarantee
or cryptographic boot attestation. Independent review of the exact OS/DLL/ABI
pins and a selected profile decision remain necessary before activation relies
on those semantics. Other Windows builds or DLL updates require a fresh reviewed
pin/ABI cut and have no inherited qualification.

A fresh random session nonce is separately recorded and appended to the
native-GUID clock identifier. Restarted provider instances get different
session identifiers even when native boot GUID and durable epoch are unchanged.
That prevents old temporal deadlines from validating across sessions. Consumed
permits and durable epoch changes remain the canonical owner's responsibility.

## Currentness and invalidation

Native reads and publication are serialized; the previous accepted sample is
retained privately by the provider. Caller-provided history cannot replace it.
Acquisition bounds and maximum inter-observation gaps are explicit. Native
counter or wall rollback, changed boot/frequency/calibration, unavailable
witness, large wall discontinuity, and paired sleep-sensitive/active-time
discontinuity latch the first rejection. Missing observations remain unavailable
and never become measured zero. A real measured zero counter is represented as
zero when its other native contracts hold.

Once latched, the instance publishes no new pair and has no reset method.
Any new session/attributable epoch, recalibration and enrollment must follow the
canonical owner's actual policy and trusted admission path. Native availability
alone never opens the existing unqualified owner.

PowerRegisterSuspendResumeNotification owns an actual retained callback and
subscription structure. Native callbacks perform only a short state-lock update:
increment observed transition generation, latch invalidation and wake the owned
sampler. They read no clock and invoke no store, authority or user callback.
Suspend/resume codes and unknown witness events all invalidate. A transition
observed during acquisition prevents its publication. Native notification
registration proves availability/ownership; it does not prove every machine
sleep/resume transition has been observed. Real host suspend/resume is a separate
explicitly scheduled qualification obligation and remains NOT_EXECUTED here.

## Resource lifetime and recovery

One non-daemon sampler thread is owned by the instance and performs bounded
periodic acquisitions. Closing first rejects further reads and signals the
sampler, then cancels the exact native registration outside the callback state
lock. It observes thread retirement, outstanding acquisition retirement and
active callback count zero before CLOSED. Callback/subscription references stay
retained for the owner's lifetime even after native cancellation succeeds.
Unregister failure preserves the exact handle and callback; blocked sampler or
acquisition leaves its actual owner reachable. Close can retry those boundaries.
No destructor abandons native registration or silently closes in-flight work.

Windows/native calls are synchronous. Bounds reject observed overlong returns;
they do not preempt an arbitrarily blocked driver or Python callback. Failed
closure is explicit and retains custody. Constructor/read primary control
exceptions survive secondary cleanup failures, with the exact clock owner
attached when recovery remains required. A background read failure invalidates
the session and ends its sampler; it does not fabricate a healthy sample.

NC2 retains constructor recovery custody after diagnostics through the trusted
BaseException dictionary descriptor, bypassing a subclass's failing custody setter or
dictionary accessor. Diagnostic note lookup/calls are independently guarded,
including control exceptions from those diagnostics. The original primary
exception object is reraised with its exact owner attached; annotations are
best effort and cannot replace that primary or erase native recovery custody.

## NC3 selected platform

`CETA-NC3-WINDOWS-10.0.26300-20261015` selects one exact Windows x64 profile.
The three changed image hashes below replace the prior NC2 profile; no old/new
fallback set, wildcard, automatic refresh or version-only admission exists.
The historical private `_NC1_` constant names remain for unchanged test
compatibility. Public shapes, native call order and clock/lifetime behavior
remain the NC2 implementation.

| System32 image | Exact SHA-256 |
| --- | --- |
| kernel32.dll | e132eba4166256e2f414b91fe7d5386590bc5ea8626aee5af9c9738383cf2ae1 |
| ntdll.dll | 651ac9041af8e6b5ebd331d53163244c0a27d36d1433f0f15cac1f28c5f2e82c |
| powrprof.dll | 096b3c77ad7fece122be0362c72530b1edc024fe7107d1d40d8bcd8fa5428a0e |
| kernelbase.dll | 5c29b73622ce0976e1ada566f31f2197ba0f8beaea89c3ec033366126172c3d0 |

Qualification records whole-file hashes/native identities, file versions and
Windows-reported Valid Microsoft Windows catalog signatures before and after
the actual native tests. Runtime still checks the exact file bodies and
Windows10.0.26300 tuple; it does not run signature-chain verification on every
sample. Host-reported catalog trust does not establish who changed the files,
when they changed, why they changed, loaded-memory equality or host integrity.
The cause of the three changed bodies is UNKNOWN. The original mismatch and
NC2 qualification remain preserved; NC3 requires its own distinct review before
any dependent composition adopts it.

## Acceptance scope

Tests exercise actual native clock/boot/API observations, periodic sampling,
notification registration/unregistration and observed closure. Controlled
backend and native-event invocations separately exercise rollback, sleep/gaps,
errors, concurrent readers, slow returns and retryable cleanup; their fake
registration and epoch stand-ins establish no live authority or native event.
Original temporal tests remain byte-for-byte retained. Actual machine clock
adjustment, suspend/reboot, external UTC attestation, live canonical epoch
provisioning and real-effect admission remain unexecuted. The candidate requires
distinct Collaborative/adversarial review and separately reviewed publication.

Primary references: [precise system wall](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getsystemtimepreciseasfiletime),
[precise interrupt time](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryinterrupttimeprecise),
[precise unbiased time](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttimeprecise),
[power registration](https://learn.microsoft.com/en-us/windows/win32/api/powerbase/nf-powerbase-powerregistersuspendresumenotification),
[power cancellation](https://learn.microsoft.com/en-us/windows/win32/api/powerbase/nf-powerbase-powerunregistersuspendresumenotification),
[native query compatibility limits](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation).
