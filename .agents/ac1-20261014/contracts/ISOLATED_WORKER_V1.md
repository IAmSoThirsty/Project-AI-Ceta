# Isolated owned Windows worker — version1 / AC1

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
System32 PATH and supplied TEMP/TMP scratch.

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

## Current native qualification disposition

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

## Next explicit boundary

A separate exact profile-creation proposal gives the fixed name/SID, zero
capabilities, exact CreateAppContainerProfile/DeleteAppContainerProfile APIs,
expected durable per-user profile objects, prior-existence protection and cleanup
verification. That proposal is preparation only. Actual host profile creation
requires the reserved approval; no candidate test or availability flag supplies it.
After authorized environment repair, a fresh qualified successor must execute
all blocked actual bypass/access/retirement cases and distinct review before
runtime activation. Old unavailable receipts remain historical.

Primary references:
[Unpackaged AppContainer requirements](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-),
[SECURITY_CAPABILITIES](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_capabilities),
[Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control),
[SetNamedSecurityInfoW](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow).
