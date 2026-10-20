# OperationPermit

**Document ID:** CONTRACT-OperationPermit  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Validate current issuance, consume state, revocation, peer identity, exact operation and resources before redemption. Consume once at the defined boundary. Never accept a caller-authored object as a valid permit merely because its JSON shape matches.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `OperationPermit`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `grant_ref` | string |
| `task_id` | string |
| `proposal_ref` | string |
| `adapter_id` | string |
| `adapter_commitment` | string |
| `operation` | string |
| `arguments_commitment` | string |
| `input_commitment` | string |
| `candidate_commitment` | nullable/union |
| `resources` | array |
| `policy_commitment` | string |
| `review_refs` | array |
| `approval_evidence_ref` | nullable/union |
| `environment_commitment` | string |
| `authority_generation` | integer |
| `fence_generation` | integer |
| `nonce` | string |
| `expires_at` | string |
| `reservation_ref` | string |
| `issuance_evidence_ref` | string |
| `consume_event_ref` | nullable/union |
| `status` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
