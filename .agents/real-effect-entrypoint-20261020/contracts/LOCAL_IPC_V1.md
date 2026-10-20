# Local Windows ingress, development profile v1

Status: IMPLEMENTED_NOT_QUALIFIED. Development execution evidence is separate
from product qualification; this document assigns no new test/case/gate result.
Source basis: ARCH-01/02, SPEC-03/04/05/06/19/39, CMP-04, POL-07, original master
sections 05/06/19 and B063/B068. All original records and prior APIs are retained.
Original B063/B068 remain NOT_RUN until their complete required profiles run.

The development adapter uses pinned Windows x64 Python 3.12 and ctypes FFI to
installed Windows kernel/security APIs. This is an engineering selection for
local ingress, not qualification of the final secret-custody/native toolchain,
publisher signing, broker ownership, restricted worker or installed profile.
No executable is imported from another project and no retained algorithm reused.

The `ceta-local-ingress-v1` envelope carries exact version, message/correlation/
causation IDs, actor session, receiving generation, operation, scope, absolute
millisecond validity, original-record SHA256 and canonical-record commitment.
Its record is one of the unchanged twenty admitted types for kernel routes, or
the separate typed TaskCommand for the four task routes described below. Revoke has exactly
one reason_ref argument; other routes have no arguments. Unknown fields, roles,
PIDs, SQL, shell, plugin or arbitrary signing requests are rejected. Original
record bytes remain the dispatch/evidence input; parsing does not confer consent.

One Windows message contains a four-byte big-endian length and one envelope of
1..1,048,576 bytes. The envelope and encoded record together must fit this bound.
This is a new explicitly bound envelope profile; it does not reinterpret the
prior record-only framing API. One complete WriteFile message is required;
partial, concatenated, trailing or oversized messages are rejected. There is no
unbounded accumulation, fallback to sockets or caller-controlled file handle.

The receiver acquires a local CETA-prefixed pipe with first-instance ownership,
one instance, explicit security descriptor and remote clients rejected. Only
explicit owner-created process registrations enter the accepted identity set.
The launcher-selected creation time is required before logical registration.
The retained process handle, matching creation time, expected executable-file hash,
primary token facts and connected-pipe PID/session bind technical identity.
After reading the bounded header, the server captures the last-read-message
impersonation identity and checks it against the registered process facts. It
must revert on that same thread before parsing or invoking application code.
An impersonation/token failure denies; server identity is never a substitute.
A failed reversion terminates the affected isolated process.

The registry binds the technical identity to logical principal/session and
explicit route/scope selections. An opaque context is valid only for that
accepted request and registry. It is revalidated by the existing authentication
port and invalidated after handling. Context class construction, a saved context,
matching user SID or a caller-supplied worker name cannot create a registration.

The sender also requires a trusted expected-server binding, supplied by its
owning composition before connecting. That binding pins the server process,
creation time and executable file, retains its live process handle and checks
the connected pipe's actual server PID/session before writing any payload.
A pipe name or a process discovered from that name cannot establish trust.
The binding is a development process identity check, not loaded-code attestation
or authority to disclose a resource outside the registered scope.

The native receiver creates its own fresh generation on every construction and
exposes it to its trusted composition; callers do not choose or reuse it. The
trusted composition supplies the resulting generation to its clients. The
serial receiver rejects
stale generations, mismatched actor sessions, missing route/scope permission,
future or expired messages and message replay. Messages are marked seen before
application dispatch, including kernel denials. Validity is at most 30 seconds;
replay capacity is 4096 entries and exhaustion denies without eviction. Pipe
and executable-byte I/O share deadlines and cancellation/drain, with explicit
file offsets. Initial identity capture has a five-second engineering bound.
Synchronous metadata queries, handle opens and native call entry still lack an
independently enforced overall occupancy bound. Windows also permits overlapped
reads to block synchronously; the supplied timeout does not qualify that bound.
Supervisor containment remains required. Local
wall/monotonic observations do not replace the trusted authority-clock owner
or qualify rollback/suspend/reboot semantics.

