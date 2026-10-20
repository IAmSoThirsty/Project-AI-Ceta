# 16-KNOWLEDGE-AND-RESEARCH - dependencies

## Construction prerequisites

| Required subsystem | Why it must be available |
| --- | --- |
| [02-IDENTITY-AND-AUTHORITY](../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) | Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability. |
| [09-MODEL-RUNTIME](../09-MODEL-RUNTIME/README.md) | Manage native model artifacts, qualified inference, optional owner-configured endpoints, routing, lifecycle, and controlled customization. |
| [10-TOOLS-AND-CAPABILITIES](../10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. |
| [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. |
| [19-STATE-AND-RECOVERY](../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |


## Shared contracts

| Contract | Canonical owner |
| --- | --- |
| [knowledge-source](../INTERFACE-CONTRACTS/INTELLIGENCE/knowledge-source.contract.md) | [16-KNOWLEDGE-AND-RESEARCH](README.md) |
| [research-claim](../INTERFACE-CONTRACTS/INTELLIGENCE/research-claim.contract.md) | [16-KNOWLEDGE-AND-RESEARCH](README.md) |
| [memory-record](../INTERFACE-CONTRACTS/INTELLIGENCE/memory-record.contract.md) | [04-PERSISTENT-MEMORY](../04-PERSISTENT-MEMORY/README.md) |
| [provenance-link](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/provenance-link.contract.md) | [17-EVIDENCE-AND-PROVENANCE](../17-EVIDENCE-AND-PROVENANCE/README.md) |
| [context-snapshot](../INTERFACE-CONTRACTS/INTELLIGENCE/context-snapshot.contract.md) | [05-CONTEXT-INTELLIGENCE](../05-CONTEXT-INTELLIGENCE/README.md) |
| [verification-result](../INTERFACE-CONTRACTS/STATE-AND-EVIDENCE/verification-result.contract.md) | [23-TESTING-AND-QUALIFICATION](../23-TESTING-AND-QUALIFICATION/README.md) |


## Dependency semantics

The build graph represents usable interface prerequisites, not an assertion that every downstream user-facing feature is already complete. Shared contract declarations and test fixtures are established first. Runtime communication can be bidirectional through approved ports without creating a build cycle. Optional connected channels, endpoints, and extensions never become mandatory dependencies for local core operation.

## Invalidation and failure

A changed contract revision, source digest, authority generation, model or tool implementation, resource qualification, or state schema invalidates the affected cached result and acceptance evidence. Missing prerequisites block only the dependent operation where safe; mandatory enforcement failure blocks effects. Do not substitute an unqualified fallback. See [the validated construction graph](../DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) for global order and [recovery requirements](FAILURE-AND-RECOVERY.md) for interruption handling.
