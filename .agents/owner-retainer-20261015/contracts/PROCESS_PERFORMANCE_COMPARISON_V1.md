# Process counter performance comparison

`CETA-20.05.02` maps to the additive
`PerformanceDiagnostics.compare_process_current()` in `diagnostics.py`.
It reuses `WorkloadComparisonInput`, `CurrentComparisonContext`, the accepted
owned process sampler, privacy projection recorder and existing current
comparison validation. Existing public operations and shared contracts retain
their signatures and behavior.

Inputs contain two nonempty, disjoint before/after measurement windows for the
same declared source digest, generation, scope, environment and workload digest.
Each window needs at least two observations. All sample and nested quantity
records are reconstructed as private immutable values before calculation.
Sequence gaps, duplicates/reordering, reused IDs, time rollback, stale/future or
incoherent constituent observations, missing process usage and cumulative
counter rollback across either window or their boundary reject both windows.
Recomputing identical pure inputs is deterministic; it dispatches no effect and
does not consume a canonical authority lease.

The result provides exact cumulative CPU time in100ns units and process read/write
transfer-byte deltas, sampled working-set/private-memory peaks, elapsed window
times, declared source/workload bindings and numeric measurement digests.
CPU rate is thousandths of one logical CPU; multicore use can exceed1000.
I/O rate is process transfer bytes per second; it describes neither physical
disk bandwidth nor exclusive storage allocation.

The required `timestamp_uncertainty_ns` is a caller-declared per-endpoint bound.
For first/last sample end stamps `t0,t1` and counter probe starts `p0,p1`,
duration bounds are `p1-t0-2u` and `t1-p0+2u`. The rate estimate uses `t1-t0`;
the conservative integer minimum rounds down over the maximum duration and the
maximum rounds up over the positive minimum duration. This includes acquisition
window occupancy as well as timestamp uncertainty. A nonpositive minimum
duration retains a measured total with explicitly unavailable rate bounds.
These bounds qualify supplied time facts; they authenticate no clock or source.

Measured zero is available. An unavailable counter anywhere in a window prevents
bridging that metric across the gap; independently measured metrics can remain
available and the result is incomplete. Counter rollback rejects the comparison.
An unavailable memory observation makes its sampled peak unavailable. A result
never fills an unknown metric with zero. Signed before/after rate differences
report increase/decrease only when conservative bounds are disjoint. Overlapping
bounds remain inconclusive; a difference is not a causal bottleneck finding.

Output excludes raw sample/workload IDs, PID, command line, paths, method/reason
text, prompts and credentials. Measurement digests bind the numeric/state/time
projection and declared source/scope/workload context, not suppressed text.
The existing recorder still provides keyed IDs, safe method/reason projection,
bounded retention and scope filtering. This analyzer adds no buffer, persistence,
principal authenticator, state store, issuer, scheduler or evidence ledger.

Cancellation returns a typed result with no measurements. Process control
exceptions propagate unchanged, with no mutation of the caller's source records.
Input work is bounded by the existing8192-sample-per-window contract. A missing
latency observation does not erase available process counter facts; the result
retains its explicit counter-comparison scope.

Native tests use fresh disposable Windows-owned jobs, named event barriers and
the same pinned CPU/read/write workload in both phases. Four accepted frames pass
through the actual sampler and recorder before comparison. Tests separately
qualify cached-frame rejection and unavailable data after observed process exit.
They do not assert improvement under concurrent host load. Deterministic tests
separately cover quantization/probe bounds, extreme integers, malformed nested
records, projection privacy, stale/source/window mismatch, rollback, interruption
and concurrent pure calls.

The scoped tests support the measured-before/after and no-guessed-cause cases
`AT-CETA-20.05.02-01/02`, input/currentness/bounds/duplicate slices03/04/06/07 and
the actual owned producer-recorder-consumer slice09. Principal separation05,
durable recovery08, distinct acceptance10, canonical evidence publication,
admitted workload execution, authenticated physical/time identity and full
latency/queueing/model/offline causation remain owner integration obligations.
The parent20.05 unit and product completion are separate from this finite slice.
