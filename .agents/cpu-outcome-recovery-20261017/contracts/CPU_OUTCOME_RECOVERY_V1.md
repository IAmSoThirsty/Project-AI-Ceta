# Original CPU invocation outcome recovery

This change implements the in-process portion of RE-T26/27/29 in the existing
real-effect implementation and acceptance plan. It uses the original kernel,
native retainer, authenticated context, thread, consumed permit, and SqliteJournal.

## Public capability operations

`with execution.recover_outcome(original_context) as execution:` obtains a new
bookkeeping borrow after the original exit failed or after a durable UNCERTAIN
or DISCREPANCY result. It reacquires one verified level of each original native
lifecycle lock. Each borrow and exit is single-use. At most 32 recovery attempts
are retained; unknown lock retirement remains pending. The original errors and
retirement records remain available in inspection. Dispatch, driver arguments,
consumption, and approval renewal remain unavailable through this borrow.

`execution.record_outcome(receipt_wire, observation_wire, original_native_proof)`
retains its existing provenance requirements. A failed write retries the exact
final journal entries, checks, projection changes, and original heads captured
before the first COMMIT attempt. Receipt or observation replacement is rejected.
The fresh authorization/identity/provenance and classification guards run again.

A successful SQLite COMMIT followed by an interrupted capacity notification is
recovered by a read transaction on the same journal. Recovery validates the
complete history and store chain, exact previous checkpoint, exact transaction
wire, events and payloads, successor heads, and changed projections before
acknowledging durable capacity. Retained bytes alone cannot establish durability.

An exact retry of a previously durable outcome writes nothing and allocates no
new physical capacity. Advancing reconciliation retains the original receipt and
consumed permit, requires the existing independent observation rules, and obtains
a fresh reservation on the same writer immediately before staging its final
canonical bytes. Cumulative evidence accounting is unchanged.

`execution.record_denied_outcome()` uses an immutable origin captured within the
original captured WT4 method's exception boundary, before final dispatch admission.
It proves this invocation did not pass that fence. A caller flag or an older CPU
change cannot provide this origin. The record has NOT_STARTED effect status and
an UNCERTAIN settlement with no observation; it does not claim a measured result.

`execution.retire_failed_entry(original_context)` handles the exact unconfigured
capacity path: no returned physical lease, no selected VFS/reservation, no attempt,
consumption, or dispatch, original context/owner custody still current, all lock
borrows retired, and canonical permit still PREPARED. It retires only this proven
empty custody and preserves the original entry error and prepared permit.

## Verification boundary and remaining requirements

The targeted cohort uses actual canonical SQLite transactions with explicitly
controlled native identities, approval, observer provenance, and VFS state. It
executes no worker, CPU Set, Hello, profile creation, or native observer process.
Independent review and native integration qualification are required before
source publication or production acceptance.

This in-process capability requires the original live native context. It cannot
reconstruct that authority from a serialized receipt, PID, new context, or caller
assertion. RE-T25 surviving supervisor/crash custody and RE-T26 cross-process
restart recovery remain separate integration requirements. RE-T28 restoration
continues to require its separate request, approval, and permit.

An expired or changed pending observation/provenance that fails the current
canonical guard stays pending; the stored transaction is not rewritten into a
different verdict. Unknown physical release, unresolved native-lock retirement,
failed journal cleanup, and ambiguous liveness retirement remain visible custody
issues. Fresh reservation failures that cannot prove exact retirement retain
their original capacity objects. These paths require separate qualified recovery;
no automatic release or raw journal write is exposed as a remedy.
