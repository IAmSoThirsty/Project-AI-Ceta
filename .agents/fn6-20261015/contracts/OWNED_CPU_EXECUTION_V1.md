# Canonical retained CPU execution admission v1

KA2 implements the retained-admission library mechanics for RE-T16 through RE-T20 on the existing `KernelTransactions`
and captured `SqliteJournal`. It adds no grant issuer, policy engine,
scheduler, persistent store or evidence ledger. The default
`require_runtime_admission()` denial remains unchanged.

`KernelTransactions.owned_cpu_execution(request_wire, prepared_permit_wire,
native_binding, capture, native_proof, request_context)` returns a private,
single-entry context manager bound to the exact kernel, original request
thread and original opaque authenticated context. Construction, DTO fields,
copying, serialization, historical permits and recovered attempts do not
authorize execution. The exact typed request and CPB1 observation commitments
are retained; restoration is a separate approved request and permit.

The same captured owners must implement
`retain_owned_cpu_execution(request, prepared_permit, binding, capture,
native_proof, peer, original_context, kernel_coordinator)`. Its retained
context manager must implement `require_current(phase, request,
consumed_permit_or_none, attempt_or_none, binding, capture, native_proof,
peer, original_context) -> None`. Entry/exit must retain and settle exact native
custody; exit returns exactly `None` and cannot suppress primary exceptions.
The required phases are CAPACITY, CONSUMED, READY and DISPATCH. Only the
original context, exact private proof and actual selected kernel/coordinator
may pass. Missing, malformed, throwing or Boolean decisions deny.

This capability is an integration prerequisite. It must actually retain the
canonical authority/current-owner view, authenticated approval, cancellation,
revocation, native target/job lifetime, current source/environment, resource
limits and physical outcome-storage/queue capacity through dispatch and
observation. ET3 logical reserved bytes, free-disk observations or a test
Boolean are not physical-storage guarantees. No such production provider is
installed or qualified by KA2. OS2 is excluded while its independent repair
and qualification are pending. Positive providers in the tests are controlled.

Initial authentication, retainer creation, entry and capability capture share a
conservative measured 50 ms bound before consumption. Entry then checks
retained capacity and currentness and invokes the same
kernel's `consume` and ET3 `begin_owned_cpu_attempt`. Only exact consumed
event/index/head and the canonical charged reservation/attempt can yield a
lease. Existing cumulative evidence accounting remains in the same journal.
If consumption or attempt commits and a later callback/return throws, the
lease performs read-only recovery and exposes retained facts on the exact
primary exception. It never retries the failed command or dispatches after
that failed entry. Consumed liability remains charged.

The coordinator tracks volatile liveness and mutation occupancy only. KA3
registers each public mutation against both the exact captured owner object
and the exact captured canonical store object before invoking authentication,
SQL or another callback. Registrations retain those object references until
their `finally` retirement, including nested calls, denied authentication and
control exceptions. Ordinary concurrent mutations remain allowed outside a
selected execution lease; occupancy is not a second authority or store.
Preparation, consumption, grant revocation, enrollment/approval/Stop,
attempt/outcome writes and all three resource-reservation writers share it.
Previously created resource adapters resolve the same coordinator. Ordinary
transaction concurrency remains available outside an execution lease; an
in-flight mutation in any kernel sharing either captured identity prevents
entry. During a lease unrelated/reentrant writes
deny. Exact active owner/store object identities also prevent a second kernel
or coordinator from admitting against those same selected owners. This is a
trusted service-process liveness fence, not an OS-wide distributed lock or
permission registry. A future composition must preserve one canonical writer
and must not expose direct private store mutation as a public effect path.

Admission first checks availability, reads the exact prepared canonical
identity outside the metadata lock, then atomically rechecks both mutation
registries and both liveness registries while installing its own lease. A
mutation registered after the preliminary check wins against that admission;
admission registered first denies the competing mutation. A losing or nested
entry cannot release the winner's records, active lease or delegation. The
same short metadata lock protects registration and retirement only. No
global liveness or coordinator lock spans authentication, SQL, callbacks,
waits, context yield, native work or cleanup. The separate short Stop/dispatch
decision lock remains, and the native owner's required binding/target
lifecycle custody is retained. CPB1's nested binding/target acquisitions are
nonblocking; contention denies. No SQL transaction spans context yield,
native execution or a human wait. Canonical Stop/revocation first executes the SAME factored grant/enrollment,
reason, peer, current-owner and canonical state checks used by the existing
durable methods. Only the matching selected grant/enrollment/lease can latch
cancellation. Denied, forged-context or unrelated requests cannot gain Stop
authority. The exact original Stop request context is authenticated on its
receiver thread; the effect request context is never borrowed across threads.

