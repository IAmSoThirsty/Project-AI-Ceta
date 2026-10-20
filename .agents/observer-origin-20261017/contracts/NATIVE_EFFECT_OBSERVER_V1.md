# Native CPU effect observer v1

Platform observation port for CMP-15 independent outcome verification and
CETA-11.03.03, in the assigned effects platform namespace; selected real-effect
plan RE-S6/RE-T21–23. The Python driver is
`src/ceta/effects/native_observer.py`; the fixed native source is
`native/windows_broker/effect_observer.rs`. The existing RC2
`CpuEffectObservation` owns the result shape. The observer creates no permit,
policy, durable state, scheduler, resource lease or evidence ledger.

Trusted composition constructs `NativeCpuEffectObserver` from an exact compiled
image path/hash, the commitment over that image and Python driver bytes, and the
captured NC2 `NativeSessionClock`. The executable path is configuration rather
than request data. `observe(OwnedCpuRequest, WindowsOwnedProcess, cancelled=...)`
returns a typed observation or an exact error retaining unresolved custody.
An optional event cancels observational work; it supplies no positive authority.
Default runtime admission and selected profile activation remain other owners'
responsibilities.

`require_observation_origin(request, target, observation)` returns exactly
`None` only for this observer's last successfully returned observation object,
the identical retained target owner, the original canonical request and
observation bytes, and the observer's current sequence. A canonically equivalent
decoded request is accepted; a copied, reconstructed or decoded observation is
rejected even when its canonical bytes are equal. The retained origin belongs
to this observer instance and cannot be transferred by copying the observer.

A valid observation attempt admitted by the nonblocking request lock invalidates
the preceding origin before source, sequence, clock or native checks. A refused
busy call or invalid input does not supersede it. Origin publication occurs only
after protocol and lifetime validation, physical custody retirement and diagnostic
finalization. Failure, cancellation, unresolved cleanup or diagnostic failure
cannot publish the computed value. Explicit cleanup never promotes a failed
attempt into an origin. Diagnostic evidence is a detached report and supplies
no positive provenance proof.

The predicate uses retained local objects and canonical bytes. It performs no
SQL, native query, clock sample, transport operation or wait; concurrent observer
use is refused immediately. Provenance does not establish current permission,
freshness, target lifetime or effect success. A genuinely returned `UNAVAILABLE`
observation may have proven origin and still has an unavailable outcome.

Integration dependency: the kernel outcome guard receives decoded DTOs. Its
captured owner adapter must retain the original observer and returned observation,
compare the decoded observation's canonical wire to the original, and pass that
original object to this predicate with the captured target. The current
`NativeOwnerView` has no capacity/provenance port; that adapter remains separate
work. This predicate alone does not qualify canonical execution or owner outcome
acceptance.

`WindowsOwnedProcess.export_cpu_query_handles` duplicates the retained target
process with `PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE` (0x101000) and its
exact job with `JOB_OBJECT_QUERY` (0x4). Separate noninheritable duplicate guards
protect explicit close retry against ordinary numeric handle reuse. The owner
retains the export; target close refuses until the bound observer's primary
lifetime, empty job and handles are observed retired and the export is closed.
Target termination remains available while an observer is outstanding.

These access requirements agree with the documented
[IsProcessInJob](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob)
and [QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)
interfaces. Actual disposable native tests establish the current host behavior.
The observer receives no target Set/terminate/duplicate right and does not open
a target from a PID, job name or caller pathname. Its fixed native program has
no target-mutation or process-creation entrypoint.

The canonical process launcher supplies a suspended, explicitly job-assigned
observer and exactly five inherited handles: the two narrowed target handles,
stdin read, stdout write, and stderr write. Other parent channel ends and guard
handles are excluded. The fixed request is 240 little-endian bytes; the fixed
response is 288 bytes. Input/output include a fresh 32-byte transport nonce,
sequence, complete request/code/job commitments and exact native target/observer
PID, creation time and image SHA-256. Native query facts include membership,
exit availability/value, QPC interval/frequency and raw class-15 DWORD policy.
Extra fields, short/long/trailing bytes, wrong identities/bindings, diagnostics
or nonzero process exit reject observation. Stderr is bounded to 1,024 bytes.

