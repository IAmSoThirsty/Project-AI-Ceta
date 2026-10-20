# 02.03 - Capability Tokens

## Purpose and boundary

This component belongs to [02-IDENTITY-AND-AUTHORITY](../README.md) and owns the coordinated behavior below. Primary construction role: [R04 Identity And Authority Engineer](../../AGENT-ROLES/R04-IDENTITY-AND-AUTHORITY-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Issue a capability from approved authority; bind exact scope and effect inputs; validate authenticity and current status; consume or revoke according to its usage rule.

**Component invariant:** The capability issuer cannot manufacture governance approval; it consumes validated approval references.

**Subsystem invariant:** Authority is explicit, bounded, attributable, and checked at use time. A model response or UI state is never an authentication proof.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-02.03.01 / capability-token-issuer](capability-token-issuer.file.README.md) | Issue scoped tokens bound to subject, audience, proposal digest, input digest, target identity, lifetime, usage count, and delegation ancestry. Persist issuance before returning the token. | A valid approved write produces a token usable only for the approved target and content. |
| [CETA-02.03.02 / capability-token-validator](capability-token-validator.file.README.md) | Check canonical signed content, trust chain, audience, time, ancestry, usage state, and current revocation at the dispatch boundary. Coordinate atomic single-use consumption with operation admission. | Concurrent attempts to consume a single-use token produce at most one admitted operation. |
| [CETA-02.03.03 / capability-scope-evaluator](capability-scope-evaluator.file.README.md) | Compare normalized resource identities and effect sets against allowed scope, including path aliases, link resolution, network targets, and bounded arguments. Return an explicit mismatch description. | A target resolved to the approved stable resource identity is accepted. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| capability_id | text |
| subject_id | text |
| audience | text |
| scope | record |
| effect_digest | digest |
| expires_at | timestamp |
| revocation_generation | integer |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[principal-identity](../../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md), [authenticated-session](../../INTERFACE-CONTRACTS/AUTHORITY/authenticated-session.contract.md), [capability-token](../../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md), [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md), [authority-revocation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md).

Implement declarations and conformance fixtures before effectful behavior. Use the existing composition mechanism to connect producers and consumers. The internal file list is an ownership map, not a forced call order. Pure checks remain separate from controlled effects, authoritative storage remains with its designated owner, and UI components issue authenticated native commands rather than performing privileged actions themselves.

## Failure and recovery

A malformed record is rejected before privileged work. Missing references, stale versions, invalid authority, and unsupported environment capabilities produce explicit blocked or failed results. An interruption after possible dispatch preserves uncertainty and invokes canonical reconciliation before retry. Keep source and output versions distinct, preserve user drafts and known security decisions, and do not destroy original evidence during repair.

## Construction sequence and acceptance

1. Inspect the mapped local component and record reuse, extension, or creation decisions.
2. Freeze shared contracts and acquire file ownership for the assigned builder.
3. Implement each linked unit and its explicit positive and negative fixtures.
4. Connect the component flow above through real local interfaces and test adverse transitions.
5. Inject interruption, concurrent update, cancellation, and stale-authority conditions where applicable.
6. Hand exact source, output artifacts, and test records to the independent verifier; accept only current evidence.

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
