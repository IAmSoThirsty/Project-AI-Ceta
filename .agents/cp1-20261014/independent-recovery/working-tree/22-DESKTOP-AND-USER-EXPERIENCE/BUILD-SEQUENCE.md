# 22-DESKTOP-AND-USER-EXPERIENCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [08-TASK-AND-WORKFLOW-ENGINE](../08-TASK-AND-WORKFLOW-ENGINE/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md), [20-RESOURCE-MANAGEMENT](../20-RESOURCE-MANAGEMENT/README.md).

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
| [22.01 Application Shell](22.01-APPLICATION-SHELL/README.md) | Launch a restricted shell; establish authenticated native communication; restore safe layout; activate routes from runtime readiness; preserve owner control during partial failures. |
| [22.02 Command Center](22.02-COMMAND-CENTER/README.md) | Query authoritative runtime summaries; show active work, health, and decisions; mark stale data; provide controlled navigation and stop actions. |
| [22.03 Agent Control](22.03-AGENT-CONTROL/README.md) | Inspect agent identity and assignments; display current grants and actions; request bounded controls; confirm native outcomes; expose reviewer and handoff history. |
| [22.04 Governance Interface](22.04-GOVERNANCE-INTERFACE/README.md) | Present exact proposals and rule traces; authenticate decisions; show delegation and revocation impact; preserve a source-linked decision history. |
| [22.05 Intelligence Interface](22.05-INTELLIGENCE-INTERFACE/README.md) | Present conversation and source attribution; inspect authorized memory; inspect exact context selection; propose corrections or deletions through governed controls. |
| [22.06 Evidence Interface](22.06-EVIDENCE-INTERFACE/README.md) | Query authorized evidence; display causal timelines and lineage; inspect raw and normalized observations; distinguish integrity, functional, and completeness verification. |
| [22.07 User Controls](22.07-USER-CONTROLS/README.md) | Load owner-scoped settings; validate proposed changes; apply through native commands; preserve accessibility and privacy; recover from invalid configuration. |
| [22.08 Owner Onboarding](22.08-OWNER-ONBOARDING/README.md) | Choose local data boundaries; establish owner identity; configure recovery; inspect hardware; qualify core local workflows; enable normal operation only after required checks. |
| [22.09 Native Maintenance](22.09-NATIVE-MAINTENANCE/README.md) | Inspect current health and data; prepare backup, restore, repair, or update proposals; show consequences; execute governed maintenance; verify outcomes and recovery points. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
