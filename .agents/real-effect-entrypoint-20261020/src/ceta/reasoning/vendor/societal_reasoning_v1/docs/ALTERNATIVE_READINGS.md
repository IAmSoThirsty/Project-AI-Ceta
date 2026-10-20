# Version 1 — Source-linked alternative reading and context comparison

## What the engine now actually executes

The existing `SocietalReasoner` implements `deliberate(DeliberationCase)` and `compare_deliberations(before, after)`. Both are offline, deterministic and advisory. They use the same canonical 2,000-record `KnowledgeGraph` and `KnowledgeRelevance` retrieval index as the earlier text assessor. The earlier 5-rule structured `analyze()` and exact-statement `assess_text()` remain operational and unchanged; there is no new execution authority or second inventory.

**This is an argument-auditing mechanism, not automatic social comprehension.** An upstream caller or optional model must propose candidate readings and the argument for each (`warrants`: attributable evidence ID, proposed pro/con relation, proposed rationale, optional typed context conditions). The core does **not** independently decide whether a rationale logically supports its reading. Every candidate and warrant is a proposal; none is a finding about a person, an established effect or an externally authenticated fact. In the output, `semantic_entailment_checked=false` and each warrant has `rationale_semantically_verified=false`.

## Algorithm — actual bounded behavior

1. Parse the JSON case strictly and check max 64 evidence records, 16 candidate readings, 32 warrants per candidate and 64 context factors. Check every evidence ID and related concept exists. Reject dangling references, unknown input fields and invalid role or origin types.
2. Preserve each source statement, its supplied origin/reference, and compute a SHA-256 of those **supplied bytes**. This detects changes for comparison; it does not authenticate the human or source.
3. Validate context using the existing reported-vs-model-proposed provenance contract. Model-proposed context cannot satisfy a declared relevance condition. Distinct reported values for the same category are conservatively held as unresolved contradictions rather than silently resolved.
4. For each hypothesis, examine its declared `support` and `challenge` warrants. A warrant is excluded if its only source is a prior `interpretation` record; deferred if required context is missing/contested; inactive when explicit contrary context is reported; active when its evidence exists and all declared conditions match reported context.
5. Report the active, inactive, excluded and deferred warrants **without** selecting a winner by number of supporting items. If both sides are active, retain both. Never treat a missing condition as evidence against a hypothesis. A proposer cannot establish personal motivation by labeling a statement `support`.
6. Retrieve relevant societal *topics* from the 2,000-entry corpus using attributed evidence, but never use a topic or any unreviewed relationship as an additional premise. Optional explicit concept IDs in the candidate are likewise contextual references only.
7. Recommend a minimal advisory response posture: surface multiple alternatives when more than one has active pro-warrants or when pro and con are both active; consider a single reading with explicit uncertainty if appropriate; otherwise withhold unsupported conclusions. Clarification is not automatically mandatory.
8. In a case comparison, report exactly which evidence records and context reports changed, and which candidate warrant states/statuses changed. Such comparison **does not establish historical causation**.

Statuses (`active_pro_warrants_not_semantic_proof`, `active_pro_and_con_warrants_not_semantic_proof`, `active_con_warrants_only`, `no_active_supporting_warrants`) describe the *presence of declared arguments on the current record*. They do not rank truthfulness, validate the proposed reasoning, or justify labeling a person. `context_facts` are reports and context conflicts can reflect incomplete descriptions, not necessarily logically inconsistent facts.

## Repeatable examples

```sh
python run.py deliberate examples/deliberation_public.json
python run.py deliberate examples/deliberation_private.json
python run.py compare-deliberations examples/deliberation_public.json examples/deliberation_private.json
PYTHONPATH=src python -m unittest discover -s tests -q
```

The examples use the **same** source reports and four deliberately distinct readings. Switching the stated channel `public_forum` → `private_chat` changes conditional warrants for the public-ridicule and private-teasing *possibilities*, while a specific technical-criticism interpretation can remain active. The unsupported claim about the poster's hidden motive is based on a prior interpretation and is excluded. An extra irrelevant day-of-week report changes the recorded contextual metadata without changing the candidate status. Repeated sources are not counted as independently confirmed.

`schemas/deliberation.schema.json` supplies the JSON structure; Python runtime validation is authoritative. The same requirement identifiers, source provenance and prior tests are preserved.

## Remaining hard problems — no inflated completion claim

- **No general semantic warrant verification:** optional digest-bound literal premises can now be checked against exact spans or a restricted subject/modal/polarity/action/object grammar. A proposer can still attach a nonsensical rationale to a genuine source phrase: the system does not know that the rationale supports the proposed *social reading*. See `BOUNDED_PREMISE_VALIDATION.md`.
- No robust automatic discovery of candidate explanations or observable social cues from arbitrary natural language, humor, imagery, gestures or cultural context.
- No validated causal reasoning, probabilistic truth inference, or independent review of the 45 knowledge relationships.
- Context dimension conflicts are conservative. Different actors/settings at different times can generate a same-category conflict that requires richer actor/time scoping.
- No verification that any source or reported observation is authentic; source digests establish content continuity, not truth.
- The public/private examples and unit cases were designed by the implementer, not a blind independent reviewer. They are not evidence of generalization or statistical performance.
- No automatic user-correction inference, continuous conversation adaptation, or enforced host application output gate. The consumer remains responsible for applying the advisory result.

**Next gate:** test the significance of premises for readings (not just textual validity), improve source-anchored actor/time context and social cue extraction, and evaluate on unseen examples without treating model guesses as facts.
