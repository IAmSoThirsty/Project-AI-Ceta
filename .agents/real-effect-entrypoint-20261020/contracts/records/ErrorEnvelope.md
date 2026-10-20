# ErrorEnvelope

**Document ID:** CONTRACT-ErrorEnvelope  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Errors affect legal next actions and retain effect uncertainty. Do not convert all exceptions into safe retry. Redaction of diagnostics must preserve actionable error category without exposing hidden resources.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `ErrorEnvelope`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `operation_id` | nullable/union |
| `task_id` | nullable/union |
| `code` | string |
| `phase` | string |
| `recoverability` | string |
| `effect_status` | string |
| `retry_policy_ref` | nullable/union |
| `affected_resources` | array |
| `diagnostic_ref` | nullable/union |
| `user_explanation` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
