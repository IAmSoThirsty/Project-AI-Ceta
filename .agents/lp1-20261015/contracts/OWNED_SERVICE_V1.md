# Owned development service and recovery, v1

This contract describes the development composition through Increment 28 in
this `rebuild_ios` checkout. Its status is IMPLEMENTED_NOT_QUALIFIED. The
Increment 24 source table and execution history below remain historical cuts;
Increment 26's separately preserved receipts bind its actual source and ledger
state. This document does not establish original acceptance completion,
installed qualification or a finished product. Positive preparation, admission,
revocation and effect authority remain CLOSED in the identity-only composition.

## Entry point and dependencies

The native operator opens model-free development task controls by default. Use
`--inspector` to open the existing typed record inspector. Run it with
this checkout's Windows x64 CPython 3.12 environment:

```powershell
& 'T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios\.venv\Scripts\python.exe' -B -X utf8 'T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios\tools\ceta_operator.py'
```

Without `--profile`, `tools/ceta_operator.py` creates a new UUID directory under
`rebuild_ios/.local-test-output/operator-24` and explicitly creates a development
journal there. To inspect an existing compatible development journal, use its
actual absolute path with `--profile`; the directory must already exist beneath
this checkout's `.local-test-output`, and the journal is opened with
`create=False`. The operator uses `installation:operator-development` and
`project:operator-development`; an unrelated or differently scoped profile is
not selected automatically. No normal user profile, service installation,
autostart, model, signing key, external endpoint or resource effect is selected.

The declared UI dependency is PySide6-Essentials 6.11.2. The D-specific
`contracts/dependencies/native-operator.lock` pins that package and shiboken6
6.11.2 to exact public wheel SHA256 identities. If dependency installation is
needed, the command for this environment is:

```powershell
& 'T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios\.venv\Scripts\python.exe' -m pip install --require-hashes --no-deps -r 'T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios\contracts\dependencies\native-operator.lock'
```

These are documented commands, not commands executed by the documentation
writer. The lock's availability does not establish installed UI qualification.

## Captured ownership and public seams

`OwnedService(profile_root, codec, installation_scope_id, scopes, *, create=False,
startup_seconds=15.0, call_seconds=4.0, principal_id="operator:development",
session_id=None)` owns one development client and one service. Its public calls
are `start()`, `begin_call(record_wire, operation, *, reason_ref=None)`,
`request_stop(reason_ref="reason:operator-stop")`, `poll()` and `snapshot()`;
`state` and `generation` are read-only observations. Each controller atomically
claims its first start attempt as single-use, including an attempt stopped
before native launch begins. Calling `start()` again on that instance denies.
Reopening a preserved journal uses a new explicitly constructed controller
after the previous owned lifetime and cleanup have been observed complete.

The service process opens the existing CMP-03 `SqliteJournal` with the explicit
v2 `STORE_PROFILE`, then captures exactly one kernel/store in
`compose_duplex_kernel_service`. The controller's request/result spool is a
transport observation surface, not a second kernel or authority store.
Application routing remains `KernelIngress` into the existing kernel port.
The service startup response reports observed scoped positions and
`authority: "CLOSED"`; READY means that this development endpoint and preserved
store were inspected, not that a model, tool, grant or effect is qualified.

The controller launches `sys._base_executable` with `-I -B -X utf8` and the exact
`client_process.py` / `service_process.py` entry paths. The native launcher uses
atomic Job Object membership at process creation, a suspended primary thread,
retained process identity and a noninherited kill-on-close job handle. It resumes
the primary thread only after its launch checks. Explicit standard-handle lists
select the child control/output/error ends; parent ends and job ownership remain
noninheritable. A controlled environment supplies System32 PATH and the selected
private development temporary directory, without inherited user Python hooks
or credential environment.

The primitive is `WindowsOwnedProcess.launch(executable, arguments, *, cwd,
environment, inherited_handles=(), standard_handles=None,
expected_image_sha256=None)`. The retained owner exposes `pid`, `creation_time`,
`image_sha256`, read-only `lifetime_closed`, `poll()`, `wait(timeout_seconds)`,
`active_process_count()`, `terminate(exit_code=125)` and `close()`. `terminate` requests termination of the
owned job only. Neither a termination request nor a primary-process exit alone
proves that all descendants exited. `close()` rejects unresolved lifetime and
requires the primary exit plus an empty owned job before releasing ownership.
The launcher is trusted composition infrastructure, not an arbitrary command
endpoint accessible through IPC.

