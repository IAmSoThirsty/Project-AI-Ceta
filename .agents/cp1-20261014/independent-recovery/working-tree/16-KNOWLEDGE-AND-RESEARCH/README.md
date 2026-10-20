# 16-KNOWLEDGE-AND-RESEARCH

## Mission

Ingest and retrieve authorized sources, extract knowledge, compare evidence, and produce attributable research outputs.

**Invariant:** Source integrity, source credibility, claim support, and claim truth are different assessments. Contrary evidence and unknowns remain visible.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [16.01 Source Ingestion](16.01-SOURCE-INGESTION/README.md) | Acquire authorized source bytes; preserve originals; classify format and trust; extract through bounded parsers; record dates and transformations; index after commit. | 3 |
| [16.02 Knowledge Extraction](16.02-KNOWLEDGE-EXTRACTION/README.md) | Parse structure; extract attributed entities and relationships; normalize identifiers without losing originals; validate against source spans; retain uncertainty and conflicts. | 3 |
| [16.03 Knowledge Indexing](16.03-KNOWLEDGE-INDEXING/README.md) | Index committed authorized source versions; preserve citation boundaries; apply access controls; retrieve lexical, semantic, and graph candidates; rebuild reproducibly. | 3 |
| [16.04 Research Reasoning](16.04-RESEARCH-REASONING/README.md) | Decompose research questions; compare sources and chronology; assess independence and support; seek disconfirming evidence; state supported findings and unresolved gaps. | 3 |
| [16.05 Research Output](16.05-RESEARCH-OUTPUT/README.md) | Build source-linked findings; validate every citation; separate observation and interpretation; preserve research state; export an inspectable report with exact evidence references. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
