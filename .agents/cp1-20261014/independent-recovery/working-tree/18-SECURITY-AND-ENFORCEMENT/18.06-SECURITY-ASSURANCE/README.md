# 18.06 - Security Assurance

## Purpose and boundary

This component belongs to [18-SECURITY-AND-ENFORCEMENT](../README.md) and owns the coordinated behavior below. Primary construction role: [R15 Security And Cryptography Engineer](../../AGENT-ROLES/R15-SECURITY-AND-CRYPTOGRAPHY-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Inspect dependency and trust integrity; run boundary-focused checks; assemble evidence; classify open findings; gate release according to explicit acceptance rules.

**Component invariant:** Integrity, vulnerability status, and runtime confinement are assessed separately.

**Subsystem invariant:** Risk scores support decisions but cannot grant authority. Cryptographic operations use reconciled, established implementations and explicit threat models.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-18.06.01 / dependency-integrity-checker](dependency-integrity-checker.file.README.md) | Verify local dependency manifests, provenance, pinned versions, artifact digests, executable permissions, and unexpected changes. Record unavailable external advisories without inventing current vulnerability status. | The installed dependency set matches the approved local build manifest. |
| [CETA-18.06.02 / security-audit-generator](security-audit-generator.file.README.md) | Produce scoped audits of controls, tests, incidents, trust assumptions, and unresolved findings. Cite exact artifacts and avoid claiming certification not actually obtained. | Each security claim is tied to a control and observed verification result. |
| [CETA-18.06.03 / trust-chain-validator](trust-chain-validator.file.README.md) | Validate chains linking owner authority, device bindings, keys, signed packages, capabilities, and evidence. Detect missing anchors, revoked intermediates, and wrong usage domains. | A revoked intermediate invalidates affected current authority chains. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| assessment_id | text |
| dependency_manifest | reference |
| trust_chain | reference |
| findings | list |
| verification_ref | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[principal-identity](../../INTERFACE-CONTRACTS/AUTHORITY/principal-identity.contract.md), [authority-revocation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-revocation.contract.md), [isolation-context](../../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md).
