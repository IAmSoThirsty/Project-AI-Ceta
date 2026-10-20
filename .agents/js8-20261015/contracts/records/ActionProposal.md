# ActionProposal

**Document ID:** CONTRACT-ActionProposal  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

This is untrusted cognitive output. Resolve the adapter and typed arguments from admitted registry records, reject unsupported postconditions, and require exact action-specific approval. A proposal never authorizes its own execution.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `ActionProposal`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `task_id` | string |
| `request_ref` | string |
| `proposal_revision` | string |
| `adapter_id` | string |
| `adapter_version` | string |
| `operation` | string |
| `arguments_ref` | string |
| `arguments_commitment` | string |
| `resources` | array |
| `expected_predicate_refs` | array |
| `candidate_artifact_refs` | array |
| `dependencies` | array |
| `required_review_classes` | array |
| `requires_human_approval` | boolean |
| `budget` | object |
| `failure_plan_ref` | string |
| `compensation_plan_ref` | nullable/union |
| `context_ref` | string |
| `model_configuration_id` | nullable/union |
| `status` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
