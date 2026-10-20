# Data contracts and ID preservation

## Concept

- `id`: stable positive integer matching the original inventory entry.
- `label`: concise source heading.
- `summary`: original entry description as represented in the manually transcribed working source; status distinguishes this from historical seed records.
- `original_text`: entire locally recorded Markdown entry line including number, bold heading, and description; required for transcribed records.
- `domains` and `aliases`: manually defined metadata for retrieval, not evidence.
- `source`: source kind, volume, ID, and (when available) original line number and title; complete Version 1 records include `source_sha256` and `entry_sha256`. Hashes protect input fidelity only, not external factual truth.
- `status`: `seed_summary_pending_transcription`, `source_transcribed`, or `independently_verified`.

These statuses are ordered for conservative merging. **A source transcription is not equivalent to external factual verification.**

## Relationship

- `source`, `target`: existing numeric concept IDs.
- `type`: one of `enables`, `depends_on`, `reinforces`, `constrains`, `contradicts`, `contextualizes`, `may_cause`, `mitigates`, `is_a`, `influences`.
- `rationale`: explicit explanation of the proposed link.
- `provenance`: source/evidence status. Initial links are hypotheses.

## Scenario

- `id` and `question` identify the evaluation.
- `context`: string-valued caller descriptions of situation, audience, and relationship; not asserted as independently verified.
- `evidence`: unique items with `id`, `statement`, `origin`, `cues`, optional `source_ref`.
- `unknowns`: unresolved information the caller or analyst identifies.
- `material_terms`: optional array of `{term, sense_id?}` declaring semantically consequential words to resolve against linked Merriam-Webster dictionary senses. The engine does not discover these automatically.

`origin` must be: `direct_observation`, `user_report`, `quoted_material`, `external_record`, or `interpretation`. Only the last type is excluded from generating support cues, while it remains inspectable in the result.

The system does not parse raw statement prose into trustworthy cues; an upstream verifier or human annotator must label them. This is a constraint, not a feature silently assumed to exist.

## Analysis result

- `status`: `provisional_interpretation`, `insufficient_evidence`, `contested_interpretations`, or `clarification_required` for declared unresolved material terms.
- `primary`: provisional selected candidate or `null`.
- `candidates`: all eligible candidates with cue/evidence source IDs and limitations.
- `epistemic_record`: separates observations, reports, quotations, records, interpretations, unknowns.
- `rule_trace`: includes rejected rules and missing prerequisites.
- `material_terms`: records resolved sense IDs, linked source references, and explicit unresolved ambiguities; a dictionary sense does not add evidentiary cues.
- `operational_boundary`: invariant `ADVISORY_ONLY_NO_EXTERNAL_ACTION_OR_AUTHORIZATION`.

## Evidence trust

A caller-provided cue is merely an annotation tied to a caller-provided report. It is **not proof** that the annotation is correct. For example, an individual's description of a meme as ridiculing users is retained as a user report. The engine can reason conditionally about that description without asserting the poster's actual motivation or the truth of the description.