## Retained kernel routes and selected native peers

The retained kernel inspector picker exposes these six kernel routes. The
authenticated router also accepts four typed task routes documented below:

| Route | Original input type | Observation/result boundary |
| --- | --- | --- |
| `kernel.prepare` | `ActionProposal` | Prepared result requires real current owners; concrete preparation owner is unavailable. |
| `kernel.consume` | `OperationPermit` | Consumption requires current admission owners; concrete protected-resource owner is unavailable. |
| `kernel.revoke` | `StandingGrant` | Exactly one `reason_ref` argument; concrete revocation owner is unavailable. |
| `kernel.resolve_consumption` | `OperationPermit` | Authenticated public lookup of committed consumption evidence, without executing an effect. |
| `kernel.recover_permit` | `OperationPermit` | Authenticated read-only lookup of the current matching PREPARED or CONSUMED record. |
| `kernel.recover_preparation` | `ActionProposal` | Exact original proposal lookup when its generated permit ID is unknown; intent-v2 input and issuance checks apply. |

Registration is selected by the service's owning composition, using the owned
client's PID, exact process creation FILETIME, pinned executable-file hash,
logical principal/session and explicit operations/scopes. The client constructs
`WindowsServerBinding` from controller-selected service PID, creation time and
image hash. A PID found by pipe name or matching executable name is insufficient.
Both sides retain selected process lifetimes and revalidate native token/process
facts; the current request's opaque context cannot authorize another envelope,
inner record, thread or later call. Every route, including all three read-only
lookups, passes the message/context binding and authentication wrapper.

Each native receiver owns a fresh cryptographic generation. The service returns
that generation through its owned control channel; the controller binds new
envelopes to it. Reconstruction does not revive old messages or an old opaque
context. This transport generation is not a substitute for durable authority,
fence or revocation generations checked at actual effect admission.

## Duplex correlation and uncertainty

The existing one-way ingress remains available as documented in
`LOCAL_IPC_V1.md`: `send_pipe_message(...)` returns `None` after submission and
selected-server revalidation, with no positive result acknowledgment.
Duplex composition explicitly selects `WindowsPipeServer(...,
response_encoder=encode_response)` and the separate
`send_pipe_request(pipe_name, message_wire, codec, timeout_seconds=5.0, *,
expected_server)` API. It returns a validated `LocalResponse` only after the
bounded exchange and selected-server checks. Request and response messages use
the existing four-byte big-endian length and at most 1,048,576 bytes per body.
The original twenty admitted record types remain unchanged.

The `ceta-local-result-v1` wrapper binds the exact request SHA256, message ID,
correlation/causation references, selected actor session, fresh receiver
generation, route, scope and input record ID. Canonical returned payloads and
events are checked against their route, causal identity, payload commitment and
actual predecessor. The encoder exports only the relevant record/event, not
other commit cells, budgets or scopes. Results are `COMMITTED`, `EVIDENCE`,
`CURRENT_RECORD` or `DENIED_RECONCILE`. `COMMITTED` reports the checked kernel
record/event result, never external effect completion. `CURRENT_RECORD` has no
event or transaction claim. `EVIDENCE` retains the actual historical consumption
actor and predecessor. A sanitized `DENIED_RECONCILE` has no payload and does
not assert rollback or absence of a prior commit.

After receiving and validating a response, the client sends its 32-byte SHA256
receipt so that the server can disconnect without discarding an unread reply.
That receipt concerns transport cleanup only: it is not an effect acknowledgment,
consent, settlement or additional permission. Native transport deadlines and
revalidation can still fail after submitted bytes or a kernel commit.

