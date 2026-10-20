# Owner enrollment DATA contract — EN1

Ownership remains CMP-04 identity and the existing CMP-02 kernel/store.
Mappings: CP1 bootstrap/trust boundaries and principal/authenticated-session
contracts; approved real-effect plan RE-T04/T05/T06 and RE-01/02/09/32.
This is an immutable input/display/transcript contract. It issues no grant,
epoch, token, permit or trust-ready transition and calls no native service.

## Exported values and data binding

`NativeObjectIdentity(path, kind, volume_serial_hex, file_id_hex)` represents
native observation data. Paths accept one spelling: absolute
`\\?\Volume{lowercase-canonical-guid}\ordinary-components`. ASCII components
are bounded to 64 characters and 16 levels, with no dot segments, ADS, alternate
device/DOS/UNC prefixes, short-name tildes, reserved DOS names, repeated or
trailing separators, trailing dots/spaces or Unicode aliases. Component case is
preserved exactly. A different case spelling does not match the expected root.
Volume serial and file ID use exactly 16 and 32 lowercase hex digits. This permits
full unsigned 64/128-bit identities without signed-wire overflow. Measured zero
is representable; missing/Boolean values are rejected. The codec never opens a
path, traverses an ancestor, verifies ACLs, or establishes absence of reparse
points. The retained native owner must measure the same final volume-GUID path,
ordinary object kind and native IDs from its actual handles at use time.

The designated private root is a directory. Its canonical database is the
existing store's exact immediate child `history.sqlite3`, kind file, on the same
volume with a distinct file ID. Root/copy/path identities must match the full
captured expected request. Native conservation and copy detection remain owner
observations, rather than facts inferred from these typed strings.

`OwnerTokenFacts` binds exact process lifetime/image, user/logon/integrity SIDs,
authentication/token/modified LUIDs, terminal session, token type, impersonation
level, integrity attributes, elevation type, UIAccess, restriction flag and a
bounded sorted unique restricted-SID tuple. Flags are strict integers 0/1, with
None distinct from a measured zero. SIDs have canonical decimal components and
native width bounds; LUIDs are fixed 16-digit hex. These fields represent raw
facts; they do not authenticate an interactive user or qualify a token. Native
owner policy must resolve actual origin, session trust and allowed token class.
Every process creation time is also within the signed canonical wire domain.
The same PID cannot describe conflicting simultaneous lifetime/image facts.

`EnrollmentRequest` binds installation/project/principal/actor scope, owner and
clock sessions, fresh expected challenge/ceremony nonce, root/database/token
facts, helper/UI identities, current policy/authority generations, exact
policy/source/environment/helper/UI/adapter/worker-image commitments, budgets,
resources and deadline. Its fixed envelope is `ceta-owner-enrollment-data-v1`,
`OWNER_ENROLLMENT_REQUEST`, `DATA_ONLY`, runtime profile
`ceta-owned-real-effect-v1`, one worker and exactly two possible effects:
`owned-worker.cpu-cap` followed by separately approved
`owned-worker.cpu-restore`. No arbitrary command, project, profile, model call,
token allowance or approval Boolean is accepted. Enrollment itself permits
neither effect; each still needs its own canonical approval and single-use intent.
The fixed `operation_limits` allows one of each operation, and `approval_mode`
explicitly binds `SEPARATE_CANONICAL_APPROVAL_PER_EFFECT` into the display.

## Limits

Request/transcript codecs accept at most 32768 bytes, exact canonical integer/NFC
wire, exact fields and nested shapes. Duplicate/unknown/missing fields,
noncanonical spelling, Boolean integers, floats, overlarge integers and enum
extensions are rejected. Constructor inputs use frozen typed records and tuples;
returned dictionaries/lists are independent projections.

Session lifetime is at most 300 seconds. Each effect duration is at most 1 second;
maximum observation age is at most 5 seconds. Clock uncertainty is capped at 250ms.
The deadline uses the existing `Deadline`/`ClockSample` rules, the actual native
boot-GUID/session-nonce spelling, matching owner-supplied clock session, durable
epoch and resume generation. Wall/monotonic rollback, expiry, missing trusted
time, wrong boot/session/epoch/resume, excessive uncertainty or sample gap deny
the data-currentness predicate. Clock samples and expected requests must come
from captured canonical owners. Both clock value records are revalidated before
the existing temporal predicates. Caller-supplied time or flags create no trust.

Authority budgets fix two effects and zero model/input/output token allowances;
recovery reserves one effect. Total and recovery wall budgets must cover their
declared bounded effect durations and fit the session. Read budget is at most
16MiB and write budget at most 1MiB. Required evidence reserve is 8192..1048576
bytes, with at least 4096 recovery bytes and conserved contained recovery budget.
After subtracting the recovery reserve, the cap still requires at least 4096
evidence bytes and its full declared effect wall duration.
The resource ceiling is 1..1000 CPU milli, 1..64MiB memory, 8192..16MiB storage and
a session-bounded wall budget covering both effect durations. Evidence must fit
storage/write limits. These are declarations, never observations of capacity or
physical provisioning; native/resource/canonical admission remains required.

## Display, transcript and replay

`canonical_wire`, `input_commitment`, `decode_enrollment_request`,
`enrollment_display_bytes` and `enrollment_display_commitment` include every
field and fixed envelope value. Input and full display use separate existing
kernel SHA-256 commitment domains. Genuine UI must render the complete returned
display data and bind the exact bytes/commitment without omitting limits.

`require_enrollment_current(request, expected, previous_clock, current_clock)`
requires complete canonical expected equality and fresh temporal bounds. It is
a pure DATA predicate. Repeated validation does not consume a challenge; the
existing canonical kernel must atomically consume the exact authenticated
challenge once and reject replay, copied roots and stale generations at commit.

`enrollment_transcript_bytes`, `decode_enrollment_transcript` and
`enrollment_transcript_commitment` wrap the unchanged RC2
`NativeApprovalTranscript` in the explicit enrollment kind and separate domain.
`require_enrollment_transcript_binding(request, expected, transcript,
previous_clock, current_clock)` checks challenge, nonce, full request/display,
principal/session, helper/UI code/lifetime, declared verified native result,
and bounded observed time. A bare effect transcript is rejected by this codec.
`REPORTED_VERIFIED` is DATA. A DTO or digest authenticates no ceremony; the
native helper must authenticate origin, kind, channel, measured identity and
currentness. UserConsentVerifier is not a cryptographic payload signature.

No global registry, competing store, authority issuer or replay ledger exists in
this module. Human wait stays outside the writer transaction. Source publication,
native owner enrollment/authentication, single-use commit, actual native root
observations, epoch provisioning and effect admission require their separately
reviewed implementation and genuine owner ceremony. Tests here use explicit
deterministic DATA fixtures and establish no native or owner acceptance.
