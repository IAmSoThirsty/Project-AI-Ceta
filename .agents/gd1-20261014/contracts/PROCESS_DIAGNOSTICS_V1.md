# Owned process operational diagnostics

`CETA-20.05.01` and `CETA-20.05.02` extend the existing telemetry recorder and
performance analyzer. The native producer is the existing `WindowsOwnedProcess`.
Observation reads its retained process handle under the lifecycle lock, with
PID, creation FILETIME, image digest and liveness checks before and after reading.
It opens no arbitrary PID, duplicates no handle, and changes no process state.

`resource_counters()` returns typed CPU-time, working-set, private-commit and
read/write I/O counters. CPU time uses 100-nanosecond units; I/O uses cumulative
process transfer bytes. Working-set and private-commit bytes stay separate.
These are process measurements, not exclusive physical memory ownership, disk
allocation, causal bottleneck proof, or a resource reservation.

`OwnedProcessTelemetrySampler` binds one verified lifetime, scope, environment,
workload digest and caller-provided canonical source generation. It samples on
demand, keeps one cached sample, one CPU baseline and three counter bounds, and
serializes observation using a lock. `collect()` retains that same producer lock
through admission to the existing recorder, so concurrent collections retain
distinct frames in producer order. Lock acquisition proceeds from sampler to
the native owner during observation, then to the recorder during retention;
those implementations do not call back into the sampler or reverse that order.
An interrupted recorder admission releases the lock, and a retry can retain the
exact cached frame without creating a second observation.

A cached sample retains its sequence and timestamp. A lightweight lifetime check
precedes cache reuse; a fresh clock reading after that check decides eligibility.
An elapsed check beyond the probe window returns explicit unavailable values
before reuse or a new counter probe. The configured
minimum interval bounds counter probes; age and probe-window limits reject old,
future or slow observations. Native API occupancy depends on Windows; the
sampler rejects an observed overlong window rather than claiming a hard native
deadline. Cancellation prevents a new counter probe and clears the CPU baseline.

The first CPU rate is explicitly unavailable. Subsequent rates use cumulative
CPU delta divided by monotonic elapsed time, in thousandths of one logical CPU.
Multicore rates can exceed 1,000. Measured zero is valid; API failures, stale
identity, dead/closed lifetime, clock/order/counter rollback and unavailable
values remain explicit. Invalid frames preserve accepted order/counter bounds.
Identity, lifetime and counter-query `OSError` failures return explicit unavailable
observations stamped after the failed call, and clear the CPU baseline. Process
control exceptions propagate unchanged and also clear that baseline. A sampling
gap or failed query requires a fresh CPU baseline. The observed lifetime check
and freshness bounds describe the observation window; they do not guarantee a
process remains alive after the check or a hard operating-system call deadline.

The native default sampler retains the existing `monotonic_ns` timestamp domain
and independently measures elapsed lifetime checks and counter probes using
`perf_counter_ns`. On this qualified Windows Python, those clocks report
GetTickCount64 and QueryPerformanceCounter respectively. Both public and elapsed
clocks maintain persistent high-water values under the sampler lock. A rollback
returns unavailable values with the observed public timestamp; it never lowers
the retained high-water or accepted counter/order bounds. The elapsed check
includes public-clock lookup time, lifetime checking and the entire counter
return. A zero public tick delta cannot satisfy a smaller physical bound by
itself. This is rejection of late synchronous returns, not native preemption.

Cache reuse requires current identity/lifetime, a fresh post-check clock reading,
and an elapsed minimum-interval/maximum-age check measured from the beginning of
the accepted sampling call. Public age also includes the declared monotonic
clock resolution as a conservative quantization margin. An age limit smaller
than that resolution produces unavailable observations. Unavailable frames keep
stable IDs while their same-reason cache is eligible; duplicate polling does not
create measurements. A custom injected clock remains a declared test or caller
time domain with its previous rate semantics and gains no native authentication.

On the native default path, sampled CPU rates divide actual cumulative CPU delta
by the precise elapsed interval between completed accepted probes. Rates are
averages over those sampled windows, in thousandths of one logical CPU; they do
not identify a causal bottleneck or eliminate bounded counter-read jitter.
Either an expired precise interval or an expired public interval including its
resolution margin requires a new CPU baseline. First-baseline CPU remains
unavailable while independently measured memory and cumulative I/O can remain
available. Failed queries and control exceptions preserve sequence/order/counter
high-water state; interruptions in observation invalidate the reusable frame
and CPU baseline. Recorder admission interruption still permits retry of the
exact completed frame, under the established sampler-to-recorder lock order.

Timing-state mechanisms adapt the same repository's qualified hardware sampler
high-water and independent elapsed observation approach into the existing
process sampler. They create no clock authority, state store, scheduler, durable
cursor, evidence publication service or resource reservation. Native tests use
retained disposable Windows job handles, explicit sub-tick scheduling delays,
an actual CPU/allocation/I/O workload, cancellation/interruption and measured
recovery. Deterministic timing injection is labelled separately from those
native observations. Canonical publication, principal separation, causal
analysis and model/offline qualification keep their existing open obligations.

`TelemetrySample.process_usage` is an optional defaulted pure-contract extension.
All prior sample fields and call patterns remain available. The existing
`ResourceTelemetryRecorder` validates, fingerprints, projects and retains these
measurements in its existing bounded buffer. Sample IDs remain keyed recorder
tokens; raw PID, creation time, command line, paths, prompts and credentials do
not enter retained telemetry. Unknown method/reason strings are redacted before
retention. Cumulative I/O is not converted into `storage_bytes`; process storage
allocation and workload latency remain explicitly unavailable in this producer.

`PerformanceDiagnostics.analyze_process_current()` reads the recorder's retained
samples, reuses current scope/environment/time checks, and rejects missing
source context, mixed epochs/workloads, duplicate/gapped sequence, time rollback,
missing counters and counter rollback. It returns measured I/O deltas and private
memory peaks alongside the existing CPU/memory/latency analysis. Alternative
causes, canonical evidence publication, authority, durable recovery cursors,
workload latency/queueing and full offline qualification remain separate owner
integration obligations.

Native tests use only explicitly created disposable Windows job children. They
execute a pinned CPU/allocation/I/O workload, measure before and after, exercise
read failures and concurrent cached collection, verify lifetime fencing, and
observe exit before closing owned resources. The deterministic injected counter
source is labelled as a test source.

Native API references: [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes),
[K32GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo),
[PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex),
[GetProcessIoCounters](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters).
