# Common contract rules

## Scope and interpretation

This package specifies native CETA contracts. It does not choose a new implementation language, storage engine, cryptographic library, operating-system backend, or external service. The local reconciliation record pins those choices from the actual application and records any approved change. Every contract's exact data and behavior is implemented in those existing conventions; no field is left semantically undefined merely because the language binding is deferred.

## Common operation envelope

Every cross-boundary request carries a stable request identity, schema identity and revision, correlation identity, caller principal or explicitly public read context, task or lifecycle context, creation time, deadline where applicable, and exact payload digest when the request can authorize effects. Privileged requests additionally carry authenticated session and process binding, expected state or target revision, and a capability or approved service-authority reference. Responses preserve request correlation, outcome class, output references, source generation, and safe error details. A reference is an identity plus an exact revision or content digest, not merely a mutable display name or path.

## Types and bounds

Text is valid Unicode with explicit maximum byte and character lengths chosen in the qualified local profile. Identifiers use a canonical immutable representation; display names are separate. Preserve exact source bytes and user wording rather than normalizing them destructively. Lists and records have maximum item count, nesting depth, and total serialized size. Integers have explicit bounds and overflow behavior. Optional values have a defined absence condition; missing is distinct from zero, empty, false, unknown, and not-applicable. Unknown enum values cannot fall through to success. Resource identities distinguish canonical path, actual file or process identity, device or volume, target revision, and approved scope as appropriate.

## Time and ordering

Store absolute event instants unambiguously, preserve the originating timezone where needed, and keep event, publication, ingestion, observation, and commit times distinct. Use monotonic elapsed time for process-local deadlines where supported. After restart, reconcile wall-clock uncertainty conservatively; clock rollback cannot extend a previously expired grant. Durable generations and sequences establish ordering where clocks cannot. Calendar schedules explicitly define daylight-change, missed-run, and overlap rules.

## Content binding and cryptographic profiles

A digest record includes algorithm identity, encoding or canonicalization revision, exact content length, and digest bytes in an unambiguous representation. Preserve raw source bytes separately from normalized semantic records. The local integration profile selects one existing qualified canonical serialization: deterministic field ordering, exact numeric representation, explicit null treatment, bounded nesting, and collision-free framing are required. Signed records include a domain separator, schema revision, payload digest, signer key identity, and trust context. Use established cryptographic implementations; never design a new primitive. Changing the canonicalization or algorithm profile invalidates affected signatures and requires migration and conformance fixtures. A valid digest or signature proves the declared binding and trust relationship, not factual truth, complete observation, or successful execution.

## Authority and exact effects

A capability binds principal, audience, exact proposal and input digests, resource and effect scope, tool revision, lifetime, usage count, ancestry, policy generation, and current revocation context. Validate at admission and again at the relevant use-time boundary. Normalize and bind actual target identities to prevent path aliases, process reuse, redirects, and concurrent changes from altering the approved effect. If the exact operation changes, require renewed evaluation. Workers cannot create authority by editing manifests, prompts, profiles, memory, or renderer state.

## State, retries, and external effects

Canonical record owners use expected-version updates and a qualified durable transaction boundary. Persist operation intent before dispatch and durable publication intent with local commits. Delivery may repeat; consumers deduplicate by stable operation identity. Do not claim exactly-once external effects unless a qualified target-side idempotency or reconciliation mechanism establishes that property. A timeout after possible dispatch is uncertain. Inspect the actual target or authoritative receipt before retrying. Compensation is a separately authorized action that may fail or be impossible. Recovery preserves later known revocations, deletion markers, user corrections, and unresolved effects.

## Privacy and provenance

Access-filter sources before retrieval or context assembly. Keep secrets in protected handles and inject only into approved destinations; exclude them from model context, diagnostics, notifications, and ordinary exports. Store exact source references, transformation identity, and uncertainty for derived content. Deletion and correction propagate through indexes, summaries, caches, and future restores according to explicit retention and backup policy. A redacted export identifies omissions and does not claim to be a complete unredacted record.

## Outcome and error semantics

Use complete, partial, failed, cancelled, and uncertain for operation outcomes. Use proposed, admitted, running, paused, awaiting-decision, cancelling, uncertain, failed, and verified-complete for task lifecycle where applicable; components may refine states only with explicit transition mappings. Verification uses passed, failed, blocked, skipped, not-executed, and uncertain. A successful transport response is not task completion. A generated artifact is not a tested artifact. A passed structural check is not installed-runtime qualification. Error records carry safe text, stable code, effect certainty, retry class, and access-controlled diagnostic references.

## Build-time and runtime dependencies

Shared contracts are approved before their implementations. The construction graph identifies prerequisites for usable interfaces; runtime services may communicate bidirectionally through those interfaces. Bootstrap storage, protected trust operations, and evidence recording use narrowly scoped service authority and do not recursively request worker capabilities for their own internal bookkeeping. General worker effects always enter the execution gate. See the architecture bootstrap document for exact startup restrictions.