The separate process independently queries the retained target and actual job
policy. It hashes the native-reported executable through a read-only, no-write/
no-delete shared file handle, checks native file identity/size/write metadata
around the bounded read, and retains that handle through hashing. Images over
128 MiB are unavailable in this profile. Both target lifetime/membership checks
bracket the class-15 query. Disabled policy `(flags=0,value=0)` is a measured
value; missing/failed native telemetry never becomes a measured zero.

The parent measures actual observer lifetime/code and independently queries the
target policy before/after the separate observation. A measured result requires
agreement of policy and observed version, live target membership, actual child
identity, and fresh NC2 clock samples bracketing the native QPC interval. Its
published `clock` is the actual parent sample at the beginning of that interval,
a conservative freshness bound rather than an invented exact measurement time.
The whole accepted interval must fit the request's maximum duration and current
deadline. Kernel/driver native call occupancy is not preemptible by Python; late
returns are rejected. Clock failure, replay, cancellation, contradictory policy
or lost lifetime cannot yield a measured accepted result.

Primary process exit and an empty job are separate observations. Cleanup polls
the actual observer job within a two-second bound and retains custody on an
unobserved empty state. It retires that observer before releasing target query
handles. Partial launches, pipe failures, unknown close responses and pending
exports remain caller-visible through `NativeObserverError` or the primary
exception's `observer_custody`; explicit `close_cleanup` performs only safe
known-resource recovery. A guard-close response of unknown effect is retained
instead of blindly replayed. No destructor hides closure or kills unrelated
work. Returned diagnostic evidence is detached from the retained facts.

Tests use declared disposable Windows jobs, actual compiled native observers,
actual NC2 samples and the RC2 codec/comparator. Controlled frame/callback faults
are labelled. Separate negative binaries test actual excess output, silence,
and denied Set/Terminate attempts through inherited query-only handles; they
are engineering fixtures, never production registered observer code. Native
process, thread, query, pipe, clock and fixture identities/closure are captured
with raw outputs. This scope observes exact CPU policy, not every filesystem,
network, utilization or transitive effect, and does not accept the public
real-effect journey, owner authentication, AppContainer isolation or full unit.
The parent, observer, host owner/admin and Windows kernel remain shared trust
assumptions; this is separate-process observation rather than external
attestation or protection from a hostile trusted parent.

## OB2 source-pin and diagnostic custody successor

The rejected OB1 cut allowed a source-file close failure to replace an original
hash interruption. OB2 keeps source pin ownership in a dedicated private object
before hashing. A noninheritable duplicate retains the exact file object for
ordinary numeric-slot close retry. Source hash publication requires successful
retirement of both the original and guard handles. A close response lost after
the original slot was retired cannot cause a replacement object to be closed.
An unobserved guard allocation or guard-close effect stays UNCERTAIN and refuses
blind replay.

The exact original error/control object remains the raised object. Its canonical
BaseException storage exposes `source_hash_custody`, `source_hash_cleanup_error`
and `close_cleanup`; the custody object's `pending_native_resources()` and
`close()` retain the known/uncertain native state. Optional note or attribute
hooks cannot substitute a diagnostic failure for that original object. No
exception truth-value hook decides which failure is primary.

Observer evidence collection also runs behind primary-preserving finalization.
A secondary evidence failure cannot hide native custody or leave the observer
request lock held. It suppresses publication of an otherwise computed result;
the retained evidence records acceptance false. Primary errors expose the exact
`observer_custody` and `close_observer_cleanup` without overwriting separate
source-file custody. Closed native resources remain closed even when producing
their diagnostic representation fails.

The unchanged Root failure body is executed with only its candidate-path
relocation and additional executable repair assertions. Native source-pin tests
exercise real file handles, duplicate guards, response loss, numeric event-slot
reuse, hostile error hooks and explicit recovery. Controlled unknown-effect
cases retain product uncertainty even when the fixture independently retires
its own exactly captured native allocations. The original thirty observer
methods and 689 connected throttling methods remain unchanged and are required
again for this successor. No independent review or Source acceptance is borrowed
from the rejected OB1 cut.
