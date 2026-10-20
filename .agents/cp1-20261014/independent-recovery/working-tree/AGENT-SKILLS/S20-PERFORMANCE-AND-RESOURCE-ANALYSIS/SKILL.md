---
name: performance-and-resource-analysis
description: "Use when constructing or verifying CETA performance and resource analysis. Apply the approved local architecture, scoped source inputs, and evidence-based acceptance to produce reproducible performance findings and qualified resource admission limits."
---

# S20 - Performance And Resource Analysis

## Input and output

Require: Target hardware, representative workloads, explicit thresholds, resource telemetry, and baseline measurements.

Produce: Reproducible performance findings and qualified resource admission limits.

## Procedure

Read [prerequisites](PREREQUISITES.md) and [the input contract](INPUTS.md) before acting. Follow [the complete procedure](PROCEDURE.md) for the assigned local task.

1. Measure warm and cold paths.
2. Record peaks and tail latency.
3. Model context and concurrency growth.
4. Reserve control capacity.
5. Test pressure and cleanup.
6. Compare before and after with the same workload.

## Verification

The system stays within its declared envelope and stop remains responsive under load.

Use [the verification rules](VERIFICATION.md) and preserve actual source, environment, execution, and artifact evidence. Treat this specific failure as a required adverse fixture: Averages hide severe stalls or estimates are labeled as observed measurements.

## Failure and handoff

Follow [failure handling](FAILURE-HANDLING.md) when prerequisites, authority, or evidence are insufficient. Transfer results using [the handoff requirements](HANDOFF.md) and [the output contract](OUTPUTS.md). Never substitute a completion narrative for observable evidence.

These are native construction instructions. They do not grant host permissions, activate runtime skills, or authorize effects by themselves. The assigned task and existing CETA authority remain controlling.
