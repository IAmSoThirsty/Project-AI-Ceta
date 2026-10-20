# 17-EVIDENCE-AND-PROVENANCE

## Mission

Capture, seal, query, replay, and independently verify operation evidence and artifact lineage.

**Invariant:** Cryptographic integrity proves binding and tamper evidence within a stated trust model; it does not prove claim truth or complete observation. Nondeterministic inference is replayed from recorded outputs or explicitly rerun as a new experiment.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [17.01 Evidence Capture](17.01-EVIDENCE-CAPTURE/README.md) | Reserve evidence capacity; capture authenticated operation events and artifacts; persist causal ordering; redact by policy; report capture gaps before final verification. | 3 |
| [17.02 Cryptographic Integrity](17.02-CRYPTOGRAPHIC-INTEGRITY/README.md) | Canonicalize versioned evidence; calculate digests; sign through protected keys; verify signer trust and time context; preserve algorithm and key-rotation metadata. | 3 |
| [17.03 Provenance Graphs](17.03-PROVENANCE-GRAPHS/README.md) | Link inputs, transformations, decisions, and outputs; index lineage; validate references and causal order; expose gaps and cycles inconsistent with the relation type. | 3 |
| [17.04 Immutable Frames](17.04-IMMUTABLE-FRAMES/README.md) | Assemble ordered evidence members; seal a canonical frame; append to protected storage; anchor where configured; verify membership, continuity, and truncation detection limits. | 3 |
| [17.05 Replay And Verification](17.05-REPLAY-AND-VERIFICATION/README.md) | Select a verification profile; restore recorded inputs and outputs in an isolated replay; reproduce deterministic transformations; compare observations; classify discrepancies and unknowns. | 3 |
| [17.06 Evidence Access](17.06-EVIDENCE-ACCESS/README.md) | Authorize evidence queries; retrieve exact records and lineage; produce scoped reports; export with integrity and redaction manifests; preserve verification semantics. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 6 component folders and 18 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