`begin_call()` reserves the exact attempt, envelope, original deadline, selected
server lifetime and client channel under a brief controller lock, then starts
tracked background preservation and control dispatch. Returning an attempt
acknowledges this in-memory reservation. It does not acknowledge a disk write,
IPC submission or kernel result. Before control dispatch, the retained worker
exclusively writes the original envelope to
`controller-<UUID>/requests/<attempt>.request.json`. A failed write prevents the
send and retains the original request bytes and uncertain attempt in memory.
Thread construction/start failure reports typed `SubmissionUncertain` for that
same attempt, preserving its original exception as the cause; a request file may
be absent because no worker wrote it. The client exclusively
writes the response file and reports its digest over the owned channel; the
controller checks that file against its pending request. These ordinary file
writes preserve inspectable bytes when present, but are not a qualified
power-loss-durable attempt ledger or automatic restart reconciliation engine.
The `ceta-owned-call-v1` control command carries integer `timeout_ms` in
1..10000; the controller rounds `call_seconds * 1000` upward and the client
converts that integer to seconds only inside its native call. Control JSON
does not contain floating-point timeout values.
Missing/mismatched responses, process death, timeout, a lost response receipt,
or `DENIED_RECONCILE` leave possible committed state to be reconciled. There is
no automatic replay, permit renewal, reconsumption or budget refund.

While RECOVERING with a live endpoint, the controller permits the three
read-only kernel lookup routes plus `task.load` and `task.list`.
`recover_permit` requires the original immutable permit
binding and the stored intent's matching principal/session. It reads the
captured store, checks PREPARED causal identity or the actual CONSUMED event,
then rechecks selected cells and peer identity. It calls no store commit,
positive decision owner, effect adapter or refund API. A consumed record can be
passed separately to `resolve_consumption` to inspect its committed event.
Expired/revoked preparation may be observed without becoming current admission.
Proposal recovery is available for intent-v2 through its original logical session.
Legacy intent-v1 lacks the historical grant commitment needed by that route.
Full settlement, independent effect observation and a qualified restart-session
handoff remain separate unfinished responsibilities. The default controller creates a new
logical session; it does not silently recover another session's authority.

## Stop, in-progress launch and retained cleanup

`request_stop` acquires the controller lock and changes the controller to
STOPPING before requesting termination. That state rejects new controller
dispatch. No controller lock spans native launch. Each launch slot is reserved
under the lock before construction, alongside a counted publication obligation.
The reservation prevents competing calls from constructing owners for the same
slot or overwriting a still-unpublished owner. The controller's single-use start
claim rejects a stale start resumed after Stop; STOPPED cannot be reported while
construction/publication is in progress. A late published channel is retained
and receives the stop request too. The controller also tracks pending service
launch. This is a host-dispatch linearization point, not cancellation of a kernel
COMMIT already in flight.

Client launch from `start()`, service launch from `poll()`, and request
preservation/control send run in retained background workers. Reservations are
installed before thread publication. The controller retains each actual thread
until both its completion flag and observed thread exit agree; it does not join
live workers in Qt callbacks or under its state lock. Constructor failure before
a thread exists can retire the absent worker. Interruption during native thread
start can leave publication ambiguous; absence of a thread identity alone does
not retire that interruption obligation or establish STOPPED.

The worker checks Stop and the original deadline after successful preservation,
before a bounded logical send-admission claim. Stop winning that claim suppresses
the control send. A worker already admitted uses the captured client, command and
server lifetime. Logical admission does not prove physical `WriteFile` entry
occurred before a concurrent Stop and does not cancel a prior kernel COMMIT.

A separate send reservation denies another call while its worker remains owned,
including when a validated result has already cleared the pending response.
Late worker failure cannot overwrite that matching validated result or revive
STOPPING/STOPPED. `OwnedChannel` reserves its input handle while `send()` runs;
`close()` rejects active write ownership without waiting for the native write.
The lease lock is released before `WriteFile`, while its handle and buffer remain
reachable. Fake or actual child exit alone cannot authorize their cleanup.

