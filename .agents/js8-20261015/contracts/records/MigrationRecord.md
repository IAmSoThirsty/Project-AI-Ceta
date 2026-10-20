# MigrationRecord

**Document ID:** CONTRACT-MigrationRecord  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Conserve original source meaning and identity status. Distinguish dry-run validity from approved live activation. Record unknown material and original bytes rather than discarding unrecognized records.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `MigrationRecord`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `source_snapshot` | string |
| `source_schema` | string |
| `source_key_status` | string |
| `converter_commitment` | string |
| `destination_schema` | string |
| `mapping_ref` | string |
| `conservation_report_ref` | nullable/union |
| `unknown_material_refs` | array |
| `uncertain_operation_refs` | array |
| `new_genesis_ref` | nullable/union |
| `cutover_approval_ref` | nullable/union |
| `rollback_reference` | nullable/union |
| `status` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
