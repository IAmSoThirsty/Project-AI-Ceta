# Project-AI: CETA canonical wire profile

Profile identifier: `ceta-json-integer-nfc-v1`. Parent requirements: REQ-06-02 and REQ-06-03. This is an engineering implementation choice, not an owner ratification or completed Gate A.

The supplied twenty version-1 record shapes use only objects, arrays, strings, integers, booleans and explicit null. The decoder accepts strict UTF-8 JSON, rejects duplicate keys at every object depth, and rejects non-finite, fractional and exponent-form numbers. Integers are signed 64-bit values. Wire messages are bounded to 1 MiB and nesting to 32 levels before JSON materialization.

Strings must already be NFC and contain valid Unicode scalar values. The decoder rejects ambiguous normalization; it does not rewrite original input. Security identifier patterns must match the whole string. Date-times require a complete date, time, seconds and explicit UTC offset. Shape-valid timestamps remain untrusted until the identity/time owner checks freshness.

NFC uses the frozen Unicode 15.0.0 tables. The Python implementation rejects a different loaded Unicode table version rather than changing the meaning of the same profile identifier. The Rust comparison uses `unicode-normalization` 0.1.22, whose source declares the same table version. Python 3.12.10 is the currently observed implementation toolchain; other Python versions require separate admission against this profile.

Canonical bytes use UTF-8, ascending Unicode key order, compact separators, unescaped Unicode and decimal integers. This is a CETA profile, not a claim of implementing RFC 8785. The record commitment is SHA-256 over `CETA:record:ceta-json-integer-nfc-v1:<record_type>` followed by a zero byte and canonical bytes. Original-wire hashes are separate. Event signatures and chain heads are not inserted into their own preimages.

The codec accepts only the exact schema vocabulary used in the supplied file. New schema vocabulary or versions require an explicit implementation amendment. Unknown keywords and remote references are rejected. The core receives an injected schema and has no filesystem, network, UI, model, or mutable-store dependency.

`tools/check_contracts.py` exercises the supplied examples through the real codec.
Retained comparison documentation reports 27,513 Rust/Python wire vectors.
That result belongs to its original source, runner and environment cut; it
is not a fresh qualification of the consolidated repository. Preserve its
raw receipts and failures, then rerun the required comparison on the
destination candidate. Parsing and framing do not authenticate an actor,
verify a signature, issue a grant, admit an operation or qualify an
installed product. Gate A remains open until its full criteria run.

The codec's record commitment identifies the complete canonical wire record. The
distinct event-chain head, signing preimage and temporal predicates are defined
in EVENT_AND_TIME_V1.md and implemented in the pure contract leaf. Shape-valid
timestamps remain untrusted. This increment rejects leap seconds and unknown UTC
offset for freshness. Store, signature verification, authenticated time and
authority integration remain unfinished.

The sole current implementation destination is `T:\00-Active\Project-AI-CETA`.
This path becomes active after the authorized build-package rename and
verified consolidation. The desktop worktree remains a read-only input.
Original profile documents and receipts are preserved as historical evidence.

Active publication or application of this profile is BLOCKED until
`EVENT_AND_TIME_V1.md`, `events.py`, `temporal.py`, their tests and required
schema/example/vector inputs have been captured with hashes, included in
the destination integration unit, reviewed, and the required tests executed.
A pinned input or reviewed plan is not executed product qualification.
