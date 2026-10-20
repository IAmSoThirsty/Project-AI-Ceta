# CPU execution connection to physical outcome capacity

Scope: RE-T27, the existing canonical CPU execution path and selected journal.
Canonical owners remain NativeOwnerView, NativeCpuOwnerSession, KernelTransactions,
KernelEffectTransactions and SqliteJournal. This connection adds no state store,
authority issuer, evidence ledger or scheduler.

NativeOwnerView accepts an optional keyword-only OutcomeCapacityBudget. Existing
positional construction remains valid. Missing configuration, an unconfigured
journal, a memory slot smaller than required_outcome_bytes, changed configuration,
or a mismatched owner, request, original context, thread, kernel or store denies
the physical reservation before consumption. Composition must explicitly provide
the approved OutcomeCapacityRuntime to the SAME canonical journal at construction.
The view does not discover or load a helper on behalf of composition.

The retained capacity adapter is noncopyable and binds the exact existing kernel
invocation and native owner retainer. It enters OutcomeCapacityLease before permit
consumption and the attempt commit, retaining the DB/WAL/SHM allocations and full
bounded outcome-memory slot across both commits and dispatch. No SQL transaction
or journal lock is held over the native effect. Final checks use the approved
cached native-state operation, with no physical query, SQL or new allocation.
Competing writer threads remain denied by the original reservation.

The NativeCpuOwnerSession dispatch fence requires the bound adapter and invokes the approved
mark_may_have_executed before its final short Stop/dispatch decision. All capacity
callbacks finish before that decision. If Stop wins after the conservative mark,
dispatch is refused and capacity remains unresolved for explicit reconciliation.
This preserves uncertainty instead of claiming that a marked effect occurred.
The mark is included in the existing measured dispatch interval; an overlong
mark also refuses dispatch and preserves pending custody.

KernelEffectTransactions finishes its existing cumulative accounting and record
construction first. For OUTCOME it stages EXACTLY tuple(entry.payload_wire for
entry in entries) and passes those same final entries to the same journal commit.
The existing journal's successful COMMIT and exact-payload comparison alone mark
capacity durable. Failed commits retain the slot, original exception and exact
capacity/journal custody. Context exit does not release unresolved storage, and
normal journal close remains denied. There is no automatic dispatch or commit
replay. After Stop, authenticated outcome bookkeeping remains possible without
reactivating approval or permitting another dispatch.

Generic owner-port callers preserve their original contract only when no physical
reservation or adapter is selected. NativeCpuOwnerSession and subclasses always
require the exact bound adapter, and any selected physical reservation also
requires it. An absent real observer-origin
predicate still produces OWNER_EXECUTION_PROVENANCE_UNAVAILABLE in the unchanged
native owner session. This connection neither creates that predicate nor treats
a controlled test predicate as production provenance.

Exact retries of the first durable outcome remain no-write returns. Advancing
an UNCERTAIN or DISCREPANCY observation requires a new qualified canonical
reconciliation reservation; this connection explicitly rejects reuse of the
already durable one-shot slot. That reservation/recovery composition remains
pending integration. Likewise, Stop or timing denial after the conservative
mark preserves the original capacity and pending native/kernel owner. The
existing lease refuses finish_reconciliation without a matching durable commit;
no public, authorized recovery entry is supplied here. Direct raw journal writes
are not an authorized public recovery operation. Later integration must retain
the original authority/current-context checks and retire exact pending custody.

The default test cohort uses actual canonical SQLite/kernel commits and the real
capacity lease/adapter, with explicitly controlled VFS state, identity, approval,
producer and observer facts. The separate native cohort uses the pinned real VFS
and disposable Windows files; its CPU/authorization/provenance facts remain
controlled. No cohort claims a real CPU effect or full authorization-to-effect
acceptance. Native qualification and independent review remain separate gates.

Allocation ceilings bound observed physical capacity and writes; device failure
and later external modification remain possible. Failed commits and ambiguous
dispatch remain explicit recovery work. A test's deliberate no-effect fixture
disposal is recorded separately from product reconciliation.

OS6 adds ADMISSION to the same retained capacity adapter. This phase accepts only
the exact PREPARED permit already captured by that adapter and kernel execution,
with consumption attempted, no returned consumed permit/attempt, no dispatch and
no recovery. CAPACITY still requires consumption not yet attempted. The native
owner uses ADMISSION initially and at the canonical consume commit guards; it
does not create another reservation, mark an effect, or treat PREPARED data as
permission. The original cached-state/currentness and cancellation fences remain
in force. Tests over the deterministic VFS are controlled integration evidence;
they establish no physical-storage or native execution qualification.
