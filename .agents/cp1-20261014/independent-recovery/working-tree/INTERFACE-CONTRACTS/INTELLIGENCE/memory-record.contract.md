# memory-record - canonical contract

Contract ID: `CETA-CONTRACT-memory-record`. Revision: `1.0.0`. Status: specified; implementation and runtime conformance are construction obligations.

## Ownership and routing

Canonical schema owner: [04-PERSISTENT-MEMORY](../../04-PERSISTENT-MEMORY/README.md). Consumers: [03-COMPANION-INTELLIGENCE](../../03-COMPANION-INTELLIGENCE/README.md), [05-CONTEXT-INTELLIGENCE](../../05-CONTEXT-INTELLIGENCE/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [16-KNOWLEDGE-AND-RESEARCH](../../16-KNOWLEDGE-AND-RESEARCH/README.md), [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md), [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md).

The schema owner coordinates amendments; consumers do not privately fork this contract. Read [common types, envelopes, versioning, and trust rules](../CONTRACT-COMMON-RULES.md) before implementing this contract.

## Purpose and mandatory semantics

Exact user statements, observations, inferences, and summaries remain distinct. Corrections and deletion propagate to all derived retrieval paths.

## Typed fields

| Field | Type or permitted values | Validation obligation |
| --- | --- | --- |
| memory_id | text | Required; bounded and validated before use. |
| revision | nonnegative-integer | Reject negative values unless explicitly permitted; define upper bound in the qualified local profile. |
| kind | episodic / semantic / procedural | Required; bounded and validated before use. |
| payload_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| source_refs | reference-list | Bound count and item size; preserve order when semantically meaningful; reject duplicate identities where uniqueness is required. |
| attribution | user-statement / observation / inference / derived-summary | Required; bounded and validated before use. |
| event_time | optional-timestamp | Optional only under the stated domain condition; absence is explicit and never interpreted as permission. |
| ingested_at | timestamp | Store an unambiguous instant and original timezone context where relevant; compare expiry using the declared clock policy. |
| access_scope | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| retention_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| supersedes | optional-reference | Optional only under the stated domain condition; absence is explicit and never interpreted as permission. |
| status | active / superseded / deleted / disputed | Required; bounded and validated before use. |


## Validation and lifecycle

1. Validate the common envelope, record revision, field types, length bounds, and declared enum values before semantic evaluation.
2. Resolve referenced objects through their canonical owners under the caller's permitted scope; retain the exact resolved revisions.
3. Apply the mandatory semantics above and all cross-field constraints implied by the record: actor and audience binding, parent scope containment, digest equality, chronological validity, and expected state generation where present.
4. Produce an explicit accepted, rejected, blocked, partial, or uncertain domain outcome. An unknown value or missing required observation cannot be interpreted as success.
5. For durable changes, use the owning service's expected-version transaction and publication intent; for pure checks, return a result without altering the object under review.
6. Invalidate cached decisions when any referenced content, policy, revocation, source, runtime, or state generation changes. Preserve historical records for authorized inspection.

## Failure and retry contract

Use [application-error](../USER-INTERACTION/application-error.contract.md) with a stable code and observed-effect certainty. Shape errors, unsupported revisions, invalid authority, mismatched digests, and broken references are not automatically retried. A transport interruption after possible dispatch is `reconcile-first`. Retrying a safe read or confirmed idempotent operation preserves the original operation identity and current authority checks. A new target or changed arguments require a new approved proposal.

## Compatibility and amendment

Minor additions may be optional only when old consumers retain identical authority and effect semantics. Removing fields, widening scope, changing enum meaning, altering default denial behavior, or changing signature/canonicalization semantics requires a new contract revision and affected-consumer qualification. Unknown security-relevant fields and enums are rejected; nonsemantic extension fields require an explicitly declared extension namespace and bounds. Record migration and downgrade behavior before activation.

## Conformance cases

**Valid case:** construct a complete record whose references resolve to the same accepted source and authority generation; verify both producer serialization and consumer semantics. **Domain rejection case:** An inferred preference is stored as an explicit user instruction or deleted content reappears after rebuild. **Cross-boundary case:** modify a bound digest, identity, version, or scope between production and consumption and assert rejection or renewed evaluation. **Recovery case:** restore the record with its referenced state and verify that expired authority and uncertain effects remain correctly classified.

Record the test fixture, exact serialized bytes or digest, expected outcome, actual observation, source revision, environment, and independent reviewer. The tests described here are requirements, not executed application results.

## Implementation handoff

The schema owner supplies typed declarations in the local application's established language after reconciliation. Each consumer adds actual conformance tests, including failure and uncertainty outcomes. The integration engineer verifies the real producer-consumer path; the independent verifier inspects exact artifacts and reproduces critical checks. Completion requires current evidence linked through [verification-result](../STATE-AND-EVIDENCE/verification-result.contract.md).
