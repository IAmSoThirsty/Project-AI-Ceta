# Isolated owned Windows worker — version1 / AC4 rejected-token diagnostics

Canonical owner: CMP-05 supervisor. Mapped dependency slice: CETA-11.02.01,
11.02.02 and11.02.03; RE-S3/T09–10/RE-03–08; SPEC-21/POL-13.

`IsolatedWindowsWorker` subclasses the existing `WindowsOwnedProcess` and reuses
its exact retained process/job lifetime, native launch image pin, poll/wait,
resource observation, terminate, observed empty-job close and error custody.
It does not create an authority issuer, scheduler, state store or evidence ledger.
The ordinary current `WindowsOwnedProcess`, service, kernel and closed defaults
are unchanged. This dependency is a trusted-composition native library; it is
not an arbitrary-command IPC interface or an activated real-effect profile.

## Exact creation

The controller supplies a pinned regular local executable, bounded argument
tuple, ordinary current directory, exact ordinary scratch directory, mandatory
SHA256 image commitment and bounded `CETA.*` container name. Shared reparse/ADS/
local-path checks run before native use. No user PATH, Python hooks, credential
variables or ambient environment is copied. The native Windows directory is
observed through its system API; environment is exactly SystemRoot, WINDIR,
System32 PATH, supplied TEMP/TMP scratch and LOCALAPPDATA. The additional path is
the current user's native FOLDERID_LocalAppData observation, obtained through
SHGetKnownFolderPath with KF_FLAG_DONT_VERIFY, without a create/init flag or an
inherited environment copy. It must identify an existing ordinary local
directory. Missing, malformed, unavailable or unqualified path observations
deny launch before CreateProcessW.

The launch derives a SID without CreateAppContainerProfile. It declares zero
capabilities and a restricted-child creation policy, explicit permitted handles,
atomic job membership, one active process and KILL_ON_JOB_CLOSE. Creation is
suspended. Exact process creation time, job membership, image-file identity and
actual token facts are verified before resume: AppContainer true, expected SID,
zero capabilities, exact low-integrity RID4096 and restricted token.

The same pinned file's native volume-GUID path and pinned ordinary directory
are used for restrictive creation. This does not map a new drive, copy resources
to another project or change host configuration. It is no fallback to a broader
security token. Any unsupported attribute, missing asset/pin/handle or native
failure denies creation; the library never retries without restrictions.

`IsolationTokenFacts` is a copied typed measurement record. Its fields do not
authorize dispatch and synthetic records establish only their shape. Startup
token facts are startup observations, not uninterrupted currentness or trusted
human approval. A future canonical execution lease must supply current scope,
authority, revocation, Stop and protected-target/evidence guarantees.

## Files, rights and native probe

The controller must provision and qualify exact assets/scratch ACLs. AC1 changes
only fresh owned fixture permissions: assets are read/execute, scratch is modify
at low integrity, and state/policy/source-like sentinels stay medium/protected.
DACL and label writes are separate and independently recorded. No Source/E3 ACL,
account, firewall, loopback exemption, protection setting or elevation changes.

The fixed Rust helper supports bounded CPU/hold and disposable qualification
probes. It executes no shell, source/cache, dynamic import, SQL or secret input.
Native probes declare attempted sentinel reads/writes, trusted fixture process
rights, child/breakaway creation, excluded event access and owned local socket
operations. A unexpectedly created child remains suspended and is immediately
terminated/observed, with the failed qualification retained. Output is bounded
by the caller and contains safe facts/errors/sizes rather than protected data.

Explicit resource operations are READ of own assets/fixture observations; WRITE
of newly owned fixture data/scratch and permissions; HOST creation and retirement
of owned jobs/processes/pipes and disposable local listener controls. The trusted
medium fixture and accessible loopback control prove their own setup, not an
AppContainer security boundary. Host OS/kernel and privileged owner/admin remain
assumptions. Job ownership alone is not filesystem/network/credential isolation.

## Failure and recovery

Resource ownership transfers to the canonical process owner immediately after
CreateProcess succeeds and before fallible inspection. Failed post-create
inspection requests termination, observes exit/empty job and closes. Unresolved
custody is returned through IsolatedLaunchError with that exact process owner.
Residual file/job handles and allocated SIDs stay explicitly retryable. A
KeyboardInterrupt/SystemExit or other primary exception survives a secondary
finalization failure with its exact cleanup object attached. No destructor
silently closes live work and no failed restriction is hidden by fallback.

