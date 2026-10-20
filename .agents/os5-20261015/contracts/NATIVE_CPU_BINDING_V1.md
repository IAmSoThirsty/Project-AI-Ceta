# Native CPU policy/time binding — version 1

CPB1 implements the observation-only timing seam of RE-S5/RE-T18/RE-T21. It
borrows one existing `WindowsOwnedProcess` and one exact `NativeSessionClock`.
It creates no authority, permit, state store, scheduler or policy mutation. The
native clock retains its existing empirical OS/ABI pins and trusted-host wall
assumption. A fixture epoch is data, never canonical owner authentication.

`NativeCpuBinding(target, clock, maximum_capture_ns=100_000_000,
cancel_event=None)` requires the observed Windows clock implementations:
Python monotonic `GetTickCount64()` and elapsed `QueryPerformanceCounter()`.
Unknown implementations, missing/nonfinite resolution or arbitrary clock/target
ports deny. The dependency WT4 already uses both clocks; this module bridges its
absolute driver timestamps to NC2 raw QPC sample time without changing WT4.

`capture()` obtains native samples around the original driver policy query,
retains the exact driver observation privately and returns `NativeCpuCapture`.
Its public `observation` is a distinct `CpuRateObservation` in the NC2 domain.
That native observation uses the earlier native sample minus uncertainty as
its conservative timestamp. Both original driver timestamp and the enclosing
driver/native samples, resolutions, duration and explicit domain names remain
available. Disabled policy DWORDs `0/0` are measured values. Unavailable policy
or clocks raise a typed denial and never become zero.

Only the exact privately retained capture object is current. Copies, another
binding, changed public values and superseded captures fail. One fresh capture
replaces the preceding one, permitting a later separately authorized restoration
to obtain a fresh observation. The binding never authorizes cap or restoration.
Private original policy/identity/time data are detached from public nested data.

`require_current(capture, request) -> None` snapshots a strict `OwnedCpuRequest`,
checks its exact native observation/identity/job binding and re-observes the same
retained worker. Policy/version/lifetime/membership changes, stale capture,
expired deadline, changed boot/epoch/resume/session, unavailable clocks,
rollback, slow observation, stop or closure deny. NC2 owns its actual power
notification/boot invalidation; this binding supplies no replacement epoch or
reset API. Conservative resolution/uncertainty can legitimately deny very tight
budgets. Synchronous native calls are measured on return, not preempted.

`driver_arguments(capture, request)` performs the same fresh checks and returns
frozen `CpuDriverArguments`. `expected` retains the original WT4 timestamp and
policy rather than the public native-domain timestamp. `keyword_arguments` is
a read-only mapping of driver deadline, maximum age and maximum duration.

For native enclosing bounds `Nlo/Nhi`, driver endpoint values `D0/D1`, and
driver quantum `r`, the measured offset interval is
`[Nlo-(D1+r), Nhi-max(0,D0-r)]`. Conversion never compares absolute elapsed/QPC
epochs. The current native deadline remainder is the minimum of conservative
native-monotonic and wall remainders, minus full uncertain acquisition and two
ceil elapsed-resolution endpoint charges. The driver deadline starts from
`max(0,D0-r)` plus that remainder. Driver observation age additionally subtracts
the bound relating the original driver timestamp to the retained older native
timestamp. Driver duration subtracts the entire current acquisition, both driver
endpoint quanta and both elapsed endpoint charges. Nonpositive allowances or
unrepresentable integers deny; time is never rounded up to create capacity.
The final elapsed read also charges local serialization/validation occupancy
after measurement. Cancellation/current native owner state is checked after
that read; a slow local return cannot reuse an earlier unspent time budget.

These are bounded same-host measurement data. Their freshness is qualified at
the inspected return boundary, not a future dispatch grant, portable clock-rate
attestation or guarantee across suspend/resume. Trusted composition must call
`require_current` with the same capture/request in the existing driver's final
pre-dispatch fence, alongside genuine canonical authority. The existing driver
must still perform its exact policy/version CAS, age/duration/deadline checks
and final native target checks. Delaying or copying arguments cannot replace
those checks. Native irreversible effects/independent outcome observation and
durable settlement remain separate components.

Binding and target locks are acquired nonblocking; nested/reentrant work denies.
Ordinary order is binding → target lifecycle → existing NC2 acquisition → short
clock-condition publication check. An existing driver fence already holds the
target lock; its binding lock acquisition is nonblocking and its target lock is
reentrant. No lock waits introduce a reverse blocking cycle. Final pure owner
state and cancellation checks follow all native/time callbacks. A close/stop
observed before publication vetoes it. `cancel()` and `close()` invalidate only
the binding; they never close, terminate, restore or replace either borrowed
owner. There are no destructor effects or hidden cleanup obligations.

Acceptance includes separately labeled deterministic clock-domain/adverse
fixtures and actual Windows medium-worker policy queries/NC2 registrations.
Native worker setup uses only the existing class9 containment setup on a fresh
owned job. Every class15 write is forbidden. Actual final-driver-fence tests
check the same capture/request and deliberately veto before any Set/version
spend. Synthetic power callback invocation is labeled controlled; actual host
sleep/clock adjustment, profile/Hello/enrollment, CPU effect, production
authority and public runtime acceptance are not part of this unit.