The Increment 24 owned development composition runs native request handling and
selected-server validation in explicit job-owned service/client processes. Its
controller retains exact process lifetimes and can request their whole-job
termination. Synchronous startup and tiny control writes still rely on ordinary
OS scheduling; process containment does not establish a universal kernel/driver
call bound, security isolation or positive effect authority. See
`OWNED_SERVICE_V1.md` for its lifecycle, uncertainty and cleanup contract.

The observed Windows build returned a one-byte TokenHasRestrictions flag,
while the public token-information documentation describes a DWORD. The
development adapter explicitly accepts only those one- and four-byte layouts
for class 21, only flag values 0/1, and unchanged returned-query lengths. Other
scalar classes remain exact DWORD. Effective message tokens require actual
impersonation level 2; anonymous, identification and delegation levels deny.

`compose_local_kernel_service` captures one existing kernel/store and real peer
authenticator. All exposed routes pass through KernelIngress, including internal
evidence lookup. The public evidence route delegates to the peer-bound kernel
query with the same original wire and opaque context, preserving the separate
trusted internal resolver signature. It checks the durable principal/session,
proposal/read-set/grant scope, consumed payload and event attribution, then
rechecks the same permit/intent cells and live context before disclosure. It does
not repeat admission or require an unexpired grant for historical evidence.
The identity-only owners deny preparation, admission, revocation
and authority-clock obligations still unavailable. Kernel runtime admission stays
closed. The same principal/session development consumption binding is retained;
a separately authenticated broker must not impersonate the worker's logical
identity. Broker subject/caller/event attribution needs its explicit contract.

The original one-way profile remains `send_pipe_message(pipe_name, message_wire,
timeout_seconds=5.0, *, expected_server)`: it returns `None`. A completed client
write means submission of bytes, not request acceptance, kernel success or
completed effect. `compose_local_kernel_service` preserves that behavior and
keeps its handler result local to the service owner.

The separate Increment 24 duplex composition is
`compose_duplex_kernel_service(store, codec, installation_scope_id, registry,
pipe_name)`, using the same captured kernel/store and authentication wrapper.
It explicitly supplies `response_encoder=encode_response` to
`WindowsPipeServer`. The client uses
`send_pipe_request(pipe_name, message_wire, codec, timeout_seconds=5.0, *,
expected_server)` and receives a validated `LocalResponse`. The same selected
server PID/creation/image binding and fresh receiver generation apply. A
correlated response does not create another authority store or change the
original twenty-record wire schema.

The bounded `ceta-local-result-v1` response binds the exact request SHA256,
message ID, correlation/causation references, sender session, receiver generation,
operation, scope and input record ID. Original canonical record/event payloads
are checked against route-specific identity, payload commitment and predecessor.
Only the requested record/event is returned, not other cells or budgets. Response
kinds are COMMITTED, EVIDENCE, CURRENT_RECORD and DENIED_RECONCILE. COMMITTED
describes a checked kernel result; it does not establish external effect
completion. A denial can follow durable COMMIT and requires reconciliation.
The client's 32-byte response SHA256 receipt permits bounded transport cleanup;
it is not consent, settlement or evidence of an effect.

The six authenticated kernel routes remain narrow: kernel.prepare accepts ActionProposal;
kernel.consume and kernel.resolve_consumption accept OperationPermit;
kernel.revoke accepts StandingGrant plus reason_ref; kernel.recover_permit accepts
OperationPermit. kernel.recover_preparation accepts the exact original ActionProposal.
The recover_permit route is a read-only current-record query. It checks
the stored intent's principal/session and immutable selector, verifies actual
consumption evidence when current state is CONSUMED, and rechecks peer/state
without admission, replay, budget refund or effect execution. It accepts only
matching PREPARED/CONSUMED selectors; unsupported lifecycle states deny. It does
not substitute for independent effect observation or settlement.

The owned controller retains exact request bytes before dispatch and enters
recovery on missing results or DENIED_RECONCILE. No automatic replay or refund
is permitted. Stop disables new controller dispatch before owned termination,
but does not cancel a kernel COMMIT already in flight. STOPPED requires observed
primary exits, empty owned jobs, completed launch publication and successful
retained cleanup. A controller atomically claims one start attempt and reserves
each launch slot before construction; competing/stale starts cannot overwrite
unpublished ownership. A channel uses the native owner's `lifetime_closed`
observation to avoid polling/terminating closed process/job handles while still
retrying retained residual cleanup. Full native UI/runtime workflow qualification
remains open; the final byte binding is documented in `OWNED_SERVICE_V1.md`.