STOPPED is reported only after every retained worker has an observed exit,
launch publication is complete, every owned primary process exit and empty job
are observed, and retained cleanup completes. Cleanup is deferred while workers
can still publish or use their owners.
Termination and cleanup failures leave STOPPING with ownership retained for
later `poll()` / stop retry. Process names or unrelated matching Python
processes are never termination selectors. Pending calls become
TRANSPORT_UNCERTAIN and their exact in-memory request remains retained through
STOPPED, including when a start or file-write failure left no disk copy. A stopped
single-use controller cannot submit again. This memory retention does not survive
interpreter exit. Process shutdown does not reconcile an effect or refund a
reservation. The returned state continues to show effect authority CLOSED.

`OwnedChannelError` retains `owned_channel`, `owned_process`, the original
`launch_error`, `primary_error`, `cleanup_errors` and `close_cleanup()`.
Construction failures do not discard a live owner merely because child-end
cleanup failed. Successfully closed handles are removed individually from the
retry set; residual child/parent handles and original launch cleanup remain
reachable. A channel tracks process closure separately and consults the trusted
native owner's read-only `lifetime_closed` observation before polling or
terminating an already closed lifetime. This covers a launcher failure that
closed its process/job ownership but retained residual startup cleanup handles.
Closed lifetime does not mean every startup/control handle is cleaned up:
`close()` / `close_cleanup()` still retry those residual owners. No caller JSON
or pipe message can set this native owner observation. This documents the
reviewed candidate cleanup path; native failure-injection execution and
integration evidence must establish its exercised behavior separately.

## Operator and timing limits

`OperatorSession` owns per-view drafts and attempt/view-generation correlation
in memory. Late results do not replace another selected view's editor.
`OperatorView` provides Submit, Stop/Esc, textual status/detail and a read-only
result, and waits for observed STOPPED before ordinary window close. A failed
draft save does not prevent the initial stop request. Memory-only draft
retention across view switches is not restart durability. No preference/draft
persistence or full conversation/approval/work UI is claimed by this inspector.

Native request handling and executable-image validation run in the owned client
and service processes, allowing their owner to request whole-job termination
without abandoning helper threads. Startup and tiny anonymous-pipe control
writes use synchronous native calls inside retained background workers, outside
the Qt callback and controller state lock. The operator's `start()` and service
launch from `poll()` reserve this work and return without waiting for native
construction to finish. Native metadata, handle open, control reads, result-file reads,
process/job observation and driver calls still rely on ordinary Windows
scheduling. Their supplied deadlines do not prove a universal OS/driver
occupancy bound or UI responsiveness during every native operation. A blocked
host worker remains owned and keeps STOPPING even after its child job exits.
The launch barrier cannot terminate a process whose native construction has not
yet published its owned handle. Exceptional interpreter/process exit is not
qualified as successful worker settlement or durable attempt preservation.

Job ownership gives lifecycle containment. It does not establish filesystem,
network, registry, device or credential isolation, independent same-account
trust domains, loaded-code attestation, protected store/key custody or publisher
signing. No service install, elevation, AppContainer or production broker is
selected by this composition. Trusted time, approval, resource selection,
independent observation and actual effect admission remain unavailable.

## Source obligations and review cut

The supplied source obligations remain whole: SPEC-08 REQ-08-01..04 requires the
full event-driven supervisor lifecycle, bounded work, restart reconciliation
and explicit background setting; SPEC-21 REQ-21-01..05 requires actual Windows
trust/resource boundaries beyond jobs; SPEC-30 REQ-30-01..04 separates stop,
admission, native containment and uncertain-effect recovery; SPEC-32
REQ-32-01..04 requires the coherent native workflow, first launch,
inspectability, keyboard/accessibility and restart/window behavior. This
development slice does not erase named PAUSED/DEGRADED/full supervisor states
or claim the inspector implements every required workflow.

The corresponding original scenarios remain acceptance obligations: SPEC-08
lists B017/B018/B019/B020/B021/B023/B024; SPEC-21 lists B065..B072; SPEC-30 lists
B015/B019/B077/B078/B098/B100/B101/B102/B115; SPEC-32 lists
B026/B113/B114/B115/B116/B119. No original case or gate status changes through
this document. Full 175 requirements, 25 components, 128 original cases,
28 work packages, 20 volumes, 406 lifecycle sources and eight gates remain in
scope; Gate A remains open.

