# 17-EVIDENCE-AND-PROVENANCE - architecture

## Responsibility

Capture, seal, query, replay, and independently verify operation evidence and artifact lineage.

## Required invariant

Cryptographic integrity proves binding and tamper evidence within a stated trust model; it does not prove claim truth or complete observation. Nondeterministic inference is replayed from recorded outputs or explicitly rerun as a new experiment.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [17.01 Evidence Capture](17.01-EVIDENCE-CAPTURE/README.md) | event_id:text; operation_id:text; event_sequence:integer; source_identity:reference; artifact_refs:list | Reserve evidence capacity; capture authenticated operation events and artifacts; persist causal ordering; redact by policy; report capture gaps before final verification. |
| [17.02 Cryptographic Integrity](17.02-CRYPTOGRAPHIC-INTEGRITY/README.md) | digest_algorithm:text; canonicalization_revision:text; key_id:text; signed_payload_ref:reference; verification_state:enum | Canonicalize versioned evidence; calculate digests; sign through protected keys; verify signer trust and time context; preserve algorithm and key-rotation metadata. |
| [17.03 Provenance Graphs](17.03-PROVENANCE-GRAPHS/README.md) | node_id:text; relation_type:enum; parent_refs:list; transformation_ref:reference; graph_generation:integer | Link inputs, transformations, decisions, and outputs; index lineage; validate references and causal order; expose gaps and cycles inconsistent with the relation type. |
| [17.04 Immutable Frames](17.04-IMMUTABLE-FRAMES/README.md) | frame_id:text; sequence:integer; previous_digest:digest; member_refs:list; seal_ref:reference; anchor_ref:optional-reference | Assemble ordered evidence members; seal a canonical frame; append to protected storage; anchor where configured; verify membership, continuity, and truncation detection limits. |
| [17.05 Replay And Verification](17.05-REPLAY-AND-VERIFICATION/README.md) | replay_id:text; input_snapshot:reference; recorded_outputs:list; replay_mode:enum; verifier_identity:reference | Select a verification profile; restore recorded inputs and outputs in an isolated replay; reproduce deterministic transformations; compare observations; classify discrepancies and unknowns. |
| [17.06 Evidence Access](17.06-EVIDENCE-ACCESS/README.md) | query_id:text; principal_scope:reference; filter:record; export_manifest:reference; redaction_map:reference | Authorize evidence queries; retrieve exact records and lineage; produce scoped reports; export with integrity and redaction manifests; preserve verification semantics. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
