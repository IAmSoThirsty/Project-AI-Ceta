# 09.06 - Model Evaluation

## Purpose and boundary

This component belongs to [09-MODEL-RUNTIME](../README.md) and owns the coordinated behavior below. Primary construction role: [R09 Model Runtime Engineer](../../AGENT-ROLES/R09-MODEL-RUNTIME-ENGINEER/README.md). Independent verification: [R20 Independent Adversarial Verifier](../../AGENT-ROLES/R20-INDEPENDENT-ADVERSARIAL-VERIFIER/README.md).

**Required flow:** Run versioned representative fixtures; score task outcomes and boundary behavior; compare against declared qualification thresholds; retain full reproducibility metadata.

**Component invariant:** Model benchmarks are scoped measurements, not universal guarantees of truth or safety.

**Subsystem invariant:** Model output is untrusted proposed content. Local operation remains complete without a connected endpoint; fallback cannot silently transmit private data.

## Planned implementation files

| Unit and specification | Exact responsibility | Required positive observation |
| --- | --- | --- |
| [CETA-09.06.01 / model-benchmark-runner](model-benchmark-runner.file.README.md) | Execute pinned task fixtures with recorded model revision, settings, inputs, hardware, and runtime. Separate warm-up, measured runs, and statistical repetition. | Another verifier can reproduce the benchmark setup and inspect raw outcomes. |
| [CETA-09.06.02 / model-quality-evaluator](model-quality-evaluator.file.README.md) | Evaluate task-specific correctness, structured output validity, citation support, and instruction handling using explicit rubrics and reference cases. Preserve disagreement and uncertainty. | A model passes the defined task class while unsupported classes remain unqualified. |
| [CETA-09.06.03 / model-runtime-diagnostics](model-runtime-diagnostics.file.README.md) | Collect bounded runtime health, allocation, latency, error, cancellation, and process-exit data. Redact prompt content unless explicitly permitted for diagnostics. | A loading failure is explained using safe runtime evidence. |


Each linked document specifies one logical implementation file, its operations, domain records, contracts, end-to-end procedure, failure handling, agent assignments, and ten acceptance cases. Bind logical paths to the actual local application before editing. Reuse or extend compliant existing units rather than creating parallel owners.

## Domain records

| Field | Type |
| --- | --- |
| evaluation_id | text |
| fixture_revision | text |
| model_digest | digest |
| metrics | record |
| environment_ref | reference |


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
