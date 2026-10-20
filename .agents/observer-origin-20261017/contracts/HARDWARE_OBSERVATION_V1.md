# Hardware observation v1

`src/ceta/resource/hardware.py` implements CETA-20.01.01, CETA-20.01.02 and
CETA-20.01.03 as local Windows observations. The shared resource-management
contracts, pressure detector, budgeting controllers and reservation port retain
their existing owners and public shapes.

`WindowsHardwareProfiler.profile()` observes CPU capability, physical memory,
storage, static adapter memory and current process job membership. It serializes
the entire profile probe and emits one sequence with a conservative common
start timestamp. Its wrapper timestamp is the observed end of the probe.
A rollback or overlong probe emits unavailable quantities for the entire profile.
Measured zero remains a measured value. Static adapter memory and global logical
processor count provide capability information; their runtime availability stays
explicitly unavailable until a corresponding runtime observation exists.

`WindowsComputeAvailabilityMonitor.sample()` observes aggregate idle CPU through
`GetSystemTimes`. The native implementation verifies exactly one active processor
group with a processor count matching the aggregate before and after reading the
counters. On machines with more than one group, missing group APIs, mismatched
counts or a scope change, availability is unavailable. It does not scale one
group's idle fraction by the whole-machine processor count. Microsoft documents
that `GetSystemTimes` covers the calling thread's primary group on machines with
more than 64 processors. Its kernel counter includes idle time.

- [GetSystemTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes)
- [GetActiveProcessorGroupCount](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getactiveprocessorgroupcount)
- [GetActiveProcessorCount](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getactiveprocessorcount)

A valid CPU frame contains exactly two bounded integer counters, aggregate and
idle. Idle cannot exceed aggregate. Measured intervals require advancing total,
nonnegative idle advancement and idle advancement no larger than total advancement.
Invalid, nonadvancing, failed, interrupted or temporally rejected frames discard
the derived baseline. Recovery starts with a new valid baseline. A processor-count
change or an interval exceeding the configured maximum also establishes a new
baseline. A valid zero idle delta means measured zero available CPU.

`StorageCapacityMonitor.sample()` anchors its declared path at construction,
observes `shutil.disk_usage`, validates bounded total/free bytes and retains the
configured cancellation, recovery and evidence reserve separately from free bytes.
If a reader supplies used bytes, used plus free must equal total. The existing
declared total/free-only reader interface remains supported. Missing, malformed,
failed or interrupted observations never become measured zero.

All sampler clock reads, native probes, cache decisions and publications occur
under the instance's lock. Cached polls retain the exact immutable object,
sequence and constituent timestamps. A clock rollback discards usable cached
capacity and preserves the clock high-water. It cannot refresh an old measured
observation. Sequence and quantity fields retain the shared 63-bit bound.

The existing `SamplingPolicy` defaults remain unchanged. Its optional
`maximum_probe_window_ns` resolves to the smaller of maximum age and one second.
Its optional `maximum_sampling_interval_ns` resolves to maximum age. Both require
positive bounded values; the sampling interval cannot be shorter than the minimum
poll interval. Control reserves are bounded nonnegative integers.

Public timestamps remain in the existing `time.monotonic_ns` domain. On the
default native path a separate `time.perf_counter_ns` elapsed clock checks probe
duration, cached observation age, minimum polling intervals and CPU baseline
intervals. A maximum sampling interval also expires a cache before maximum age
when configured to be shorter. This prevents a
coarse public clock tick from qualifying a small physical elapsed bound. Both
clock high-water values are monotonic; rollback is explicit unavailable.
An explicitly injected clock defines its caller-supplied observation domain;
such controlled test clocks do not authenticate production time. Consumers using
only the shared public timestamp must account for their clock resolution when
setting age policy. The installed Python 3.12 environment reports 15.625 ms
resolution for its GetTickCount64 monotonic clock and 100 ns for its QPC elapsed
clock. These are recorded environment observations rather than platform constants.

Sampling is synchronous. A probe window controls acceptance after a native call
returns; it does not preempt a stalled Windows API or callback. No background
worker, alternate scheduler, reservation store or authority issuer is introduced.
`KeyboardInterrupt` and `SystemExit` propagate and invalidate derived cache or CPU
baseline state. Ordinary failed probes emit fixed reason codes without paths,
adapter descriptions, process identifiers or exception bodies.

`available_capacity()` subtracts supplied reservations from the single measured
reservable dimension only when the shared snapshot is recent. It cannot infer
other resource dimensions. Pressure classification uses utilization and its
existing distinct-observation hysteresis. A pressure recommendation permitting
admission still requires the owner's budget checks and atomic reservation. A
measured zero-byte volume supplies zero allocatable storage for nonzero workloads.

Native tests observe owned disposable files, real storage capacity, real Windows
CPU counters, the real profiler, and the existing pressure consumer. They also
exercise the real admission controller's denial path while forbidding reservation
dispatch. Declared reservation quantities in subtraction tests are domain inputs;
they do not prove a production reservation owner.

Canonical profile register/resolve/supersede, authenticated resource and producer
epochs, scope-controlled publication, reservation lifecycle and evidence admission
remain integration requirements. Current contracts do not expose authenticated
storage volume identity, independent quota/staging/snapshot commitments, thermal
headroom, process/worker affinity admission or runtime accelerator free capacity.
Those gaps cannot authorize a workload. Physical observations supply facts to
canonical owners, which must combine all required dimensions and current policy.
Distinct review and destination regression are required before active application.
