# Strict records and semantic validation

schemas/records.schema.json contains 20 proposed strict wire-record shapes with bounded fields and explicit absence. records/ explains their meanings and required cross-boundary verification. JSON Schema validation checks shape only. Duplicate-key rejection, original-byte commitments, current authority, IPC origin, signatures, time, read-set consistency and transition legality require actual implementation. Synthetic examples contain no valid operational authority or confidential keys.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.
