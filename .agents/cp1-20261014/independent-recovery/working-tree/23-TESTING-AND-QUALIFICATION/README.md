# 23-TESTING-AND-QUALIFICATION

## Mission

Define and execute layered tests, adversarial checks, recovery probes, usability checks, and evidence-bound product qualification.

**Invariant:** Design completeness, test existence, test execution, and passed acceptance are separate states. Critical skipped or not-executed tests cannot satisfy release gates.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [23.01 Test Architecture](23.01-TEST-ARCHITECTURE/README.md) | Register requirements and test oracles; build controlled fixtures; execute on pinned source and environment; normalize results without erasing failures or omissions. | 3 |
| [23.02 Contract Testing](23.02-CONTRACT-TESTING/README.md) | Exercise canonical schemas and semantics on producers and consumers; test valid, invalid, stale, and adversarial inputs; bind results to exact contract revisions. | 3 |
| [23.03 Integration Testing](23.03-INTEGRATION-TESTING/README.md) | Execute complete workflows across real subsystem boundaries; observe effects independently; interrupt at defined points; validate state, authority, and evidence continuity. | 3 |
| [23.04 Adversarial And Failure Tests](23.04-ADVERSARIAL-AND-FAILURE-TESTS/README.md) | Construct bounded adversarial inputs and faults in isolated fixtures; attempt declared boundary violations; observe enforcement; preserve reproducible failures and recovery evidence. | 3 |
| [23.05 Product Qualification](23.05-PRODUCT-QUALIFICATION/README.md) | Collect current results; validate source and environment binding; evaluate mandatory gates; preserve existing local acceptance obligations; approve release only with complete evidence. | 3 |
| [23.06 User Experience Testing](23.06-USER-EXPERIENCE-TESTING/README.md) | Test real owner workflows through the native interface; inspect focus and assistive behavior; measure performance under representative load; verify state and evidence outcomes. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
