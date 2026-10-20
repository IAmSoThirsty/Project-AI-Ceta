# Same-journal physical outcome capacity

Requirement binding: RE-T27 and RE-16/RE-30, SPEC-07 REQ-07-01/02/05,
CMP-03 canonical store. This implementation extends the selected writer and
keeps its existing event/state schema. Its allocations confer no authority.

`OutcomeCapacityRuntime(path, sha256)` is an explicit composition input. It
loads a hash-checked native helper, verifies the actual loaded module path and
ABI, and registers a unique wrapper around the already selected SQLite 3.53.4
win32 VFS. The helper cannot substitute a second SQLite engine. A journal opts
in with `outcome_runtime=runtime`; existing constructors retain their original
behavior. An unconfigured journal rejects capacity reservation.

The Python VFS owner, native token output slot and snapshot buffer are allocated
and retained by the journal before native registration. A failed registration
response exposes that exact owner and its output slot without assuming that
registration failed. Snapshot allocation failure occurs before registration is
attempted. An interruption at the registration method's return preserves the
already retained owner; constructor cleanup observes its actual first-close
result and exposes the original primary error with capacity custody.
Failed VFS destruction exposes the retained capacity owner; ordinary journal
closure also exposes the journal. Repeated closure is denied with the original
cleanup error retained, without invoking native destruction again. The SQLite
connection's known closed state remains separate from VFS closure uncertainty.

`journal.reserve_outcome_capacity(OutcomeCapacityBudget(...))` creates a
single-use context manager. Entry allocates one bounded memory slot and retains
the actual DB, WAL and SHM files. Native volume/file identifiers must match the
SQLite DB/WAL handles and the file backing SQLite's actual SHM mapping. Sparse,
compressed, reparse, delete-pending, multi-link, changed-identity and oversized
files fail closed. Absolute ceilings are aligned to 64 KiB and total at most
64 MiB per reservation; memory is at most 1 MiB. Allocation is measured through
native file information after `FileAllocationInfo` and flush. Existing bytes
and EOF are preserved at reservation entry. Zero capacity is never used to
represent an unavailable observation; failures have explicit error states.

The VFS fences DB/WAL writes and SHM map growth to the retained ceilings,
disables memory-mapped DB access and handle-replacement/NULL_IO controls, and
rechecks actual allocation after writes. A truncation that releases allocation
must restore the same file's allocation before returning success. Failure
latches and blocks subsequent writes. SQLite's advisory SIZE_HINT alone is
never treated as reservation proof. Cached `require_current()` uses a retained
snapshot buffer and nonblocking native locks; it performs no SQL or physical
file query. Explicit `measure()` is forbidden inside a SQL transaction.

The journal holds its existing lock only while entering the reservation and
performing ordinary commits. No SQL transaction or journal lock survives into
an external effect. Competing writer threads are denied while capacity belongs
to the original thread. Commit notifications retain the reservation captured
under the writer lock, so a later reservation cannot capture an earlier commit.

The trusted effect integration must call `mark_may_have_executed()` before
dispatch. It stages the exact canonical outcome payload tuple through
`stage_outcome()`. Only the existing journal's successful COMMIT of that exact
tuple sets the lease's durable observation. An unrelated transaction or caller
success Boolean cannot release the slot. `__exit__` retains unresolved bytes
and capacity, prevents journal closure/new reservation, and signals uncertainty
to explicit context-manager callers. An original body exception is re-raised
unchanged in identity with custody and cleanup details attached. Unknown
retirement is never retried automatically. A matching later journal commit can
be followed by `finish_reconciliation()` on the original owner thread.

The optional same-owner view adapter, final dispatch hook, and exact outcome
payload staging at `KernelEffectTransactions` remain integration work. This
storage implementation and its controlled phase markers do not satisfy actual
human authorization, native action, independent observation or full RE-G3/G4
acceptance. Native tests exercise the real canonical STORE_PROFILE writer,
files, capacity limit, failed commit, reconciliation and reopen mechanics.

Allocation is a measured prerequisite, not a guarantee against disk/device,
filesystem, power, trusted-host or later external modification failures. A
post-effect write/sync failure remains unresolved. The bounded memory slot is
volatile; the existing durable intent is the recovery authority after process
loss. No emergency spool, second ledger, policy engine or scheduler is added.
The helper retains at most 256 VFS address tombstones per process; exhausting
that bound returns unavailable rather than reusing an uncertain address.

Native interface references: [SQLite VFS](https://sqlite.org/c3ref/vfs.html),
[SQLite file methods](https://sqlite.org/c3ref/io_methods.html),
[SQLite file controls](https://sqlite.org/c3ref/c_fcntl_begin_atomic_write.html),
[Windows file allocation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_allocation_info).
