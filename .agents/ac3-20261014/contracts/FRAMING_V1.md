# Bounded record framing — working profile v1

Profile: `ceta-record-framing-v1`. Engineering contract only; whole Gate A
ratification and authenticated transport qualification remain open.

One frame contains a four-byte unsigned big-endian length followed by exactly
that many original UTF-8 record bytes. Body length is 1 through 1,048,576 bytes,
the existing strict wire limit. The length excludes the header. There is no
zero-body heartbeat, trailing padding, batched record or concatenated frame in
this API. Each body must decode as one of the existing twenty strict records.

`decode_frame_length(header)` validates the exact header before a transport
reads or allocates the body. The future transport must perform bounded header
and body reads with its own admitted identity, deadline, cancellation and
capacity policy. It must not allocate the raw unsigned length first. Partial
reads are accumulated within those limits; EOF or deadline before completion
does not become a completed message.

`decode_record_frame(frame, codec)` rejects oversized buffers, bad declarations,
missing or trailing bytes before record parsing. It validates only a complete
frame already held by the caller. It is not a streaming receiver and cannot
undo an allocation made by that caller. `frame_record(wire, codec)` checks the
body and preserves its original bytes; it does not replace signed/historical
bytes with a canonical reserialization. Existing canonical record commitments
and original-byte hashes remain separate and unchanged.

The framing prefix contains no profile version, sender identity, message ID,
receiver generation, nonce, authority or deadline. Actual session/profile
binding and the message envelope required by ARCH-02 remain separate unfinished
contracts. Do not auto-detect a framing version or treat a shaped record as an
authenticated message. No parser result permits dispatch: authentic current
peer/lifetime evidence, receiving generation, current policy/scope, replay state,
fences, relevant revisions and validity must be checked at the actual boundary.

This pure leaf performs no socket, process, filesystem, database, key, network,
authority or model operation. Unit tests establish bounded framing and strict
record rejection only. They do not establish IPC, OS containment, replay
protection, one-use permit consumption, independent observation or runtime
availability. First full-system failure scenarios remain unexecuted.

Source basis: ARCH-02 length-bounded framing and strict decoding; SPEC-06,
SPEC-21 and SPEC-36; complete original 042 API Architecture and 045 Security
Architecture. ADR-021 in the adjacent specification records this engineering
choice without claiming whole-contract approval.
