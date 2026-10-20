# 19.05 - Migration

## Purpose and boundary

This component belongs to [19-STATE-AND-RECOVERY](../README.md) and owns the coordinated behavior below. Primary construction role: [R16 State And Recovery Engineer](../../AGENT-ROLES/R16-STATE-AND-RECOVERY-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Plan compatibility and data transformations; run preflight and backup; stage or checkpoint migration; validate transformed data; commit activation; verify rollback or forward repair.

**Component invariant:** Migration success includes preserved user data and working application behavior, not only a new schema version.

**Subsystem invariant:** Storage durability, authority validity, and external-effect certainty are independent. Recovery never silently replays uncertain effects or rolls back known revocations.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-19.05.01 / schema-migration-planner](schema-migration-planner.file.README.md) | Define version transitions, data transformations, compatibility windows, disk requirements, preflight checks, backup needs, and reversal limits. Identify authority and evidence records requiring special preservation. | A migration plan covers every affected record family and consumer. |
| [CETA-19.05.02 / migration-execution-controller](migration-execution-controller.file.README.md) | Execute migrations with durable progress, bounded transactions, interruption recovery, and validation before schema activation. Prevent simultaneous incompatible application access. | A crash mid-migration resumes or restores without exposing mixed schema semantics. |
| [CETA-19.05.03 / migration-reversal-validator](migration-reversal-validator.file.README.md) | Verify whether reversal preserves information and current security state. Test rollback against the real transformed data or define an explicit forward-repair plan for irreversible changes. | A reversible migration restores data and keeps known revocations intact. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| migration_id | text |
| from_schema | text |
| to_schema | text |
| preflight_ref | reference |
| progress_checkpoint | reference |
| reversibility | enum |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[state-transition](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/state-transition.contract.md), [persistent-checkpoint](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/persistent-checkpoint.contract.md), [uncertain-operation](../../INTERFACE-CONTRACTS/EXECUTION/uncertain-operation.contract.md), [recovery-report](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/recovery-report.contract.md), [provenance-link](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md), [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md).
