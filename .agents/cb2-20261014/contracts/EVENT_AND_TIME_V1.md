# Event and temporal contract increment

This is a source-tested WP-01 engineering increment. Parent obligations are
REQ-06-02/03, REQ-07-05 and REQ-19-04. Source-linked applicability and unresolved
dependencies remain in the adjacent specification ledger. Gate A remains open.

`src/ceta/contracts/events.py` consumes a strict version-1 EventRecord. The exact
event body includes every schema field except `signature_ref`. The
`signer_key_ref`, prior head, scope, sequence, actor/session, causation, recorded
time and payload commitment remain in the body. Unknown profile/version or a
future final-hash field is rejected. A signature reference requires a signer-key
reference. No private key is handled here.

The chain head is SHA-256 over ASCII `CETA:event-head:ceta-json-integer-nfc-v1`,
one zero byte, then canonical body bytes. Signing bytes use the separate ASCII
domain `CETA:event-signature:ceta-json-integer-nfc-v1`, one zero byte, then the same
body. An unkeyed event has no signing preimage. Attaching a signature leaves the
head and signing bytes unchanged; the generic full-record commitment changes.
This is deterministic preimage construction, not signature verification or an
authorization decision. A future identity service must resolve current keys,
authenticate the actor/session and verify the signature before evidence admission.

The injected accepted stream position starts at sequence zero with null prior
head. Later positions require a non-null accepted head. Successor checks bind
exact scope, sequence and prior head. Payload checks bind a strict typed record's
record ID, scope and full-record commitment. A null payload reference cannot
satisfy this typed-payload path. Other payload encodings require a separate
registered version and decoder. No writer, transaction, event registry,
projection, durable anchor, replay or effect is implemented by this contract.
Future store composition owns acceptance; a supplied StreamPosition is not proof.

`src/ceta/contracts/temporal.py` represents Unix wall time and monotonic time as
exact integer nanoseconds. Wall instants are signed 64-bit values; counters and
uncertainty are nonnegative signed-64-bit values. Conversion preserves up to nine
fractional digits without float rounding. Complete calendar/time and explicit
known UTC offset are required. Unknown offset `-00:00`, leap seconds, finer
precision and dates outside the nanosecond range are rejected. Their original
wire bytes can still be preserved for inspection; they do not pass freshness.

A sample records boot identity, durable epoch, resume generation, monotonic time,
wall estimate, uncertainty and trust availability. Only the authenticated time
provider may supply samples and their previous accepted sample. This pure module
does not observe clocks, authenticate samples, persist epochs or detect OS resume.
The future provider must retain rollback suspicion until trusted recalibration
and an attributable epoch change; it must not erase history or let a worker
replace previous samples. Injected trust flags are not credentials.

Issuance denies missing trusted time, obvious wall rollback, monotonic rollback,
changed boot/epoch/resume and expired or uncertain expiry. It caps lifetime at
both the requested absolute expiry and the configured maximum, using the latest
possible wall instant. Validation rejects at equality with either wall or
monotonic expiry. Existing deadlines retain their issuance anchors. A wall change
within the uncertainty interval cannot extend the monotonic cap. Restart, epoch
change and resume invalidate existing deadlines; new preparation requires fresh
admission. Consumed permits and budgets are a future durable-store responsibility
and are never reconstructed from a Deadline value object.

The manually specified vector in `contracts/vectors/event-preimage-v1.json`
includes a separate .NET SHA-256 result. The Rust serializer comparison covers
its full event and reordered body bytes. Event and temporal tests use synthetic
data and injected clocks. They do not qualify OS clock trust, authenticated IPC,
real permit redemption, cryptographic custody or an installed product.
