# 21.04 - Extension Security

## Purpose and boundary

This component belongs to [21-EXTENSIONS-AND-INTEROPERABILITY](../README.md) and owns the coordinated behavior below. Primary construction role: [R18 Integration Engineer](../../AGENT-ROLES/R18-INTEGRATION-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Assign an extension principal; grant minimum capabilities; launch in qualified isolation; verify code integrity; monitor and revoke on boundary failure.

**Component invariant:** Extension identity and authority are distinct from the owner and host process.

**Subsystem invariant:** Extensions are optional untrusted components until qualified. Installation, discovery, and compatibility do not grant execution authority.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-21.04.01 / extension-authority-controller](extension-authority-controller.file.README.md) | Issue extension-scoped delegated grants for specific tools, resources, destinations, and lifetimes. Revalidate at invocation and prohibit ambient owner credentials. | An extension can use only its explicitly delegated resource scope. |
| [CETA-21.04.02 / extension-isolation-controller](extension-isolation-controller.file.README.md) | Run extension workers in qualified boundaries with bounded resources, explicit IPC, and controlled storage. Preserve separation between extensions and host state. | One extension cannot read another extension's private data or host secrets. |
| [CETA-21.04.03 / extension-integrity-verifier](extension-integrity-verifier.file.README.md) | Verify installed artifact digests, manifest binding, signatures where configured, and runtime code identity before activation and after updates. Quarantine unexpected mutations. | A modified extension binary cannot reuse its prior qualification state. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| extension_principal | reference |
| granted_scope | record |
| isolation_ref | reference |
| integrity_generation | integer |
| revocation_ref | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[skill-manifest](../../INTERFACE-CONTRACTS/AGENTS-AND-TASKS/skill-manifest.contract.md), [tool-manifest](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-manifest.contract.md), [tool-invocation](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/tool-invocation.contract.md), [isolation-context](../../INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md), [authority-delegation](../../INTERFACE-CONTRACTS/AUTHORITY/authority-delegation.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S14 Tool Execution Boundary Engineering](../../AGENT-SKILLS/S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S18 Adversarial Security Review](../../AGENT-SKILLS/S18-ADVERSARIAL-SECURITY-REVIEW/SKILL.md), [S21 Cross Subsystem Integration](../../AGENT-SKILLS/S21-CROSS-SUBSYSTEM-INTEGRATION/SKILL.md).