The Stop lane takes no retained execution/native lock, refuses short journal
lock contention without waiting, and requires bounded nonblocking canonical
authentication/currentness. The controlled fixture uses separate retained
execution custody and short authentication locks while invoking the original
rights predicates. This does not qualify a missing live provider. The
canonical preflight fits the selected request's existing at-most-1s check
window; the existing owner-current callback retains its own 50ms bound.
Elapsed rejection is not preemption of a malicious blocking provider.

Authorized cancellation and irreversible dispatch linearize on the separate
short decision lock, also shared with lease retirement. During a retained
lease, cancellation reports CPU_EXECUTION_CONTROL_DURABLE_PENDING with exact
lease custody, immediate_cancellation=True, durable_completed=False and the
observed admission side. It has performed no durable revocation. After lease
release, a newly authenticated control request may complete the original
durable Stop/revoke path. This never repeats native dispatch or refunds the
consumed permit. The private retained lease.cancel remains a cancellation
capability for its selected trusted owner, not public caller authority.

`lease.dispatch()` accepts no caller arguments. It uses the exact captured
approved WT4 method/function, owned target, immutable request limit and CPB1
driver translation. The exposed fence denies unless armed by that dispatch.
Copies of returned argument data cannot change retained arguments. Recursive,
cross-thread, second and cross-kernel dispatch do not issue a second native
Set. A returned native change is bounded effect data, not independent proof.

At the last WT4 fence, fallible authentication, native binding, canonical
state and retained-owner checks complete before the final decision. Exact
consumption and attempt history are audited before context yield. The final
dispatch rechecks every audited canonical dependency cell, stream/store head
and mutation generation under that retained single-writer owner. It does not
replay the same immutable history a second time inside the native operation;
arbitrary direct SQL writes are outside this trusted composition boundary.
The native owner callback has a conservative 50 ms occupancy bound. The
complete check, including canonical auditing, is separately bounded by the
request's native duration for each complete check. The separately charged
canonical operation wall budget bounds the complete retained admission,
including time between checks. Its finite wall budget is distinct from the
maximum native-effect duration; neither time allowance restarts on a check. The request deadline and the potentially earlier canonical
intent/permit deadline must both remain strictly current in monotonic and
wall domains after the last callback; equality denies. Current native time
and the initial sample plus cumulative high-resolution elapsed time supply
conservative age/deadline bounds, so repeated fresh checks cannot restart
the admission duration or extend either deadline. Clock rollback never lowers the
retained high-water marks. No independent callback follows the final Stop
decision before WT4's retained native-field check and sole class15 Set.

Stop and logical dispatch admission linearize on that short decision lock.
Stop winning first denies Set. Stop following admission disables later work;
it cannot preempt a synchronous native call or erase a possible delivered
effect. Native ambiguity/control exception spends the one attempt, retains
the exact native change/custody and requires independent observation or
reconciliation. A permit, process exit or successful return is not settlement.

`lease.record_outcome(receipt_wire, observation_wire, native_proof)` delegates
to the existing ET3 owner and independent proof predicate. It does not mint a
receipt, observer identity or refund. Absence of telemetry remains uncertain.
`inspection()` returns historical/custody facts only. Failed retained-owner
entry/exit keeps explicit pending custody and blocks further admission;
cleanup is not blindly replayed. Base-exception storage preserves exact
custody even if attribute/note hooks refuse diagnostics. If cleanup also
throws, exact secondary identity remains in owned_cpu_cleanup_failure on the
original primary and cleanup_failure in lease inspection.

Actual disposable Windows tests cover native cap, distinct controlled-approved
restoration, final Stop with zero Set, and a real Set followed by lost return
and read-only reconciliation. Those tests use actual NC3/CPB1/WT4 resources
but controlled approval/capacity and controlled canonical settlement proofs.
They do not qualify genuine owner authentication, independent outcome
observation, physical-storage durability, isolated-worker launch or public
runtime activation. No profile operation or Hello prompt is run.