Focused test sources distinguish real owned Windows lifetimes
(`test_windows_jobs.py`), pure synthetic result bindings
(`test_local_results.py`), real v2 journal recovery with synthetic decision
owners (`test_kernel_recovery.py`), and Qt offscreen controls with a controlled
session (`test_operator_view.py`). Offscreen widget/keyboard assertions do not
qualify the visible Windows desktop, screen readers, native Stop under full
workload, installed behavior or the complete original scenarios. Increment 24's
documentation-only review assigned no execution result. Increment 26 adds
`test_stop_dispatch.py`: actual controller/channel/operator and offscreen Qt
paths with controlled launch, send, process lifetime and result fixtures. The
separately retained first baseline run records failures against the old
synchronous implementation. Later repaired results must bind their changed
inputs, raw test identities and stable ledger cut; their scope remains
development scheduling evidence rather than a reproduced native driver stall.

`test_owned_service.py` separately contains native owned-service/client/IPC and
journal cases, with positive records prepared by explicitly synthetic fixture
owners before the parent journal closes. The child service keeps identity-only
owners and CLOSED positive authority. Its launch scheduling, cleanup failure and
late-result cases inject controlled local channels/processes/handles; they are
not reproduced native CloseHandle failures or independent identity/effect proof.
Reading those test definitions establishes their intended scope, not a pass.

At the historical Increment 24 document evidence cut, the focused native primitive run
`windows-jobs-lifetime-24-01` actually executed eighteen tests with return code 0
and eighteen matching raw `ok` identities, ending
2026-10-08T17:05:54.669233Z. The inspected receipt SHA256 is
`1b10a9acfeca68ed0b1e9efda79fe536f0a6d7b3b851be14620091a03846f7c9` and its raw
log SHA256 is `371cc8dcdfe7a920936509b25e66690ee9e5c7f1633e6d79c98c4b5f7418ac8b`.
Both are under S `.local-build-cache/increment-24-owned-service/`, named
`windows-jobs-lifetime-24-01.json` and `.txt`. Current primitive/test/wire hashes
match the receipt's before/after inputs. This proves only those disposable native
lifecycle fixtures, including controlled resume/image-close faults. It does
not execute the service/controller or qualify the original acceptance cases.

The frozen owned-service test source contains twenty-four methods: ten native
integration definitions and fourteen controlled regressions. Reading those
definitions establishes their scope. Actual owned-service and full-suite
execution results are maintained in separate retained evidence rather than
assigned by this contract. Later execution does not retroactively change the
historical source cuts or establish product qualification.

The first full development suite executed 427 methods with one error: the
foreign-process fixture exposed its readiness filename before its JSON write
completed. That unchanged run is retained as `contracts-full-first-24-01.json`
and `.txt` under the same S evidence cache. The current fixture writes and closes
a separate pending file before publishing the final marker. An explicit
parent/child barrier exercises the empty pending stage and asserts that the
final marker is absent before release. This correction retains strict JSON
validation and the original checks that Stop observes both owned jobs while
preserving the separately created foreign process. Subsequent execution results
must bind this corrected source cut separately.

Historical Increment 24 frozen implementation, specification and test inputs.
The earlier 17:03:04Z twenty-four-pin cut is historical after the authorized
single-use/slot and closed-lifetime repairs. Both document candidates from that
cut were preserved before these updates. The table below replaces the five
changed controller/channel/native/test pins with their actual frozen bytes;
the client retains the already reviewed integer-timeout correction. Earlier
semantic reads between 16:55:17Z and 17:01:53Z were followed by affected-clause,
property, complete before/current diff and regression reads between 17:05:07Z
and 17:08:50Z. Completed earlier reads are reused only with verified byte identity
or an exact bounded change comparison, not by treating a hash as a semantic read:

