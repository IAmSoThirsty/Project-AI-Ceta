# 24.04 - Release Integrity

## Purpose and boundary

This component belongs to [24-BUILD-AND-RELEASE](../README.md) and owns the coordinated behavior below. Primary construction role: [R21 Build And Release Engineer](../../AGENT-ROLES/R21-BUILD-AND-RELEASE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Bind release artifacts to the manifest; sign through approved protected facilities where configured; verify trust and exact bytes; record provenance and distribution identity.

**Component invariant:** An unsigned artifact is labeled accurately and cannot be presented as trusted-signed without evidence.

**Subsystem invariant:** Release completion is determined by actual installed behavior and current evidence, not generated file volume, successful compilation, or a persuasive report.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-24.04.01 / release-artifact-signer](release-artifact-signer.file.README.md) | Sign exact release artifacts or manifests through authorized protected keys and declared algorithms. Preserve signing identity, timestamp context, and key-rotation references. | A signature verifies the exact distributed candidate bytes. |
| [CETA-24.04.02 / release-integrity-verifier](release-integrity-verifier.file.README.md) | Verify package hashes, signatures where required, trust chains, manifest completeness, and installation-time identity. Distinguish integrity from platform trust and functional qualification. | The installed artifact is cryptographically bound to the accepted release manifest. |
| [CETA-24.04.03 / release-provenance-recorder](release-provenance-recorder.file.README.md) | Link source baseline, build environment, dependency set, tests, package, signatures, and installed-runtime observations into an inspectable release lineage. Preserve actual local source evidence. | A release can be traced end to end to the exact tested local source. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| release_digest | digest |
| signing_key_ref | reference |
| trust_policy | reference |
| provenance_ref | reference |
| verification_state | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md), [evidence-receipt](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/evidence-receipt.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md), [state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md), [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md), [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md), [S23 Release Qualification](../../AGENT-SKILLS/S23-RELEASE-QUALIFICATION/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md), [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md).
