# Native owner approval transport v1

This component implements the Windows desktop consent transport for the declared
`OwnedCpuRequest` profile. It builds a real x64 executable using the installed
Windows SDK's `IUserConsentVerifierInterop::RequestVerificationForWindowAsync`.
The Python owner uses the existing `WindowsOwnedProcess` job/lifetime owner.
It creates no grant, enrollment, authority epoch, scheduler, store or approval
issuer. Active composition defaults stay closed.

## Trusted composition and remaining integration

`NativeApprovalOwner` is constructed by trusted composition with a local ordinary
helper path, its reviewed SHA-256 and an owned ordinary temporary directory.
Its path, code binding, native integrations and original opaque context are not
worker request fields. An executable hash binds the held file; it does not prove
every executing byte or isolate this library from an unrestricted same-account
process, debugger, administrator or changed Python code.

`availability()`, `inspect_request(OwnedCpuRequest)` and
`cancel_without_prompt(OwnedCpuRequest)` return retained sessions. These three
paths cannot call native authentication. Inspection constructs a hidden native
window and verifies the complete read-only text control's exact contents.

`begin_interactive(request, original_context=...)` requires a captured canonical
owner, a captured `NativeSessionClock.clock()` and a reviewed helper-source
commitment. The clock returns its owner-retained previous and fresh current
`ClockSample` pair. Trusted time, boot/epoch/resume continuity and the exact
request deadline are checked. There is no invented `.sample()` interface.

The proposed canonical integration is:

```
canonical_owner.retain_native_approval(request_wire, original_context)
    -> retained context manager
retained_lease.require_current(request_wire, challenge_id, ceremony_nonce,
                               measured_helper_evidence, original_context)
    -> exactly None
```

The same captured lease and exact original context remain held through the
native operation, final currentness checks and observed helper cleanup. No SQL
transaction spans the human wait. The actual canonical kernel/session owner
must implement and qualify this capability, the principal-to-OS-session binding,
evidence capacity and nonce consumption. An arbitrary callable or a controlled
test implementation does not establish that integration. Absence, noncallability
or malformed currentness/clock results deny before the interactive gate opens.

Enrollment remains unavailable: the canonical enrollment-body type, designated
root/profile bindings and kernel transition are separately required. A dictionary,
raw body, approved Boolean or this CPU request cannot substitute for enrollment.

## Exact private transport and display

One owner admits one outstanding session. It creates two anonymous 64 KiB pipes
and unnamed manual-reset cancellation/start events. Only the four explicitly
selected child ends are inherited. Parent ends and event originals are not
inheritable. The child receives decimal handle identifiers only; request bodies,
nonces and decisions never travel in argv or the environment. The child runs in
its owned job with a minimized environment and no unrestricted fallback.

The start event remains closed until the parent holds the exact image against
ordinary write/delete replacement, observes the child's PID/creation/image and
measures its primary token. Measured facts include user and logon SID,
authentication LUID, terminal session, restrictions, integrity, elevation,
UIAccess, token ID and modified ID. The native response repeats those facts;
the parent compares exact typed canonical values. `TokenHasRestrictions` and a
restricted-SID count are distinct measurements.

The request frame is little endian: magic `CETAAP01`, mode DWORD, timeout DWORD,
length-prefixed ASCII challenge ID, a fresh 32-byte nonzero nonce, length-prefixed
complete canonical request, request commitment and display commitment. The
bounded request is at most 32,768 bytes; the complete input is at most 40,960.
Timeout is an exact integer in 20..300,000 ms. The parent closes its writer, and
the native reader requires exact EOF before processing a request. Extra bytes,
unknown profiles/operations, noncanonical integer JSON, duplicate keys and
commitment mismatches fail closed. Availability has no request body.

The Python wrapper first validates and byte-freezes the declared request using
the reviewed pure contract decoder. The native executable is the exact-body
transport, not a second canonical domain authority: its own parser checks the
bounded canonical encoding, declared top-level profile/shape and commitments;
the trusted wrapper supplies full nested domain validation. Direct use of the
binary outside that composition does not constitute canonical admission.