| Exact path within D | SHA256 |
| --- | --- |
| `src/ceta/supervisor/windows_jobs.py` | `821e2615799a66e4b0c519b4f98434cd71b375c2e47bf496d834edb0ee1a8ec7` |
| `src/ceta/supervisor/service.py` | `c209c1ada212d5ddde470510c9b10b3a32597704da4671bdf1aba9486c3e53a4` |
| `src/ceta/composition/owned_service.py` | `90ab77124b43362b91607b7119c14b3137fc22ae6700fe6e7ad1c8530960693a` |
| `src/ceta/composition/service_process.py` | `589f2f027a8cacb052853a63d1e7fba8577600dadbde83ecbd4119164585a792` |
| `src/ceta/composition/client_process.py` | `e9aeb5706955c99b8bb430d1d80c4d64e79acc8c7c77145d2ccf17cc5d709f7f` |
| `src/ceta/composition/ipc_service.py` | `8ad855dd542cee7eb64c4b883ce43c2bd39e2d293deb5bca2b8b5021e00210bf` |
| `src/ceta/contracts/local_ipc.py` | `0de4ebfdf3d491d6bc162bfe4067d3dd5e2fee73f072ed5991b4714da3b641d1` |
| `src/ceta/contracts/local_results.py` | `2a7024783d38815693cbc17f507ddb8fc060bb12af6d52c0e974113c41f19c64` |
| `src/ceta/identity/windows_pipe.py` | `deb0e56991c71933e1b6b433cdf636e1f7dbc14e16e71c1ab4ca1458f9259052` |
| `src/ceta/kernel/transactions.py` | `3aad2092d8f803c766329449cb68eee4fc0f0e091f4cadd471371c3d8b71c10c` |
| `src/ceta/identity/owners.py` | `ebddcb6d2d2dade6910ce49a7ffb1568d875d49048bad2b1a2b3efacd88e76d8` |
| `src/ceta/application/operator.py` | `3d78312eb8f46c2dfb51f2a511d2b346f646a79e26d8828b244e7879982a0ed3` |
| `src/ceta/desktop/operator_view.py` | `ecb3fd471734b39747774bbe2d9a10b7eecb74b590348843f9d7f1e9fd8ae6a4` |
| `tools/ceta_operator.py` | `c4540af7da84a3b5383310ea9a498bb24fa2afa7c30508a30aefb119f5878cca` |
| `contracts/dependencies/native-operator.lock` | `191f0de31ee4af2e6d9a79dd06bdbe929909b0966f881f2af3d1d21a594c1c67` |

| Exact path within S | SHA256 |
| --- | --- |
| `docs/specification/08_supervisor_and_continuing_operation.md` | `0124063954ce08802b8e72c9d0c61e6dd42fcf0bb0e2f4d53f4053999aad1d6d` |
| `docs/specification/21_windows_process_and_resource_enforcement.md` | `8dbf43e1df8b11df8fc8264d61a819f2e8a9a5fe2e2b470ecc4eb70f967407dc` |
| `docs/specification/30_cancellation_shutdown_and_recovery.md` | `a7e7078ac93a043bbc4900e0e129eafecf35a7af0fe0bf7ff9b0d403cd58b694` |
| `docs/specification/32_native_interface_and_inspectability.md` | `a004fc27cf8de7cb9f05aaf1a16ec2229f42b4ad0a3c7a0a6916b17e673f3e4d` |

| Exact inspected test path within D | SHA256 |
| --- | --- |
| `tests/contract/test_windows_jobs.py` | `eec728dce440964cc9a99f272fd05368ef378827833f26edeae0d6244cb72d11` |
| `tests/contract/test_kernel_recovery.py` | `0e164750f16e12ef5e2735a553ad4eb9eff7de199f6c2bc595ecec0008b543e5` |
| `tests/contract/test_local_results.py` | `2b6ba5c72d5752a63e8f72f708df88a4cdcda7eb141c6f6675229bb05da14965` |
| `tests/contract/test_operator_view.py` | `38a655a7eed064ae88c78b2f654a5514466352ae004729e3c5add1c3cf5f2d0e` |
| `tests/contract/test_owned_service.py` | `24b234ed1665b13b96818c149068e01cc97969073c314b6d2198ed2b4ce7c0b6` |

Here D is `T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios` and S is
`T:\00-Active\CETA_Intelligence_Operating_System_Build_Package`. Hashes bind
the reviewed cut, not future edits. Complete reads of the four specifications,
result parser, controller, channel, operator and entrypoints support this prose;
kernel/transport recovery and duplex call sites were inspected by bounded line
ranges, without a claim of a new full-module review of their unrelated paths.

