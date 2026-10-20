# ProtectedOperationRequest

**Document ID:** CONTRACT-ProtectedOperationRequest  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

This request is an object for independent verification, not proof itself. Every authorization-relevant field must be transcript-bound. Secret shares, object keys and unrestricted plaintext never reside in its ordinary serialized record.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `ProtectedOperationRequest`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `object_id` | string |
| `object_version` | string |
| `ciphertext_commitment` | string |
| `object_key_lineage_ref` | string |
| `requester_proof_ref` | string |
| `consumer_id` | string |
| `operation` | string |
| `capability_ref` | string |
| `purpose_proof_ref` | string |
| `policy_root` | string |
| `codex_root` | string |
| `traversal_proof_ref` | string |
| `interpretation_proof_ref` | string |
| `worker_measurement_ref` | string |
| `authority_manifest_ref` | string |
| `quorum_policy_ref` | string |
| `epoch` | integer |
| `revocation_state_ref` | string |
| `nonce` | string |
| `issued_at` | string |
| `expires_at` | string |
| `prior_audit_head` | string |
| `session_binding` | string |
| `permitted_output_class` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
