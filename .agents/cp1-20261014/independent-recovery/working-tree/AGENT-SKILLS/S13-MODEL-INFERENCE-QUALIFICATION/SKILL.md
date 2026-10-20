---
name: model-inference-qualification
description: "Use when constructing or verifying CETA model inference qualification. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce a measured capability and resource envelope with inference, streaming, cancellation, and cleanup evidence."
---

# S13 - Model Inference Qualification

## Input and output

Require: Exact model artifact, runtime configuration, target hardware, task fixtures, and locality policy.

Produce: A measured capability and resource envelope with inference, streaming, cancellation, and cleanup evidence.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Validate artifacts.
2. Measure peak allocations.
3. Test supported modalities and context limits.
4. Run representative and adverse inputs.
5. Verify cancellation and process ownership.
6. Qualify fallback only within approved data boundaries.

## Verification

The selected model completes the declared task classes within measured limits and stops safely.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: Advertised capability or artifact size is treated as measured runtime qualification.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.
