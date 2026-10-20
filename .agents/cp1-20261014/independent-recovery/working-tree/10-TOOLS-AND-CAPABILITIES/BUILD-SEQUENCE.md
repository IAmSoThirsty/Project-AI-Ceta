# 10-TOOLS-AND-CAPABILITIES - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [11-EXECUTION-AND-ISOLATION](../11-EXECUTION-AND-ISOLATION/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [10.01 Tool Registry](10.01-TOOL-REGISTRY/README.md) | Register a tool manifest; verify implementation binding and qualification; expose authorized discovery; pin the exact tool revision for each invocation. |
| [10.02 Tool Contracts](10.02-TOOL-CONTRACTS/README.md) | Validate exact arguments; classify all intended effects; bind normalized input to approval; validate returned observations before consumers use them. |
| [10.03 Local Operations](10.03-LOCAL-OPERATIONS/README.md) | Resolve local targets within approved roots; validate stable identities; execute through isolated native adapters; observe actual changes; return exact results. |
| [10.04 Network Operations](10.04-NETWORK-OPERATIONS/README.md) | Validate destination and payload scope; acquire explicit network authority; enforce redirects and size limits; record requests and observed outcomes; classify timeout uncertainty. |
| [10.05 Tool Execution Results](10.05-TOOL-EXECUTION-RESULTS/README.md) | Validate invocation; obtain gate admission; dispatch once per stable operation identity; normalize observations; bind an evidence receipt; return a typed outcome. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
