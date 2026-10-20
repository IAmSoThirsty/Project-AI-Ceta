# 23-TESTING-AND-QUALIFICATION - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [23.01 Test Architecture](23.01-TEST-ARCHITECTURE/README.md) | Register requirements and test oracles; build controlled fixtures; execute on pinned source and environment; normalize results without erasing failures or omissions. |
| [23.02 Contract Testing](23.02-CONTRACT-TESTING/README.md) | Exercise canonical schemas and semantics on producers and consumers; test valid, invalid, stale, and adversarial inputs; bind results to exact contract revisions. |
| [23.03 Integration Testing](23.03-INTEGRATION-TESTING/README.md) | Execute complete workflows across real subsystem boundaries; observe effects independently; interrupt at defined points; validate state, authority, and evidence continuity. |
| [23.04 Adversarial And Failure Tests](23.04-ADVERSARIAL-AND-FAILURE-TESTS/README.md) | Construct bounded adversarial inputs and faults in isolated fixtures; attempt declared boundary violations; observe enforcement; preserve reproducible failures and recovery evidence. |
| [23.05 Product Qualification](23.05-PRODUCT-QUALIFICATION/README.md) | Collect current results; validate source and environment binding; evaluate mandatory gates; preserve existing local acceptance obligations; approve release only with complete evidence. |
| [23.06 User Experience Testing](23.06-USER-EXPERIENCE-TESTING/README.md) | Test real owner workflows through the native interface; inspect focus and assistive behavior; measure performance under representative load; verify state and evidence outcomes. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
