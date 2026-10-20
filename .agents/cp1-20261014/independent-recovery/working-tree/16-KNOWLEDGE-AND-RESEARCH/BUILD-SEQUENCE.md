# 16-KNOWLEDGE-AND-RESEARCH - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md), [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md), [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md), [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md), [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [16.01 Source Ingestion](16.01-SOURCE-INGESTION/README.md) | Acquire authorized source bytes; preserve originals; classify format and trust; extract through bounded parsers; record dates and transformations; index after commit. |
| [16.02 Knowledge Extraction](16.02-KNOWLEDGE-EXTRACTION/README.md) | Parse structure; extract attributed entities and relationships; normalize identifiers without losing originals; validate against source spans; retain uncertainty and conflicts. |
| [16.03 Knowledge Indexing](16.03-KNOWLEDGE-INDEXING/README.md) | Index committed authorized source versions; preserve citation boundaries; apply access controls; retrieve lexical, semantic, and graph candidates; rebuild reproducibly. |
| [16.04 Research Reasoning](16.04-RESEARCH-REASONING/README.md) | Decompose research questions; compare sources and chronology; assess independence and support; seek disconfirming evidence; state supported findings and unresolved gaps. |
| [16.05 Research Output](16.05-RESEARCH-OUTPUT/README.md) | Build source-linked findings; validate every citation; separate observation and interpretation; preserve research state; export an inspectable report with exact evidence references. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