Native calls are synchronous. Observation/deadline rejection does not claim to
preempt Windows/kernel/driver occupancy. Successful CloseHandle/FreeSid and
observed exited/empty ownership are distinct from requested cleanup. Cached
startup facts, process exit alone or a Stop flag are not terminal custody proof.

## Historical AC1 native qualification disposition

Actual no-profile AppContainer CreateProcessW attempts on this host returned
ERROR_FILE_NOT_FOUND2 using a verified T: NTFS image, its exact volume-GUID alias
and fresh read/execute asset/ancestor ACLs. No restricted worker was published.
The internal cause is UNESTABLISHED. Microsoft documents an AppContainer
definition/profile for ordinary unpackaged deployment; AC1 has not created one.

Therefore positive actual worker token, allowed asset/scratch, forbidden
state/process access, child escape, inherited event and network/listen outcomes
remain **NOT_EXECUTED / BLOCKED_BY_RESTRICTIVE_LAUNCH**. Passing binding, native SID,
resource cleanup and actual safe-denial tests qualify those exact properties.
They cannot certify the missing positive isolation boundary or activate CETA.
No unittest skip is used to turn those unexecuted obligations into passing cases.

The native helper compiled with the observed installed rustc1.96.1 Windows x64
GNU toolchain and static CRT, without download/install. Build receipts pin source,
resolved real compiler, trampoline descriptor, exact image and output. The first
Rust trait error and installed-tool-alias measurement failure, first combined
ACL/label error5 and every restrictive error2 remain retained separately.

## Profile-operation approval boundary

A separate exact profile-creation proposal gives the fixed name/SID, zero
capabilities, exact CreateAppContainerProfile/DeleteAppContainerProfile APIs,
expected durable per-user profile objects, prior-existence protection and cleanup
verification. That proposal is preparation only. Actual host profile creation
requires the reserved approval; no candidate test or availability flag supplies it.
After authorized environment repair, a fresh qualified successor must execute
all blocked actual bypass/access/retirement cases and distinct review before
runtime activation. Old unavailable receipts remain historical.

## AC2 cleanup custody and uncertainty

The original public launch and SID interfaces are retained. Native finalization
attempts every independent queued cleanup operation even after an earlier failure.
The original `KeyboardInterrupt` or `SystemExit` object remains the raised object;
its `isolation_cleanup` retains the exact API/owner and exposes
`pending_native_resources`. Explicit `close_cleanup()` retries known pending
operations and preserves a currently live canonical process owner if close is
not yet permitted. A secondary diagnostic or `add_note` failure cannot replace
the original exception.

Handle retries keep a noninheritable duplicate and compare the underlying kernel
object before closing the original numeric slot. A closed or reused slot is not
closed again. This cleanup mechanism requires the Windows 10 or later
`CompareObjectHandles` API from System32 KernelBase; unavailable binding denies
construction. Native object comparison is an ownership safeguard for cleanup,
not a grant for workload execution.

SID, local-string and attribute-list finalizers record uncertainty before an
operation whose completion may become unobservable. A native failure returning
the exact still-pending allocation permits explicit retry. An interrupted call
or malformed result retains an `UNCERTAIN` record and refuses blind replay,
because the allocation may already have been released. Attribute-list deletion
has no native status return; an exception after deletion therefore retains its
buffer and uncertainty while unrelated handles/SIDs still receive cleanup.
These retained uncertainty records remain unresolved observations and are not
reported as successfully retired resources.

AC2 qualifies the three reproduced cleanup defects, known-refusal recovery,
native handle-slot reuse, concurrent explicit token recovery, independent cleanup
and post-call uncertainty on owned disposable resources. It creates no profile
and does not qualify a successfully restricted worker. All AC1 positive isolation,
post-create restricted-child recovery, runtime authority and activation obligations
above remain open after the observed no-profile CreateProcessW error 2.

Primary references:
[Unpackaged AppContainer requirements](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-),
[SECURITY_CAPABILITIES](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_capabilities),
[Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control),
[SetNamedSecurityInfoW](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow).

