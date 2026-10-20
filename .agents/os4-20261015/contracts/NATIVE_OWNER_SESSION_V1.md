# Native owner enrollment session v1

`ceta.identity.owner_session.NativeOwnerSession` connects the reviewed Windows
peer registry, NC2 clock, NOV2 retained SQLite file identities, CB2 source and
environment pins, and NA2 enrollment helper to KA1's canonical owner-enrollment
ports. The canonical `KernelTransactions` and the captured `SqliteJournal`
remain the unique authority and state writers. The native session never issues
a grant or executes a CPU effect.

Trusted composition supplies exact concrete native owners, distinct installation
and project scope, a policy commitment, and three manifest names: helper image,
helper source and worker image. Names must resolve exactly once in the retained
code manifest. The composition is responsible for selecting the complete reviewed
source and environment manifest. The finite manifest used by engineering tests
is a fixture and does not qualify a release environment.
The helper's temporary directory must be the same measured private root retained
by the native store binding; selecting another scratch directory is rejected.

`native_context(original_context)` authenticates the actual opaque pipe dispatch
on its original thread, retains the code objects and requires the same native
private root/database identity. It holds no SQLite transaction while the helper
waits for a person. Borrowed registry, clock, file binding, code binding and
journal lifetimes remain the caller's responsibility. An independent Stop call
publishes cancellation without waiting for the context lock.

The helper first prepares a real measured process behind a closed native gate.
`designate_enrollment` accepts its exact body, private root/database, native owner
token, scope, policy, code/environment, worker, helper/UI identity, build, challenge
and ceremony nonce. It freezes a codec copy and permits one designation. Both
the helper and peer must have matching user/logon SID, authentication LUID,
terminal session, medium integrity and attributes, non-elevated default/limited
token class, filtering flag, zero restricted SIDs, and zero UIAccess. The peer
must be a primary token without impersonation. Native PID/creation/image facts
remain distinct for the peer and helper.

