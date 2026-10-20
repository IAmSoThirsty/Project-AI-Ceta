# Strict records and semantic validation

schemas/records.schema.json contains 20 proposed strict wire-record shapes with bounded fields and explicit absence. records/ explains their meanings and required cross-boundary verification. JSON Schema validation checks shape only. Duplicate-key rejection, original-byte commitments, current authority, IPC origin, signatures, time, read-set consistency and transition legality require actual implementation. Synthetic examples contain no valid operational authority or confidential keys.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.

FRAMING_V1.md specifies the implemented pure four-byte length-prefixed record
codec. Validate the header before the transport allocates or reads its body.
Framing and record shape do not authenticate peers or authorize dispatch; the
actual transport/session envelope and runtime gates remain unfinished.

MEMORY_LIFECYCLE_BINDING_V1.md specifies the pure memory/event scope, reference,
retention-policy and current-lifecycle binding check. Its deletion metadata
assessment preserves outstanding authority, independent outcome and residual
copy obligations; it cannot authorize access or claim global forgetting.

For this consolidation, these modules and documents must be brought into
the sole destination repository together. Source presence is not fresh
runtime qualification. Preserve the original documents and test receipts.