Cleanup references:
[CompareObjectHandles](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-compareobjecthandles),
[DuplicateHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle),
[FreeSid](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-freesid),
[LocalFree](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-localfree),
[DeleteProcThreadAttributeList](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-deleteprocthreadattributelist).

## AC3 qualification boundary and native path custody

One separately authorized profile attempt following AC2 created the exact
reserved profile, observed restricted CreateProcessW failure203, retired every
captured resource, deleted its own newly created profile and observed folder
absence. Its retained receipt is under
`.agents/runtime/ac2-20261014/profile-tool-repair-r2/profile-qualification-7b716b95d15f440a90d6be98a666014c/RESULT.json`.
Positive worker isolation remains unqualified. The internal cause of error203
is unestablished; adding LOCALAPPDATA is a documentation-supported candidate
variant, not proof that the launch failure has been repaired.

The known-folder output slot is retained before the native query. A returned
HRESULT, including failure with an allocation, permits exactly one known
CoTaskMemFree cleanup. An interrupted query or unobservable free retains an
UNCERTAIN record and refuses blind retry. Independent handles/SIDs still receive
cleanup; the original control/error object and explicit cleanup owner remain
available. Known-folder text/path validation runs before the buffer is freed.

The original environment method and public launch signatures are retained.
Native tests qualify the six-key construction, API/GUID/flag binding, real
allocation cleanup, denial, response loss, concurrency and existing resource
recovery. The historical actual restricted-create test stays in source but is
not executed in AC3's current cohort because no additional profile or restricted
launch attempt is authorized. Any future attempt requires a separately reviewed
exact tool and a fresh explicit host approval. No failed isolation request falls
back to an unrestricted worker.

Environment references:
[AppContainer profile environment](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer),
[SHGetKnownFolderPath](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath),
[Known-folder flags](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/ne-shlobj_core-known_folder_flag),
[FOLDERID_LocalAppData](https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid).

## AC4 rejected-token observations and current qualification disposition

The separately authorized AC3 attempt on 2026-10-15 created its own reserved
profile and one suspended restricted process. Native token qualification raised
`ISOLATION_TOKEN_NOT_QUALIFIED`. The retained process owners retired, the tool
deleted its own profile and a subsequent native folder query observed absence.
The individual rejected token values were not retained in that historical
receipt; which exact predicate failed remains unestablished. No successful
isolation, access-denial probe set or canonical real effect is established.
The evidence is retained under
`.agents/runtime/ac3-20261014/profile-tool/profile-qualification-a82d795283474f5daa218f8c158d5047/RESULT.json`.

The one authorized post-cleanup original denial regression passed its existing
assertions and retired its disposable medium control. Its raw restrictive launch
error was 267. The original unanchored `:2` regular expression also matches
`:267`; that test result supports bounded denial and cleanup, without proving
an exact error 2 or attributing error 267 to profile absence. The unchanged
historical assertion and raw evidence remain available for separate repair.

On a token-read or qualification failure, AC4 attaches a copied, bounded
`native_isolation_token_observation` dictionary to the same primary exception.
Its classification is `REJECTED_NATIVE_OBSERVATION`. The stage names the operation
that was in progress. Fields appear only after their native measurement or
conversion completed: raw AppContainer DWORD, expected-SID comparison,
capability count, integrity SID/RID, AppContainer SID, `IsTokenRestricted` result
and observation timestamp. SID diagnostic text is bounded to 192 characters.
An absent field means unobserved; measured zero remains zero. Native token
buffers, addresses, handle values and token contents are excluded.

The observation is diagnostic data. Every existing `IsolationTokenFacts`
qualification predicate remains unchanged. Diagnostic attachment uses the
base exception dictionary and preserves an exact `KeyboardInterrupt`,
`SystemExit` or other primary object even when attribute hooks refuse access.
Native handle ownership, uncertainty and explicit cleanup retain their existing
behavior. A secondary cleanup failure cannot replace the primary diagnostic.

AC4 parser fixtures establish rejection/measurement behavior only. Its actual
native test reads the current process token, derives and frees SID memory, and
observes token handle retirement; it creates no profile or worker. The preceding
AC3 profile approval has been used. Any further positive qualification attempt
requires a freshly reviewed exact tool and a new explicit profile-operation
approval. Positive isolation and runtime activation remain unqualified.