`TokenHasRestrictions` records whether a token has ever been filtered. Its value
is preserved independently from restricted-SID count; a limited UAC token can
carry that flag with an empty restricted-SID set. The allowed class is explicit
and never substitutes an unavailable observation with zero.
[Microsoft's token information reference](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class)
and [token elevation types](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_elevation_type)
describe these separate values.

The designation retains an actual pre-consent NC2 sample as the ceremony's
beginning. `clock()` pairs that sample with a new actual native sample and checks
progress; NC2 continues its own independent highwater checks. Repeated current
observations therefore do not move the beginning past an already observed
transcript. No timestamp is fabricated or accepted from a caller as native time.

The enrollment retainer binds the helper's original session, immutable body,
opaque context, original thread, semantic challenge/nonce and native evidence.
It checks actual current native owners, retained code, store custody and Stop
again before returning. An authentic helper that has exited with an empty job
can still supply its retained result: process, image, token provenance and interop
custody remain owned until explicit close. Requiring it to remain running after
the transport has observed completion would reject genuine completion.

`retain_verified_enrollment` creates an opaque witness only from this owner's
still-retained native session after an actual verified result, zero helper exit,
empty job, exact transcript bindings and fresh native currentness. The witness
is identity-bound to the exact session/context/body/transcript, remains private
to this owner, and is invalidated when the context ends. A Boolean, JSON object,
transcript DTO, digest or independently constructed witness cannot substitute
for the registered native witness. KA1 subsequently consumes the reserved
challenge and nonce in its single-store transaction; the session does not
create a parallel issuer, store or ledger.

Native faults retain the actual primary exception and session cleanup owner
through BaseException's canonical storage even if diagnostic hooks refuse work.
Close first requests Stop, then retires its own settled helper. Unsettled native
authentication work remains retained for explicit recovery; the library does not
kill operating-system authentication processes. Caller-owned native resources
are closed separately by composition after this session retires.

This component implements enrollment/currentness, Stop/revoke/recovery checks.
CPU approval, protected resource admission, effect preparation and revocation
integration are separate capabilities that remain closed until their concrete
effect owner is composed and qualified. Default runtime admission is unchanged.
The public command journey, actual owner consent, isolated worker launch, native
CPU execution, independent observation and durable settlement require their
remaining integration and acceptance checks.

Tests use actual disposable Windows pipe clients, native token observations,
retained code/file identities, native clock, prepared helper, hidden display and
canonical SQLite challenge. Negative tests intercept the actual gate before its
native Set call, or cancel before the gate, to qualify the native retainer
without displaying an authentication prompt. Controlled transcript data tests
exercise denial and time validation only. Genuine enrollment and Windows Hello
acceptance are explicitly NOT_RUN by this suite.
# OS2 selected native CPU approval owner

`NativeCpuOwnerSession` extends the same enrollment owner for effect approval
only. The base `NativeOwnerSession`, default construction, preparation,
admission, revocation and kernel runtime denial preserve their behavior.

Within the original `native_context`, `designate_effect(request, binding,
capture, original_context)` freezes one strict `OwnedCpuRequest` and borrows
the exact CPB1 binding/capture/WT4 target and native session clock. The qualified
NC3 platform cut retains the NC2 clock algorithm and pins its measured Windows
version and exact native image hashes. The request must match
the configured enrollment identity, source/environment/adapter/policy, limits,
session/deadline and real measured worker image. Designation grants no permit.

NA2 captures `retain_native_approval(request_wire, original_context)` at owner
construction. It returns an opaque local lease before helper process allocation.
Its repeatable `require_current(wire, challenge, nonce, helper, context)` checks
the exact active helper/session, request, original context/thread, native
principal, private retained capture and current policy/version/lifetime/clock.
Stop, closure, resume, membership loss, stale data and substitutions deny. It
does not query or reenter SQLite or ask the human inside a kernel predicate.

`retain_verified_effect(session, original_context)` can retain a witness only
from that owner's actual settled interactive NA2 session with its verified
result and exact transcript. `require_owner_authority_current` accepts this
exact opaque witness only for its matching `APPROVE_CAP` or `APPROVE_RESTORE`.
The existing canonical `approve_owned_cpu` transition alone consumes ceremony
nonces and creates decisions, grants, budgets and prepared basis. These owner
objects create no authority, dispatch lease, new ledger or native effect.

Context exit invalidates local designations/witnesses before closing an active
effect helper. A simultaneous control exception and helper cleanup failure keep
the original exception and expose this same surviving owner for cleanup. The
owner retains the active session even after designation invalidation. Borrowed
worker, clock, source/code and store resources remain their existing owners'
responsibility. Close/Stop never apply or restore a CPU policy.

Engineering acceptance uses actual medium disposable jobs, measured helper/
worker/current-clock/file/peer identities and real SQLite denials. Genuine
interactive gates are intercepted before native forwarding; hidden inspect
mode does not authenticate. Controlled cache/resume/nonce/error variants remain
fixtures. No genuine positive ceremony, isolated worker profile, execution
admission, CPU cap/restore or public runtime acceptance is implied by those tests.

Owner-session cleanup preserves the exact original exception and the exact
session-close secondary as `native_owner_session_cleanup_error`. Trusted builtin
dictionary and list operations avoid overridden diagnostic methods, including
exception dictionary subclasses and hostile note containers. This retains
`native_owner_session` and `close_cleanup` without invoking add_note callbacks.
The repair grants no authority, repeats no cleanup operation, and changes no
preparation, admission, revocation, or native effect gate.

OS4 adds a private single-use original-thread guard around the two owned public
`native_context` generator managers. Public signatures and original generator
bodies are preserved. A body exception remains the exact primary even when the
underlying contextlib traceback trampoline or a nested code-lease exit fails.
The guard uses BaseException traceback/dictionary descriptors and unbound dict
operations; it returns False so the caller resumes the original exception.
It never patches contextlib or calls an exception diagnostic hook.

`native_owner_session_cleanup_error` remains the exact OS3 session-close failure.
Distinct boundary failures retain their exact exception and captured traceback
pairs in `native_owner_context_boundary_failures`; `native_owner_context_guards`
retains each nested guard. The current guard and original owner remain exposed
for explicit custody inspection. Failed entry and uncertain exit are not replayed.
An entered manager receives its real failure on its one exit. Suppression, an
invalid response, or swallowed same-guard transition refusal is a recorded failure.
A foreign thread cannot consume the original thread's entry or exit.

These tests execute the real public contexts over controlled ports with native
DLL loading and process creation forbidden. Python thread/lock fixtures are
owned and joined. They qualify this exception/lifecycle boundary only; the full
joined native regression and genuine consent/effect journey remain pending.
