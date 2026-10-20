# CapabilityQualification

**Document ID:** CONTRACT-CapabilityQualification  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Record role

A verifier evaluates concrete evidence under frozen thresholds. Configuration identity and scope are essential. Qualifying one capability does not imply another; status is invalidated by relevant changes.

## Structural specification

Canonical schema: `contracts/schemas/records.schema.json`, definition `CapabilityQualification`. Every listed field is required; nullable fields explicitly represent unavailable values. Unknown fields are rejected. Arrays and strings are bounded, counters use exact safe integers, and timestamps are ISO date-time values whose semantic trust is evaluated separately.

| Field | Structural type |
| --- | --- |
| `schema_version` | constant |
| `record_id` | string |
| `scope_id` | string |
| `causation_ref` | nullable/union |
| `capability_id` | string |
| `profile_id` | string |
| `application_source` | string |
| `executable_commitment` | nullable/union |
| `configuration_commitment` | string |
| `model_configuration_id` | nullable/union |
| `os_identity` | string |
| `hardware_evidence_ref` | nullable/union |
| `adapter_commitment` | nullable/union |
| `fixture_set` | string |
| `sample_count` | integer |
| `threshold_policy_ref` | string |
| `failure_count` | integer |
| `skip_count` | integer |
| `evidence_bundle_refs` | array |
| `independence_class` | string |
| `status` | string |
| `valid_until` | nullable/union |
| `invalidation_triggers` | array |

## Validation ordering

Bound raw bytes before decoding. Reject duplicate keys, malformed UTF-8, non-finite numeric values and unsupported versions; validate shape; resolve references in the authorized scope; verify commitments, actual identities, policy and freshness; then evaluate the permitted transition. JSON Schema handles shape, not these entire semantic gates.

## Implementation work

Implement an immutable typed representation, strict decoder/encoder, canonical bytes, equality semantics, version routing, source conversion and rejection fixtures. Preserve original signed historical bytes separately. Use cryptographic domain separation and explicit commitment preimages. Do not store private reasoning traces or secrets as convenient unbounded audit strings.

## Evidence

Provide boundary-value examples, unknown-field rejection, forged/stale references and integration tests through the owning use case. The examples supplied with this package are synthetic shape fixtures only and confer no permission or qualification.
