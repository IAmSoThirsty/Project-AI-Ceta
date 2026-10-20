# ContextEnvelope

**Document ID:** CONTRACT-ContextEnvelope  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Bind exact prepared bytes and all relevant versions. Revalidation occurs after preview and before actual dispatch. Omitted material and unknowns stay explicit; a model-generated payload hash does not prove the compiler used the right sources.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `ContextEnvelope`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `task_id` | string |
| `objective_revision` | string |
| `principal_id` | string |
| `companion_id` | string |
| `model_configuration_id` | string |
| `policy_refs` | array |
| `authority_refs` | array |
| `snapshot_commitment` | string |
| `read_set` | array |
| `observation_refs` | array |
| `memory_refs` | array |
| `open_questions` | array |
| `contradiction_refs` | array |
| `omissions` | array |
| `template_commitment` | string |
| `tokenizer_commitment` | string |
| `payload_commitment` | string |
| `input_tokens` | integer |
| `reserved_output_tokens` | integer |
| `expires_at` | string |
| `revalidation_triggers` | array |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