The actual-native controlled fixture declares a 5 s operation wall budget
within its existing authority/recovery allowance, while retaining the 1 s
native-effect bound. Its earlier 1 s canonical intent legitimately expired
during the larger restoration-history audit and is preserved as a failed
qualification attempt. The literal default-1 s intent-expiry and cumulative
wall-budget regressions remain unchanged. No production bound was widened.

Exception custody uses the unbound built-in dictionary operations even when trusted BaseException storage is a dict subclass. Refused dictionary, attribute and note hooks cannot replace the original control exception or remove the exact retained lease, native target, ambiguous change and secondary cleanup failure. Fixture teardown marks its one attempt before native cleanup and uses the same non-hookable storage for response-loss custody.

The selected grant and original intent deadline are read from the exact canonical PREPARED permit/intent and proposal before the active lease exposes native-owner, authentication or capacity callbacks. An authorized matching canonical Stop during CAPACITY therefore cancels before consumption; denied or unrelated requests do not acquire cancellation authority. After consume returns, both canonical grant and deadline must still equal that retained prepared identity. Early cancellation retains the PREPARED reservation, makes no native call and reports durable Stop completion pending; a later separately authenticated durable Stop remains a separate operation.

KA3's focused qualification uses disposable canonical SQLite journals and
controlled, nonnative owner/target fixtures. The original KA2 native methods
and evidence remain historical, byte-exact dependencies. A fresh connected
qualification must bind the accepted Source292 transition before claiming
live-source conservation; it cannot borrow historical Source290 equality.
No new native-effect, profile or Hello cohort is authorized by this repair.

KA4 repairs the measured partial-registration interruption boundaries. Each
mutation owns one private volatile invocation object. The owner and store
rows contain that exact invocation set; their existing identity and count
tuple positions remain stable. Retirement begins before either publication
and removes only the current invocation from each independently present row.
The local count is derived from the coordinator's exact invocation set, so
an interrupted local assignment cannot decrement a concurrent or nested
invocation. No authentication, SQL or external callback executes while the
metadata lock is held. This is same-service-process occupancy, not authority.

An interrupted active claim retires only its exact owner/store/coordinator/
lease rows. Release tolerates a missing partner and preserves an unrelated
winner. A release failure keeps the exact lease pending and preserves the
original exception plus the exact secondary; a completed native-retainer
exit is not replayed. Mutation retirement failure similarly retains the
exact invocation and secondary on trusted BaseException storage, without
calling overridden attribute, dictionary or note hooks. Remaining uncertain
rows continue to deny entry; no public recovery or automatic replay is added.

Qualification injects one control exception at each declared Python line
boundary in bounded owned test interpreters, using actual disposable canonical
SQLite and controlled authority/nonnative targets. It does not establish
arbitrary-opcode interruption safety, natural signal occurrence, native-effect
acceptance or a production owner provider. The original seven native methods,
joined/full regression and current-Source integration remain separate gates.

KA5 retains the exact already-computed timing terms when initial admission or
the retained-owner callback exceeds the unchanged 50,000,000 ns bound. The
original `CPU_EXECUTION_ENTRY_TOO_SLOW` or `CPU_EXECUTION_OWNER_TOO_SLOW`
`ContractError` carries `owned_cpu_timing` in trusted BaseException storage:
`phase` (`ENTRY`, `CAPACITY`, `CONSUMED`, `READY` or `DISPATCH`), `elapsed_ns`,
`bound_ns` and `resolution_ns`. The elapsed value includes the existing two
clock-resolution allowances; it is the conservative term actually rejected.
The helper does not query a clock, change the inclusive bound, reorder owner
callbacks, authenticate authority or authorize retry. Refused diagnostic hooks
cannot replace the original rejection or its lease/cleanup custody. If
diagnostic allocation itself fails, the original rejection remains primary.

The three pure codec modules are reconciled byte-for-byte with the separately
reviewed ER1 optimization. This is dependency reconciliation, with zero new
implementation credit; its effect on native timing has not been measured in
KA5. The failed KA4 native attempt and its unknown elapsed terms remain
preserved. The original seven native methods remain unchanged and NOT_RUN in
this successor, pending distinct review and a separately authorized attempt.
