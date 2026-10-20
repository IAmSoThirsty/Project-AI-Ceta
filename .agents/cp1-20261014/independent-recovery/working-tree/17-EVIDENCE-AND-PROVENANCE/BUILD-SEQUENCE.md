# 17-EVIDENCE-AND-PROVENANCE - construction sequence

## Entry criteria

The local application has an inspected baseline, assigned source ownership, approved contract bindings, and preserved existing acceptance requirements. Required prerequisites: [00-MASTER-ARCHITECTURE](../00-MASTER-ARCHITECTURE/README.md), [18-SECURITY-AND-ENFORCEMENT](../18-SECURITY-AND-ENFORCEMENT/README.md), [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md).

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
| [17.01 Evidence Capture](17.01-EVIDENCE-CAPTURE/README.md) | Reserve evidence capacity; capture authenticated operation events and artifacts; persist causal ordering; redact by policy; report capture gaps before final verification. |
| [17.02 Cryptographic Integrity](17.02-CRYPTOGRAPHIC-INTEGRITY/README.md) | Canonicalize versioned evidence; calculate digests; sign through protected keys; verify signer trust and time context; preserve algorithm and key-rotation metadata. |
| [17.03 Provenance Graphs](17.03-PROVENANCE-GRAPHS/README.md) | Link inputs, transformations, decisions, and outputs; index lineage; validate references and causal order; expose gaps and cycles inconsistent with the relation type. |
| [17.04 Immutable Frames](17.04-IMMUTABLE-FRAMES/README.md) | Assemble ordered evidence members; seal a canonical frame; append to protected storage; anchor where configured; verify membership, continuity, and truncation detection limits. |
| [17.05 Replay And Verification](17.05-REPLAY-AND-VERIFICATION/README.md) | Select a verification profile; restore recorded inputs and outputs in an isolated replay; reproduce deterministic transformations; compare observations; classify discrepancies and unknowns. |
| [17.06 Evidence Access](17.06-EVIDENCE-ACCESS/README.md) | Authorize evidence queries; retrieve exact records and lineage; produce scoped reports; export with integrity and redaction manifests; preserve verification semantics. |


## Parallel work and exit

Parallel implementation is allowed only after shared interfaces are stable and write scopes are disjoint. A stale lease cannot publish canonical changes. A conflict returns to the owning architecture or integration role, not to a last-writer-wins merge. Exit requires [the subsystem acceptance gate](ACCEPTANCE.md) and independent review of the delivered revision.