An explicit user-SID DACL does not isolate unrestricted same-account workers or
protect against an administrator, handle transfer, process injection or owner
DACL changes. An executable-file hash is not an attestation of loaded code or
publisher signature. Actual restricted worker/broker identities, protected state
and resources, trusted approvals/time, independent observation and runtime
qualification remain mandatory open lanes. No such claim derives from this API.

Native tests must use disposable real Windows processes and record success,
denial and interruption through the owning composition. Unit tests and model
review remain separate from original acceptance, installed, external, hardware,
device/custody/distributed, power-loss and endurance qualification. Preserve all
failures and historical evidence. Gate A stays OPEN and the full goal active.

The additive `kernel.recover_preparation` route accepts the exact original
ActionProposal and returns CURRENT_RECORD with the matching durable PREPARED or
CONSUMED OperationPermit. It retains the same original opaque message context;
it never retargets that context to the discovered permit or retries preparation.
Kernel input/event/subject checks remain mandatory. Intent-v1 lacks historical
grant commitment and denies this new route without changing old recovery APIs.
The result has no event/predecessor export or effect/settlement claim. A different
original proposal, subject/session, scope, route or request binding denies.

Increment 28 adds `task.create`, `task.save`, `task.load` and `task.list`. Their
exact-field TaskCommand body and separate correlated TaskResult profile preserve
the original captured UTF-8 text without changing the twenty admitted record
schemas. The same authenticated envelope, message context, receiver generation,
route/scope bounds and original bytes reach the captured TaskDrafts kernel owner
over the same journal. Stable SID/principal ownership permits task content to be
reopened across fresh sessions; it confers no kernel session handoff or effects.
`TASK_ABSENT` establishes only coherent current absence, never historical rollback.
Atomic generation-bearing draft and kernel task revisions, catalog custody,
uncertain writes and remaining qualification are specified in `TASK_DRAFTS_V1.md`.

Increment 29 adds `task.meaning_propose` and `task.meaning_load` through the same
authenticated envelope, captured TaskDrafts owner and journal. Their command-v2
and separate meaning-result-v1 profiles bind all ten exact proposed text fields,
the full saved task revision, current proposal CAS, principal/session attribution
and canonical request/result commitments. Old task command/result shapes remain
unchanged. A stored interpretation is always UNACCEPTED; later task changes yield
an explicitly STALE read. These routes confer neither task acceptance nor a grant.
`TASK_MEANING_ABSENT` describes only coherent current absence. The complete wire,
bounds, atomic persistence and recovery requirements are in `TASK_MEANING_V1.md`.

## Selected manual real-effect commands

The additive `ManualEffectCommand` data profile declares `manual.run`,
`manual.restore`, `manual.inspect`, `manual.reconcile` and `manual.stop`. Its
4096-byte canonical body contains only command/scope/run identifiers, operation
kind, bounded CPU rate, original request selector and Stop reason. Unknown fields,
proof/configuration inputs, Boolean rates and route/kind substitutions deny.
It is a separate command profile like TaskCommand; the twenty RecordCodec
records and their schemas are unchanged. Correlated manual-result-v1 responses
bind the complete original envelope. A returned state or denial grants no
authority and is not an independent native observation.

Only the explicit `ManualRealEffectHost` routes these commands. The ordinary
identity-only KernelIngress continues to deny them. Its registered native peer
and scope checks, replay generation and 30-second envelope bound are unchanged.
One RUN context spans genuine enrollment, exact per-effect ceremony, canonical
prepare/consume/attempt, native dispatch, separate observation and settlement.
RESTORE uses a fresh authenticated request and a separate genuine approval,
retaining the same actual owned target and canonical cap-parent binding.

An optional trusted receiver context-retainer can retain an unresolved original
context and connected pipe. It cannot renew that envelope, change its thread,
register a peer or grant authority. Pending custody denies another receive and
ordinary receiver close. Explicit retirement requires the same captured owner
to report no pending custody before invalidation/disconnect. An expired original
context stays expired; this does not implement cross-process or renewed-context
recovery. The original owner and receiver remain exposed on failure.
