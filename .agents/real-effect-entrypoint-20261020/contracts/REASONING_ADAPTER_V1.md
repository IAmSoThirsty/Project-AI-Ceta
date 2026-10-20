# CETA reasoning adapter contract

The owner-integrated V1/F source at commit `83fc9432b4a37ee7f91d6c5b0d358a015548aed4`
is an advisory dependency. The active adapter is `src/ceta/reasoning`. Retained
vendor files and original ZIPs remain unchanged. This contract describes the
adapter's executable boundaries; it does not qualify canonical governed effects.

## Source identity

Both original archives must match their pinned SHA-256 values. Extracted Python,
package resources, F configuration and schema files must match archive bytes and
membership. Linked/reparse members and added executable files are rejected.
The import finder owns only `societal_reasoning` and `truth_accountability` and
executes captured archive source. It reads package resources from those same
snapshots and never uses vendor bytecode caches or changes `sys.path`.

Preloaded foreign modules, changed verified origins, removed modules, removed
finders and subsequent source changes reject another initialization. Repeated
successful loads share verified modules; new sessions receive independent V1
reasoners and ephemeral in-memory reference ledgers. Provenance in a shared
Python interpreter supplies no OS isolation or protection against arbitrary
trusted code modifying that interpreter.

## Provider and assessment

`initialize()` verifies sources and constructs the actual V1/F pipeline with the
bounded local arithmetic verifier registered as `arithmetic`. `assess()` requires
an explicit provider implementing `generate_proposal`. It starts no model service
and chooses no synthetic provider. `SyntheticProposer` is retained solely as an
explicit legacy rejection fixture: its unsupported schema is rejected.

Speaker identity is a nonempty string up to 128 UTF-8 bytes; input text is up to
65,536 UTF-8 bytes without NUL. The vendor pipeline bounds proposal JSON at
32,768 UTF-8 bytes and rejects duplicate keys and unsupported proposal fields.
Context queries return one through ten explicitly unverified candidates.

The adapter classifies the vendor's actual quote, meaning-review and supported
arithmetic decisions as `ADVISORY_PASS`; held/unsupported/disputed decisions as
`ADVISORY_HOLD`; rejected, refuted and failed reviews as `REVIEW_FAILURE`. An
unknown decision is `NOT_EVALUATED` and withholds response/fact claims. Only an
actual `SUPPORTED_BY_CHECK` result with a literal true vendor fact flag sets
`established_fact`; this describes the reference check, not canonical authority.

Shadow mode defaults to true and withholds rendered responses. False permits
returning the reference renderer's bounded advisory text; it does not attach to
the application or grant a permit. Provider/runtime exceptions produce a
`PIPELINE_ERROR` assessment with `NOT_EVALUATED` context and retain the actual
exception in `last_error`. They do not falsely claim source unavailability.
Provider attribute admission runs under the busy guard and captures its callable
once. Admission errors propagate before source preservation and leave the
session open; provider descriptors cannot retire or reenter that admission.

## Lifecycle and attachment

A session is confined to its initializing thread. Reentrant operations and
foreign-thread assessment/retirement are rejected. Partial initialization closes
its created core; if cleanup fails, the primary exception retains the actual
secondary exception as `reasoning_cleanup_error`, and the session retains its
core for an explicit close retry. Close stops new admission before retirement;
failure propagates and preserves custody. Successful close clears initialized
state, retires the core, is repeatable, and makes that instance terminal.
Diagnostic attachment uses the raw `BaseException` dictionary descriptor so an
exception subclass cannot replace the primary error through attribute hooks.

`ShadowModeController` requires literal boolean host attestations. Initial
`ADVISORY_ATTACHED` and transitions involving attachment require true
authorization. This local attestation is not a CETA capability or kernel grant.

## Assessment encoding

`ReasoningAssessment` is frozen and validates typed outcomes, tuple references,
bounded strings, explicit status identifiers, booleans and SHA-256 digests.
`canonical_bytes()` uses sorted compact typed JSON schema
`ceta.reasoning-assessment.v2`; nulls and sequence boundaries remain distinct.
`commitment()` hashes that encoding with `CETA:reasoning-assessment:v2` domain
separation. This deliberately replaces the ambiguous original delimiter encoding;
v1 and v2 commitments must not be compared as if they used the same format.

## Acceptance evidence

The original 21 adapter tests remain unchanged. Added regressions exercise the
actual pinned pipeline, true/refuted arithmetic, exact quotation, advisory holds,
unsupported/malformed provider output, independent sessions, close failure,
partial initialization cleanup, thread/reentrancy boundaries, foreign module
rejection, resource loading, extracted-source tampering, export binding and
commitment collisions. Disposable mutable files remain under this T: repository.
Execution receipts and independent review are required before accepting the
repair. Model integration, application composition and governed execution remain
separate requirements with their own evidence.