Increment27 adds proposal recovery through the existing kernel/store. The original
proposal, current captured principal/session, durable issuance event and complete
operation-input commitment must match before any record is returned. New intent-v2
retains the historical grant commitment; legacy intent-v1 still supports the old
permit/evidence routes and explicitly denies this new lookup. No query migrates
metadata, retries dispatch or changes held/charged allocation. RECOVERING permits
this third read-only route while commands continue to require READY. The native
inspector exposes the additive route through the same injected application use
case and authenticated transport. It remains a development inspector with memory
only drafts, not a completed task workflow or cross-session recovery engine.

Increment 28 adds the typed task workflow in `TASK_DRAFTS_V1.md`. Task create and
save remain READY-only asynchronous calls. RECOVERING also permits task load and
list; an unrelated successful read preserves the earlier recovery state. The
controller retains a captured uncertain task write and clears it automatically
only when a matching loaded snapshot establishes that exact command commitment
for that task and scope. Explicit `acknowledge_task_reconciliation(task_id,
revision)` selects the actually observed current task CAS after a conflicting
or absent load, retains the original uncertain request and current response,
and leaves historical write attribution unresolved. Absence is selectable only
for a pending task creation. Neither route clears prior kernel/effect uncertainty.
Fresh task writes invalidate earlier task observations. Retained reconciliation
history is bounded at 256 entries before admitting further task mutations.

The default TaskView shows confirmed persistence separately from service state,
retains local drafts across views and late acknowledgments, and exposes current
task reload even when an uncertain creation is absent from the catalog. Stop/Esc
does not wait for text validation or persistence. Close considers unconfirmed
text in every retained task and waits for observed owned termination. Local
unconfirmed editor text remains memory-only; the native journal stores confirmed
task snapshots. This development entry point neither installs nor activates a
production profile, model, trusted authority owner or external effect.

Increment 29 adds manual interpretation editing through the same task session.
`task.meaning_propose` is a READY-only write; `task.meaning_load` is also allowed
while RECOVERING. The controller separately records the actually observed task
and interpretation revisions. An ordinary task load cannot clear an uncertain
interpretation write. A matching authenticated proposal load can establish the
exact retained command and records `EXACT_MEANING_PROPOSAL_OBSERVED`. Explicit
`acknowledge_meaning_reconciliation(task_id, revision, task_revision)` requires
the actual matching observation, retains the original uncertain request and
current response, and selects the current CAS while leaving earlier write
attribution unresolved. Current absence is selectable only for an initial
proposal. These decisions do not settle kernel or effect uncertainty.

The interpretation dialog retains valid unsaved text in the shared task session,
keeps newer edits after late responses, exposes stale basis and CAS conflicts,
and provides Stop/Esc independently of text validity. Invalid widget edits require
an explicit discard decision before return. Original instructions remain read
only. This manual proposal workflow does not claim a qualified model compiler,
accepted objective, finite grant or historical uncertain-attempt import across
fresh controllers. Those remain required implementation and qualification work.

## Increment 32 exceptional application shutdown

The development entry point now captures ShutdownCoordinator before Qt setup.
It captures the task/inspector session before window construction. Setup,
window-show, service-start and event-loop failures therefore share the same
cleanup path instead of performing one service poll after an exceptional exit.

The coordinator requests the session's Stop first, independently of draft
validation, and falls back to the actual service termination request if that
callback fails. It polls both the service and session. STOPPED requires actual
service STOPPED, session STOPPED, and no pending compiler work. Owned lifetime
settlement remains separate from saved editor text and outcome reconciliation.

The default cleanup wait is 15 seconds. This is a caller wait budget, not proof
that every native driver call has a universal occupancy bound. A timeout or
failed observation retains the captured owners and reports
APPLICATION_SHUTDOWN_UNRESOLVED. A primary application exception remains the
primary exception, with a separate cleanup-failure note. No normal profile,
production authority owner, model, effect, installed service or positive grant
is introduced by this change. Full production launch containment, durable
editor recovery and uncertain-attempt reconciliation remain required.

### Resumed P00 shutdown repairs

