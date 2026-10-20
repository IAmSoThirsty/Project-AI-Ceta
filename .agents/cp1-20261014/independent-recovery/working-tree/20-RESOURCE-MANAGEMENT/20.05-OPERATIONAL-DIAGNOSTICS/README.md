# 20.05 - Operational Diagnostics

## Purpose and boundary

This component belongs to [20-RESOURCE-MANAGEMENT](../README.md) and owns the coordinated behavior below. Primary construction role: [R17 Resource And Performance Engineer](../../AGENT-ROLES/R17-RESOURCE-AND-PERFORMANCE-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Collect scoped resource telemetry; identify bottlenecks; compare against qualification envelopes; run offline and failure probes; report measured limits.

**Component invariant:** Operational reports distinguish measured behavior from inferred causes.

**Subsystem invariant:** Resource estimates carry uncertainty and are checked against measurements. Stop, evidence, and recovery retain reserved capacity under pressure.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-20.05.01 / resource-telemetry-recorder](resource-telemetry-recorder.file.README.md) | Record bounded, privacy-aware resource measurements tied to task and runtime identity. Use retention and sampling limits that do not become a resource leak. | Long sessions retain useful telemetry without unbounded memory or disk growth. |
| [CETA-20.05.02 / performance-diagnostics-engine](performance-diagnostics-engine.file.README.md) | Correlate latency, allocation, queueing, I/O, and process events to identify reproducible bottlenecks. Preserve alternative explanations until measurements distinguish them. | A performance finding includes a repeatable workload and before/after measurements. |
| [CETA-20.05.03 / offline-operation-qualifier](offline-operation-qualifier.file.README.md) | Test startup, ownership, local inference, memory, tools, task recovery, evidence, and shutdown with external connectivity unavailable. Verify optional network features fail explicitly without blocking core local use. | The qualified local workflow completes without external network access. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| sample_id | text |
| task_ref | reference |
| measured_resources | record |
| environment_revision | text |
| diagnostic_ref | reference |


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
