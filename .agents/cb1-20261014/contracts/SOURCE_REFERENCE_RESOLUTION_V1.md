# Working Codex handoff-schema reference resolution

The v1 resolver accepts only the exact receipt-bound mapping bytes with SHA-256
`7311708cdd0a8e32a7ddb648e214be6bc91fe3ccd4c770331c727b3484523e99`.
This binds each witness number to its actual guide path and source digest; a
permutation of valid witness numbers rejects. Changing the engineering map
requires an explicit new reviewed commitment rather than caller substitution.

Finding 2 remediation. Parent obligations: REQ-01-01/02/04, REQ-04-02,
REQ-06-03, REQ-36-01/02 and REQ-40-03. The twenty-one original expected-output
guides retain their exact bytes and broken `../schemas/handoff_record.md` link.
The missing outer location and original author's intended location remain
historical facts; this mapping does not rewrite either.

`source_reference_map_v1.json` explicitly maps each exact guide identity and
original reference to `reference_material/handoff_record.source.md`, an exact
493-byte copy of the authentic nested canonical schema. Carrier/archive/member
paths, byte domains and commitments are recorded in that mapping and the adjacent
specification evidence. SHA-256 is
`036909b7fec542b60ecc7bb5c472bf7779ed612b8f869dbd60c02b759de84fda`.

`src/ceta/contracts/source_references.py` resolves supplied original guide bytes
through the working map and verifies the schema bytes. It opens no arbitrary
paths and issues no authority. The map is engineering reference data whose own
identity must remain bound to the execution receipt; it is not a trusted source
issuer, a permit, a handoff-record decoder or a source-ratification decision.

Deterministic tests read all twenty-one actual originals, resolve the authentic
schema, verify originals remain unchanged, and reject changed guides/material,
unmapped paths and duplicate/missing/wrong witness maps. They qualify this
reference mechanism only. Gate A and runtime acceptance remain open.