The coordinator publishes requested state before Stop callbacks. It catches
callback interruptions, attempts actual service Stop as fallback, and preserves
the initiating BaseException. ShutdownObservation records callback, fallback,
and poll attempt counts separately from native process observations.
ShutdownIncomplete exports a typed PendingShutdownOwner; retry performs another
explicit Stop and bounded drain. Cleanup diagnostics cannot replace the primary
exception, including when its overridden add_note fails or mutates its dictionary.
This owner retains custody within the current interpreter lifetime.

OwnedService records immutable termination attempts for each exact retained
native process owner. Each explicit Stop may request termination once per owner,
with a lifetime limit of three requests. Polling never issues another termination
request. A successful request does not establish exit; observed exit and completed
handle cleanup are separate facts. Failed or unknown observations, exhausted
requests, and partial cleanup retain the owner. A later published process gets
its own budget without resetting an existing owner's budget.

TaskOperatorSession publishes Stop intent before callbacks, attempts every retained
compiler cancellation and native Stop, and preserves the first failure. During
shutdown, failed service, cancellation, or worker observation keeps pending work
in STOPPING.
Native STOPPED does not authorize window closure while compiler work remains.
Structured session diagnostic codes accompany the retained local drafts.

These repairs do not close protected custody across interpreter exit, genuine
no-entry publication through restart, or durable rejected-editor recovery. Their
qualification and original source-defined acceptance cases remain required.

## Current consolidation qualification location

The entry-point commands and `.local-test-output` descriptions above retain
their historical desktop source cut and results. In the current consolidation
candidate, the unchanged guards in `src/ceta/composition/owned_service.py`,
`src/ceta/composition/service_process.py` and `tools/ceta_operator.py` require
disposable development profiles inside this repository's `.agents/fixtures`.
The operator's default creates `.agents/fixtures/operator-24/<UUID>` here; an
explicit existing development profile remains subject to the same directory and
link checks. These paths resolve from this same repository after a verified
rename. This clarification does not adopt historical desktop commands as current
launch instructions, change a guard, admit normal user data or live profiles, or
qualify installation, positive authority, resource effects or product completion.

## LP1 launcher custody filesystem paths

The launcher keeps its public logical profile, record and lock paths unchanged.
On Windows, native file operations use one validated extended-prefix spelling
consistently for ancestor/link checks, lock acquisition, record reads,
create-only temporary writes, atomic replacement and owned temporary cleanup.
This follows the Windows extended-path rules described in
[Microsoft's maximum path length documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).
It changes no registry setting or application-wide filesystem configuration.

Ordinary absolute drive paths, UNC paths and their corresponding extended
spellings are parsed without accepting device namespaces, parent traversal,
alternate streams, reserved components or trailing-dot/space aliases. Native
qualification here uses local T: fixtures; UNC conversion has syntax-only
coverage and performs no network access. The captured profile directory's
device/inode is checked again, and observed ancestor/endpoint reparse points
or hardlinked record/lock files deny. These are observed identity checks in
the existing private profile, not exclusion of a hostile external filesystem
writer between native calls.

The temporary file remains create-only. A collision preserves the existing
entry. Cleanup deletes only a temporary file whose creation and native
identity were observed by this write; a changed entry is preserved. Short
writes are completed before flushing and replacement. A close is attempted
once, including when a native close succeeds but its response is lost.
Replacement ambiguity does not replay the write or clear a PENDING record.

An initiating BaseException survives independent close/unlink failures.
Trusted exception storage retains the exact `launcher_custody`, ordered
`launcher_custody_io_errors`, root and observed temporary native identities,
temporary path/creation facts, uncertain close
identifier and replacement-attempt flag. Refused attribute, note or dictionary
hooks do not replace the primary exception. An uncertain descriptor number is
diagnostic custody and must not be blindly closed again: that number may have
been reused after a completed close.

LP1 tests use actual disposable files, NTFS junctions/hard links and byte-lock
contention between independent handles in one process. Fault/response-loss
injection is recorded separately from the native operations it surrounds.
Child processes, service/worker launch, profile operations, Hello and CPU Set
are excluded. Existing cross-process lock, native shutdown and full-product
qualification remain separate gates; this filesystem repair does not close
them.
