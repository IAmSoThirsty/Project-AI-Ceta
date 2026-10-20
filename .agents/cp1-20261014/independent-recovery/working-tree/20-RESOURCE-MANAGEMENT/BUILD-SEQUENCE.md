# 20-RESOURCE-MANAGEMENT - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

## Ordered work

1. Inspect the existing local implementation and classify every logical unit as reuse, extend, or create; record exact source digests.
2. Approve canonical interfaces, domain records, error semantics, and state ownership with affected producers and consumers.
3. Create positive, negative, boundary, and recovery fixtures before relying on the new behavior.
4. Implement pure validation and transformation logic first; then connect canonical state, authority, resources, evidence, and controlled effects as applicable.
5. Integrate the component flows listed below in their actual dependency order, using the existing application composition mechanism.
6. Exercise real cross-subsystem paths and concurrency, cancellation, resource, and recovery failures.
7. Update user and engineering documentation from observed behavior and preserve source-to-test-to-artifact traceability.
8. Submit exact artifacts and raw evidence to independent verification; close the subsystem gate only after all required obligations pass.

## Component integration units

| Component | Flow to construct |
| --- | --- |
| [20.01 Hardware Discovery](20.01-HARDWARE-DISCOVERY/README.md) | Inspect actual available hardware and runtime limits; measure usable capacity; monitor changes; publish a versioned capability profile with uncertainty. |
| [20.02 Resource Budgeting](20.02-RESOURCE-BUDGETING/README.md) | Define per-task and shared budgets; reserve atomically; meter actual use; throttle or stop at limits; release reservations after verified cleanup. |
| [20.03 Workload Admission](20.03-WORKLOAD-ADMISSION/README.md) | Estimate requirements; validate budgets and environment; reserve capacity; queue or admit fairly; fence expired reservations; release only after cleanup. |
| [20.04 Resource Pressure](20.04-RESOURCE-PRESSURE/README.md) | Detect sustained pressure; prioritize control and evidence; throttle optional work; stop unsafe admissions; recover gradually after measured stability. |
| [20.05 Operational Diagnostics](20.05-OPERATIONAL-DIAGNOSTICS/README.md) | Collect scoped resource telemetry; identify bottlenecks; compare against qualification envelopes; run offline and failure probes; report measured limits. |
| [20.06 Inference Accounting](20.06-INFERENCE-ACCOUNTING/README.md) | Meter observed inference usage; distinguish estimates and provider reports; charge parent and child tasks once; enforce budgets; reconcile interrupted streams. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
