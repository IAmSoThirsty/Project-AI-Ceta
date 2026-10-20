# RecoveryRecord

**Document ID:** CONTRACT-RecoveryRecord  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Capture uncertainty rather than rewriting the action as failed. Only new observation or receiver-side evidence can narrow outcome. Any compensation receives fresh authority and preserves newer user modifications.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `RecoveryRecord`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `operation_id` | string |
| `last_accepted_event_ref` | string |
| `uncertain_from` | nullable/union |
| `uncertain_until` | nullable/union |
| `observation_refs` | array |
| `conflict_resources` | array |
| `remaining_risks` | array |
| `allowed_next_operation_classes` | array |
| `new_authority_ref` | nullable/union |
| `settlement_ref` | nullable/union |
| `status` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
