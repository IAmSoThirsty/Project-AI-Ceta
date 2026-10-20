# ReviewFinding

**Document ID:** CONTRACT-ReviewFinding  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

Reviewer role is checked against actual identity and producer lineage. The kernel applies findings under current policy. ALLOW_RECOMMENDATION is advisory and never overrides missing consent or mandatory denial.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `ReviewFinding`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `matter_ref` | string |
| `input_commitment` | string |
| `candidate_commitment` | string |
| `policy_commitment` | string |
| `reviewer_session` | string |
| `producer_sessions` | array |
| `perspective` | string |
| `outcome` | string |
| `evidence_refs` | array |
| `rationale_summary` | string |
| `dissent_refs` | array |
| `limitations` | array |
| `independence_class` | string |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
