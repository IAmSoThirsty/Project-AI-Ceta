# evidence-receipt - canonical contract

Contract ID: `CETA-CONTRACT-evidence-receipt`. Revision: `1.0.0`. Status: specified; implementation and runtime conformance are construction obligations.

## Ownership and routing

Canonical schema owner: [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md). Consumers: [00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md), [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md), [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md), [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md), [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md), [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md), [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md), [12-ENGINEERING-INTELLIGENCE](../../12-ENGINEERING-INTELLIGENCE/README.md), [14-AUTOMATION-AND-SCHEDULING](../../14-AUTOMATION-AND-SCHEDULING/README.md), [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md), [21-EXTENSIONS-AND-INTEROPERABILITY](../../21-EXTENSIONS-AND-INTEROPERABILITY/README.md), [23-TESTING-AND-QUALIFICATION](../../23-TESTING-AND-QUALIFICATION/README.md), [24-BUILD-AND-RELEASE](../../24-BUILD-AND-RELEASE/README.md).

The schema owner coordinates amendments; consumers do not privately fork this contract. Read [common types, envelopes, versioning, and trust rules](../CONTRACT-COMMON-RULES.md) before implementing this contract.

## Purpose and mandatory semantics

Receipts bind exact operation evidence within a declared trust model. Integrity, attribution, observation completeness, and functional success remain separate checks.

## Typed fields

| Field | Type or permitted values | Validation obligation |
| --- | --- | --- |
| receipt_id | text | Required; bounded and validated before use. |
| operation_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| input_digest | digest | Bind exact content using the active declared digest and canonicalization profile; include algorithm identity. |
| authority_decision_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| implementation_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| target_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| observation_refs | reference-list | Bound count and item size; preserve order when semantically meaningful; reject duplicate identities where uniqueness is required. |
| outcome | enum-declared | Required; bounded and validated before use. |
| artifact_digests | digest-list | Bind exact content using the active declared digest and canonicalization profile; include algorithm identity. |
| sequence | nonnegative-integer | Reject negative values unless explicitly permitted; define upper bound in the qualified local profile. |
| previous_digest | optional-digest | Optional only under the stated domain condition; absence is explicit and never interpreted as permission. |
| key_id | text | Required; bounded and validated before use. |
| signature_ref | reference | Resolve an authorized exact identity and revision; reject missing, wrong-domain, or stale bindings. |
| canonicalization_revision | text | Required; bounded and validated before use. |


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

**Valid case:** construct a complete record whose references resolve to the same accepted source and authority generation; verify both producer serialization and consumer semantics. **Domain rejection case:** An authentic receipt for a different operation or stale source revision is attached to the current claim. **Cross-boundary case:** modify a bound digest, identity, version, or scope between production and consumption and assert rejection or renewed evaluation. **Recovery case:** restore the record with its referenced state and verify that expired authority and uncertain effects remain correctly classified.

Record the test fixture, exact serialized bytes or digest, expected outcome, actual observation, source revision, environment, and independent reviewer. The tests described here are requirements, not executed application results.

## Implementation handoff

The schema owner supplies typed declarations in the local application's established language after reconciliation. Each consumer adds actual conformance tests, including failure and uncertainty outcomes. The integration engineer verifies the real producer-consumer path; the independent verifier inspects exact artifacts and reproduces critical checks. Completion requires current evidence linked through [verification-result](verification-result.contract.md).
