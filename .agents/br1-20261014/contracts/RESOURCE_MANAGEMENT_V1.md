# Resource pressure observation ordering

`ResourcePressureDetector.observe(snapshot, current=...)` retains the shared
`CapacitySnapshot` and `PressureDecision` interfaces. It produces a local advisory
decision. Canonical admission, reservations, source authentication, publication,
and persisted recovery remain with their existing owners.

Each detector binds to the first snapshot's resource kind and all four
observation method strings. Use a fresh detector when replacing the sampler or
resource. The shared snapshot contains no authenticated physical-resource ID or
producer epoch; this binding cannot authenticate two devices behind one label.
Composition must establish the physical source and restore canonical uncertainty.

Recovery requires the configured number of distinct, coherent observations.
Each constituent timestamp must be equal within one sample and strictly advance
from the preceding accepted sample. Its sequence must also strictly advance.
Polling the identical immutable snapshot, or an equal copy, preserves recovery
progress. It never contributes another sample. Sampling-cache age is rechecked
on every call, including duplicate polling.

Currentness failure, unavailable utilization, stale or future observation,
incoherent timestamps, resource/method switch, changed content under one sequence,
sequence/time rollback, and clock rollback close the advisory gate and clear
recovery progress. They retain the accepted order bounds. The greatest seen
sequence and exact snapshot are retained as well: relabelling a previously
rejected cached observation as current cannot count as a fresh recovery sample.
Only a genuinely new observation can begin recovery again.

Replay state consists of two bounded shared snapshots, a kind/method tuple, a
clock bound, and the existing pressure/counter fields. The existing lock guards
clock sampling, stream ordering, duplicate detection, and the recovery state.
There is no growing observation registry or independently owned state store.

The SA2-01 regression suite covers immutable duplicates, altered-content replay,
sequence/time rollback, each constituent timestamp/method, currentness and
availability resets, resource switching, clock rollback, concurrent replay, and
the CPU/storage sampler caches. Disposable storage sampling executes the actual
host query. Synthetic pressure and counter readings remain labelled test inputs.

The mapped implementation is `src/ceta/resource/pressure.py`, logical unit
`CETA-20.04.01`. This repair supplies source-bound observations for the duplicate,
generation/order, bounded-memory, and producer/cache obligations. Independent
acceptance, physical source composition, canonical publication, and the remaining
unit acceptance cases retain their separate evidence requirements.