Native mode 1 queries availability. Mode 2 constructs the hidden full display.
Mode 3 displays the native window and waits for genuine local input. Mode 4
returns cancellation without invoking availability or authentication. No mode
accepts a supplied result, Boolean, transcript or native status as approval.

The display contains the complete immutable canonical request, consequences,
source/policy/environment commitments, request commitment and display commitment.
Integers above IEEE-754 exact precision retain their original bytes. No JSON
floating-point reserialization participates in the displayed commitment. A real
interactive invocation additionally rechecks exact text readback, cancellation,
expiry, foreground HWND and hardware input origin before calling the desktop
interop API. Synthetic window messages do not constitute an approved input path.
The genuine hardware-input/Hello ceremony still needs its positive native test.

The response uses `CETAAO01`, a DWORD length and at most 16,384 bytes of exact
canonical JSON. It binds the challenge, nonce, mode, body/display digests and
commitments, native result/HRESULT, QPC interval and measured native provenance.
Unknown fields, Boolean/integer substitutions, foreign provenance, bad lengths,
trailing bytes and any noninteractive authentication result are rejected. The
observed SDK interop implementation must be the qualified ordinary System32
module; its actual file hash and native identity are retained. It supplies no
external signature over a CETA payload.

## Stop, timeout, failure and custody

`cancel_current()` publishes logical Stop without waiting for a poll/native-I/O
lock and signals the retained event. Stop before native input binding can result
in an explicit native protocol/runtime rejection with no approval result. Stop
after a completed result marks subsequent observations cancelled; an earlier
returned DTO never supplies enduring authority. The kernel must recheck and
consume the exact challenge under its current lease.

Native input has a 10-second engineering startup window; Python rejects late
startup before opening the gate. The actual ceremony has its own bounded
engineering timeout and the canonical deadline checks remain independent.
`wait()` returning None retains the session and every owned native resource.
`close()` refuses a live primary/descendant lifetime. It never claims that killing
the helper retires a separate OS authentication operation. Once an interactive
gate might have opened, failed startup requests cancellation and waits for
observed settlement; unresolved work remains owned. Genuine in-flight Hello
cancellation has not been tested unattended.

Synchronous Windows launch, token, file, pipe and COM calls depend on scheduling
and driver behavior. Elapsed-time checks detect late completion and bounded
buffers prevent unbounded payload growth; this is not a universal native-call
preemption guarantee. A stalled native operation remains an explicit dependency
of the retained owner.

Control exceptions preserve their exact primary object and expose
`owned_session`, `owned_process`, `cleanup_errors` and `close_cleanup`. Independent
cleanup attempts continue after an observed empty helper job even if another
release fails. Native out-handle storage is registered before fallible pipe,
token and duplication operations. The narrowly reused AC2 duplicate-object fence
prevents closing a reused integer handle during retry. If release of the last
duplicate itself is interrupted, `pending_native_cleanup` reports its uncertainty
and blind retry is refused. It is never inferred settled from a Boolean stub.

## Acceptance evidence and limits

The accompanying tests exercise the actual built helper, real disposable Windows
jobs/pipes/events/tokens, hidden text readback, malformed input, currentness/clock
denials, nonce/commitment/type binding, cancellation competition, primary/control
exception retention, actual handle-value reuse preservation and recovery. Existing
Windows job, identity pipe and temporal test bodies are retained unchanged.
Controlled responses and owner/clock fixtures qualify pure validation only.

The source/build/test manifests identify the exact compiler, linker, SDK headers,
binary, native library, raw IDs, failed attempts and source/environment snapshots.
Real user authentication, positive native approval, canonical owner integration,
authenticated kernel nonce consumption and enrollment are `NOT_RUN` or unavailable
as specifically stated above. A `NativeApprovalTranscript` is attributable result
data; its construction alone grants no authority.

Primary API documentation:
[desktop interop](https://learn.microsoft.com/en-us/windows/win32/api/userconsentverifierinterop/),
[UserConsentVerifier](https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverifier),
[input origin](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getcurrentinputmessagesource).
