# 20.01 - Hardware Discovery

## Purpose and boundary

This component belongs to [20-RESOURCE-MANAGEMENT](../README.md) and owns the coordinated behavior below. Primary construction role: [R17 Resource And Performance Engineer](../../AGENT-ROLES/R17-RESOURCE-AND-PERFORMANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Inspect actual available hardware and runtime limits; measure usable capacity; monitor changes; publish a versioned capability profile with uncertainty.

**Component invariant:** Total physical capacity, currently free capacity, and safely reservable capacity are different values.

**Subsystem invariant:** Resource estimates carry uncertainty and are checked against measurements. Stop, evidence, and recovery retain reserved capacity under pressure.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-20.01.01 / hardware-capability-profiler](hardware-capability-profiler.file.README.md) | Inspect processor, memory, accelerator, storage, and relevant native isolation capabilities without assuming a specific vendor or device. Record measurement method and unavailable fields. | The profile reflects the actual target device and distinguishes unknown from zero. |
| [CETA-20.01.02 / compute-availability-monitor](compute-availability-monitor.file.README.md) | Track active CPU and accelerator utilization, reservations, thermal or runtime constraints where observable, and worker ownership. Bound sampling overhead and stale measurements. | Admission uses recent available capacity and existing reservations. |
| [CETA-20.01.03 / storage-capacity-monitor](storage-capacity-monitor.file.README.md) | Monitor free space, quota, temporary staging needs, snapshot retention, and evidence reserve. Trigger safe admission closure before critical storage exhaustion. | Disk pressure preserves enough space for cancellation and recovery records. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| profile_id | text |
| cpu_capacity | record |
| memory_bytes | integer |
| accelerator_capacity | record |
| storage_bytes | integer |
| measured_at | timestamp |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[resource-budget](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md), [workload-admission](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md), [inference-request](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md), [inference-response](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-response.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S08 State Transition Engineering](../../AGENT-SKILLS/S08-STATE-TRANSITION-ENGINEERING/SKILL.md), [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md), [S17 Failure Injection And Recovery](../../AGENT-SKILLS/S17-FAILURE-INJECTION-AND-RECOVERY/SKILL.md), [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md).
