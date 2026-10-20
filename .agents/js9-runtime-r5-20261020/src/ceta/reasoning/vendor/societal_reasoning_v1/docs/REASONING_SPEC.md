# Version 1 reasoning specification — implemented subset

This describes **the actual executable behavior**, not the full proposed capability. The target is in `docs/IMPLEMENTATION_PLAN.md`, and requirements evidence in `docs/TRACEABILITY.json`.

## Canonical current paths

1. `SocietalReasoner.analyze(Scenario)` preserves the earlier five cue-rule classifier. Caller labels cues; the system does not independently perceive or infer those cues.
2. `SocietalReasoner.assess_text(text, ...)` captures exact Unicode input and hashes, records clause spans and provisional speech acts, identifies a possible request, discovers reviewed dictionary words and processes explicitly material senses, and preserves caller-supplied context with provenance. It now consults the 2,000-concept inventory for **lexically suggested topics**, but **does not synthesize general social interpretations** or treat retrieved topics as facts about people.
3. `SocietalReasoner.review_draft(assessment, draft, writing_as_user=False, correction_ledger=None)` performs limited surface checks for misquotation, a restricted set of unreported personal attributes/motives, possible modal and negation strengthening, new numeric attributions, and unverified first-person ghostwritten statements. It outputs `pass`, `review_needed` or `hold` with issue codes and hypothetical impact reminders. **`pass` only means the bounded surface checks did not find one of their targeted problems.** It does not mean truthfulness, social comprehension, authorization, or semantic fidelity have been proved.
4. An integration remains advisory unless its host *actually enforces* a `hold` or `review_needed` verdict; this source project cannot compel third-party hosts to comply.
5. `SocietalReasoner.deliberate(DeliberationCase)` and `.compare_deliberations(before, after)` examine **submitted** competing readings, sourced argument warrants, reported contextual conditions, and possible counterevidence. Optional SHA-256-bound literal premises now check exact spans or strictly parsed stated propositions, and the engine exposes opposed literal source reports. These checks **do not** validate whether a warrant justifies a social interpretation, independently observe social behavior, or establish a person's internal state. See `ALTERNATIVE_READINGS.md` and `BOUNDED_PREMISE_VALIDATION.md`.

## Human wording and attribution

`Utterance.capture` validates turn/speaker identifiers and retains the exact text, including Unicode and whitespace, with a SHA-256 digest. `SourceSpan.capture` indexes source characters (not normalized token positions); `verify()` detects mismatches. `record_statements()` proposes low-confidence speech acts and records observable modal, conditional, negation and quantity markers; this is not a syntactic or pragmatic parser. It does not identify emotions without the person stating them.

`derive_objective()` returns an explicitly **provisional** extraction only if a request or question marker is detected. Bare statements return `no_explicit_request_identified` instead of inventing a task.

## Knowledge relevance / graph interface

The `knowledge_considerations` output references lexically related concepts, attributable source IDs and source hashes; no model hypothesis or unresolved contradictory context report may seed those suggestions. Nearby graph links are unreviewed relationship hypotheses, never extra observations or validated inferences. Zero matches returns zero topics rather than inventing a people-category. This is a bounded first connection between the inventory and the text pathway, not general natural-language semantics. See `RELEVANCE_AND_CORRECTIONS.md`.

## Session-correction boundary

An explicitly instantiated `CorrectionLedger` records author-attributed corrections within one in-memory session, preserves superseded original statements, and can hold an exact old quote inaccurately presented as current. It requires a marked corrective turn, explicit target and source span, same speaker, and compatible session ID. The default stateless path does **not** silently interpret or apply corrections; no implicit session persistence exists. Semantic paraphrase review remains incomplete.

## Merriam-Webster meaning contract

The offline ten-term registry links to Merriam-Webster and retains original project-authored explanatory glosses. `discover_in_text()` identifies literal registered-word occurrences, recording exact offsets and referenced sense identifiers. It does *not* fetch Merriam-Webster live, and the registry has no evidenced editorial review timestamp.

When a caller explicitly marks a term as material, an unresolved multiple-sense case requests clarification. For the narrow phrase `context of this paragraph` / `context of this incident`, adjacent words can support a recorded sense without interruption. Arbitrary colloquialisms, user-defined meanings, jokes, dialect and unstated materiality are **not generally resolved**; the next increments must address them without forcing guesses.

## Context boundary

Context factors are typed reports or model hypotheses with source references. They are not facts about identity, emotions or private intentions. A context comparison identifies **which caller-reported dimensions changed**; it does not infer the effect of that change on actual human actors. A model hypothesis is excluded from observed-context change comparisons. Conflict between different reports remains unresolved in the output.

## Consequence awareness

The effect lens starts from a concrete draft verification issue (misquotation, unsupported state, commitment strengthening, etc.) and emits only `hypothetical_not_observed` impact notes. No harm or benefit is claimed as an observed outcome. No default message to the user is generated from these notes.

## Known gaps / fail conditions

- No NLP or vision integration; no reliable automatic pragmatic/social interpretation of arbitrary input.
- No general claim entailment verifier: synonyms, implicit predicates and tricky sentence structure can bypass the surface checker, and some benign wording may receive a false-positive review notice.
- No automatic understanding of indirect requests, sarcasm, speaker switching inside prose or anaphora.
- Explicit session corrections exist but are opt-in, limited to source supersession and exact stale-current-quote checks; no automatic semantic revision of interpretations.
- Source-text inventory has not been independently reconciled against an original authenticated transcript.
- Knowledge graph relationships are provisional, returned separately as hypotheses, and do not control `assess_text` conclusions.
- No evidence of generalization from the authored test suite.
- Alternative-reading deliberation accepts proposed arguments from the caller. Literal premise checks reject some unsupported factual links and expose direct oppositions, but cannot certify that proposed rationales justify a social interpretation. Active warrants are not validated inferences.

**Next engineering gate:** validate *inference relevance* between sources and proposed social readings beyond the narrow literal proof fragment, develop source-anchored context extraction, and independently evaluate adaptive reasoning. Broader correction semantics remain open. The first grounded retrieval and explicit correction steps are not completion of the 120-requirement target.
