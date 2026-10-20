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
