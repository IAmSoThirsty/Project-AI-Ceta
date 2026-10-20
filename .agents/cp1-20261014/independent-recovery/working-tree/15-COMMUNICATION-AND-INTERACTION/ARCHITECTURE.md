# 15-COMMUNICATION-AND-INTERACTION - architecture

## Responsibility

Provide native conversation, voice, media, attachments, optional communication channels, notifications, and explicit human decisions.

## Required invariant

Incoming messages and media are untrusted content. Outgoing communication requires scoped destination and content authority; interface delivery does not imply human approval.

## Internal composition

| Component | Record model | Required flow |
| --- | --- | --- |
| [15.01 Conversation](15.01-CONVERSATION/README.md) | conversation_id:text; message_id:text; sequence:integer; content_ref:reference; delivery_state:enum | Accept exact messages and drafts; preserve order and identity; stream assistant responses; reconcile delivery and storage; render history with provenance. |
| [15.02 Voice](15.02-VOICE/README.md) | voice_session:text; audio_scope:reference; transcript_ref:reference; confidence:bounded-number; playback_state:enum | Obtain microphone permission; capture bounded audio; transcribe with uncertainty; confirm consequential ambiguity; synthesize approved output; support interruption and cleanup. |
| [15.03 Channels](15.03-CHANNELS/README.md) | channel_id:text; endpoint_identity:record; sender_binding:reference; message_digest:digest; delivery_receipt:reference | Configure an optional channel; verify endpoint and sender identity; normalize incoming data; authorize outgoing content and recipient; record delivery uncertainty accurately. |
| [15.04 Attachments](15.04-ATTACHMENTS/README.md) | attachment_id:text; content_digest:digest; media_type:text; byte_count:integer; access_scope:reference; scan_result:enum | Stage bytes; validate type and size; inspect unsafe structures; store under scoped ownership; create source references; ingest only through qualified parsers. |
| [15.05 Human Intervention](15.05-HUMAN-INTERVENTION/README.md) | decision_id:text; proposal_digest:digest; approver_scope:reference; response:enum; expires_at:timestamp | Present the exact decision and consequences; authenticate the responding human; bind the response to the proposal revision; expire stale prompts; resume only authorized work. |
| [15.06 Multimodal Interaction](15.06-MULTIMODAL-INTERACTION/README.md) | media_id:text; modality:enum; source_frame:reference; extraction_ref:reference; temporal_alignment:record | Validate image or media input; extract authorized observations; preserve spatial and temporal source references; combine with dialogue context; expose uncertainty. |


## Ownership and boundaries

The subsystem owns its declared domain logic, not the authority, state, evidence, or resource services of another subsystem. Canonical shared schemas have one owner. Derived views and caches are explicitly rebuildable and invalidated by source generation. Effectful workers pass through the execution gate; narrowly scoped internal service operations follow the bootstrap trust model. Model output and imported content remain untrusted data.

## Activation and shutdown

Compile and validate shared contracts before implementation. Activate required native services only after their dependencies are healthy and qualified. Expose readiness separately from configuration. On shutdown, close new admission, stop or reconcile work, persist unresolved outcomes, and release resources after ownership-aware cleanup. Read-only inspection may remain available in a restricted maintenance state where safe.

## Design decisions that require local evidence

Map the logical units to the existing language, process model, storage schema, native enforcement backend, and application composition points. Preserve existing compliant behavior and tests. Any changed owner, contract semantics, data migration, or platform restriction needs an explicit integration decision with affected consumers and acceptance evidence. The design does not replace the owner's constitutional text or invent a local repository layout.

## Required integration proof

Exercise the component flows above with actual producer-consumer interfaces, exact input and output references, failure cases, current authority, and observed effects. Keep deterministic transformations separate from model-assisted assessments and external observations. The architecture is accepted only when implemented behavior satisfies the linked file specifications and subsystem invariant.
