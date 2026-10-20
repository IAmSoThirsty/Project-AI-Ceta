# 09.04 - Model Admission

## Purpose and boundary

This component belongs to [09-MODEL-RUNTIME](../README.md) and owns the coordinated behavior below. Primary construction role: [R09 Model Runtime Engineer](../../AGENT-ROLES/R09-MODEL-RUNTIME-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Inspect actual hardware; estimate model and context working sets; reserve headroom; run qualification probes; admit only within tested limits.

**Component invariant:** Installed artifact size is not a substitute for peak runtime memory measurement.

**Subsystem invariant:** Model output is untrusted proposed content. Local operation remains complete without a connected endpoint; fallback cannot silently transmit private data.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-09.04.01 / model-hardware-qualifier](model-hardware-qualifier.file.README.md) | Qualify loading, inference, cancellation, and recovery on the actual target hardware and runtime configuration. Record supported operating envelopes and failed limits. | A model passes load, representative inference, cancellation, and cleanup on the target device. |
| [CETA-09.04.02 / model-resource-estimator](model-resource-estimator.file.README.md) | Estimate weights, runtime buffers, context cache, concurrency, and temporary allocations using measured calibration. Return uncertainty bounds and conservative admission requirements. | Estimated peak usage contains observed qualification peaks within the declared margin. |
| [CETA-09.04.03 / model-admission-gate](model-admission-gate.file.README.md) | Acquire atomic resource reservations before loading or inference, enforce configured limits, and reject or queue excess demand. Fence stale reservations after crashes. | Two simultaneous admissions cannot both reserve the same remaining capacity. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| hardware_profile | reference |
| peak_memory_estimate | integer |
| reserve | integer |
| qualification_result | enum |
| admission_lease | reference |


Resolve enum domains and shared field semantics from [the common contract rules](../../INTERFACE-CONTRACTS/CONTRACT-COMMON-RULES.md) and the canonical contracts below. Record any application-specific representation decision in the local mapping; preserve exact meaning rather than silently changing the approved behavior.

## Canonical interfaces and integration

[model-manifest](../../INTERFACE-CONTRACTS/INTELLIGENCE/model-manifest.contract.md), [inference-request](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-request.contract.md), [inference-response](../../INTERFACE-CONTRACTS/INTELLIGENCE/inference-response.contract.md), [resource-budget](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/resource-budget.contract.md), [workload-admission](../../INTERFACE-CONTRACTS/TOOLS-AND-RESOURCES/workload-admission.contract.md), [verification-result](../../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md).

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

Component completion requires every linked unit's mandatory acceptance cases plus the integrated flow and invariant. Tests are specified here, not executed by this documentation package. Required construction skills: [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md), [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md), [S13 Model Inference Qualification](../../AGENT-SKILLS/S13-MODEL-INFERENCE-QUALIFICATION/SKILL.md), [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md), [S20 Performance And Resource Analysis](../../AGENT-SKILLS/S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/SKILL.md).
