# Canonical wire profile, implementation increment 1

Profile identifier: `ceta-json-integer-nfc-v1`. Parent requirements: REQ-06-02 and REQ-06-03. This is an engineering implementation choice, not an owner ratification or completed Gate A.

After the owner's rescission and resume, the authoritative implementation moved
to the mapped desktop namespace recorded in `handoff/owner_scope.json`. This
file and the package's early contract source are retained as pre-transfer
working history. Current amendments, Unicode-version rejection, schema/date
repairs and the actual second-implementation comparison belong to
`T:\00-Active\CETA-desktop-delivery-20260906\rebuild_ios`. Use its source-bound
evidence rather than treating this historical copy as a second runtime.

The supplied twenty version-1 record shapes use only objects, arrays, strings, integers, booleans and explicit null. The decoder accepts strict UTF-8 JSON, rejects duplicate keys at every object depth, and rejects non-finite, fractional and exponent-form numbers. Integers are signed 64-bit values. Wire messages are bounded to 1 MiB and nesting to 32 levels before JSON materialization.

Strings must already be NFC and contain valid Unicode scalar values. The decoder rejects ambiguous normalization; it does not rewrite original input. Security identifier patterns must match the whole string. Date-times require a complete date, time, seconds and explicit UTC offset. Shape-valid timestamps remain untrusted until the identity/time owner checks freshness.

Canonical bytes use UTF-8, ascending Unicode key order, compact separators, unescaped Unicode and decimal integers. This is a CETA profile, not a claim of implementing RFC 8785. The record commitment is SHA-256 over `CETA:record:ceta-json-integer-nfc-v1:<record_type>` followed by a zero byte and canonical bytes. Original-wire hashes are separate. Event signatures and chain heads are not inserted into their own preimages.

The codec accepts only the exact schema vocabulary used in the supplied file. New schema vocabulary or versions require an explicit implementation amendment. Unknown keywords and remote references are rejected. The core receives an injected schema and has no filesystem, network, UI, model, or mutable-store dependency.

`tools/check_contracts.py` exercises the supplied examples through the real codec. Contract tests cover malformed input and byte commitments. These checks do not authenticate an actor, validate a signature, issue a grant, admit an operation, establish independent review, or qualify an installed product. The canonical profile remains subject to full source reconciliation and the required second implementation comparison before Gate A closes.
