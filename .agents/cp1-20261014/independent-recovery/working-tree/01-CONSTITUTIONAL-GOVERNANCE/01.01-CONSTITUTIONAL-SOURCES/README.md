# 01.01 - Constitutional Sources

## Purpose and boundary

This component belongs to [01-CONSTITUTIONAL-GOVERNANCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R03 Constitutional Governance Engineer](../../AGENT-ROLES/R03-CONSTITUTIONAL-GOVERNANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Ingest authoritative rule sources; validate provenance and structure; stage a revision; obtain approval; activate atomically and retain earlier revisions.

**Component invariant:** Only explicitly designated rule sources can become governing inputs.

**Subsystem invariant:** Capability, authority, evidence, and preference remain distinct. Policy activation requires a traceable approved transition; untrusted text cannot amend governing rules.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-01.01.01 / constitution-registry](constitution-registry.file.README.md) | Store constitutional versions with issuer, exact source digest, approval reference, activation interval, and supersession links. Expose immutable historical views and one atomic active-generation pointer. | A decision can recover the exact constitutional revision used at execution time. |
| [CETA-01.01.02 / constitutional-rule-catalog](constitutional-rule-catalog.file.README.md) | Index rules by stable identity, applicability, declared precedence, affected capabilities, and enforcement owner. Preserve original text alongside normalized predicates. | A rule query returns both executable meaning and its exact approved source. |
| [CETA-01.01.03 / rule-version-loader](rule-version-loader.file.README.md) | Load a complete validated revision snapshot, check all referenced rules, and swap active generations atomically. Keep the last approved snapshot available for inspection, not silent authorization after revocation. | Concurrent evaluations see either the old complete revision or the new complete revision. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| constitution_id | text |
| rule_id | text |
| rule_digest | digest |
| source_ref | reference |
| activation_generation | integer |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[policy-decision](../../INTERFACE-CONTRACTS/AUTHORITY/policy-decision.contract.md), [governance-packet](../../INTERFACE-CONTRACTS/AUTHORITY/governance-packet.contract.md), [principal-identity](../../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md), [capability-token](../../INTERFACE-CONTRACTS/AUTHORITY/capability-token.contract.md), [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S06 Constitutional Policy Implementation](../../AGENT-SKILLS/S06-CONSTITUTIONAL-POLICY-IMPLEMENTATION/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
