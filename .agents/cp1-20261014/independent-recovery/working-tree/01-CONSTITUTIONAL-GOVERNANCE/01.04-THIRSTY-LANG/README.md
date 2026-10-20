# 01.04 - Thirsty Lang

## Purpose and boundary

This component belongs to [01-CONSTITUTIONAL-GOVERNANCE](../README.md) and owns the coordinated behavior below. Primary construction role: [R03 Constitutional Governance Engineer](../../AGENT-ROLES/R03-CONSTITUTIONAL-GOVERNANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Parse the locally reconciled language grammar; resolve names; type-check policy expressions; compile a bounded representation; retain source maps.

**Component invariant:** The approved local language grammar is authoritative; integration cannot silently replace it.

**Subsystem invariant:** Capability, authority, evidence, and preference remain distinct. Policy activation requires a traceable approved transition; untrusted text cannot amend governing rules.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-01.04.01 / language-parser](language-parser.file.README.md) | Implement or extend the reconciled grammar for governed policy declarations, expressions, source spans, and diagnostics. Reject ambiguous or incomplete constructs with precise locations. | An approved valid policy produces a stable syntax tree with complete source spans. |
| [CETA-01.04.02 / policy-type-checker](policy-type-checker.file.README.md) | Enforce principal, capability, resource, time, and effect types. Prevent implicit conversion of narrative text or model output into an authority-bearing value. | A well-typed scope comparison resolves against the expected resource type. |
| [CETA-01.04.03 / governed-rule-compiler](governed-rule-compiler.file.README.md) | Compile validated policies into a bounded, versioned intermediate representation with source maps and reproducible digests. Require semantic equivalence tests against the evaluator. | Compiled and interpreted forms agree on the same permitted and denied fixtures. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| source_span | range |
| syntax_node | record |
| value_type | enum |
| capability_type | record |
| compiled_digest | digest |


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
