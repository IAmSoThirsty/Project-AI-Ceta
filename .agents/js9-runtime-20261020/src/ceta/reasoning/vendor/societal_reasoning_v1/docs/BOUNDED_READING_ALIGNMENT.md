# Version 1 - bounded checks against the *proposed reading*

## What changed

Previously, the deliberation component verified some premises, but did not
independently check whether the **candidate reading itself** directly conflicted
with supplied source wording. A caller could present "Alex will attend" as an
active proposed warrant even when the only source said "Alex will not attend".
The new `reading_support.py` performs an independent, conservative source check
for candidate readings and preserves all source hashes and origins.

This is **not** broad semantic entailment, psychological insight, independent
factual confirmation, or verification that a source *socially justifies* a
proposed interpretation. Claims about human motives, personality, emotions,
consent and actual consequences cannot be established by this component.

## Supported source-reading comparisons

1. **Strict literal statements** in the existing tiny grammatical subset:
   `subject [will|may|might|can|could|did|does|do] [not] verb [object]`.
   The same actor, tense/modal, action, object and polarity must appear in an
   `external_record`, `user_report` or `direct_observation` record. Quoted
   text does not become the quoting speaker's assertion; previous
   `interpretation` records cannot ground a statement. Explicit definite
   polarity opposition is reported; modal possibility is not a contradiction.
   Textual matches verify **source reporting**, not real-world truth.
2. **Universal-quantifier wording** of the restricted, complete form
   `All|Every|No <noun phrase> <verb> <predicate>.` can support only the
   narrowly phrased reading
   `The supplied text makes a universal claim about <noun phrase>.`
   The check is about the *form of the supplied sentence*; the group has not
   been proven to have the claimed attributes. Neither ridicule nor author
   intent is deduced. Unquoted unconditional wording and a finite safe word
   subset are required. A hedge, hidden clause, or non-universal quantity
   defers rather than being normalized to an assertion.
3. **Work-product evaluation wording** in the restricted form
   `The|This <artifact> <fails|failed|passes|passed|contains|contained|lacks|lacked> <detail>.`
   It can support only the narrowly phrased reading
   `The supplied text evaluates the <artifact>.`
   Supported artifacts include patch, build, program, module, function, app,
   code, codebase, test, website, report, feature, commit and release. This
   does not verify that any tests ran, that a defect exists, or that a person
   is competent or incompetent.

These are three bounded checks, **not a general ontology of social categories**.
The same case may contain a group-quantified statement and a specific work
report. Both text patterns are retained; the engine does not force them into
mutually exclusive social labels.

## API and effects on deliberation

Public Python APIs (no network or model dependency):

```python
from societal_reasoning import assess_reading_sources, source_language_signals
from societal_reasoning.models import Evidence

sources = (Evidence("caption", "All AI coders are incompetent.", "quoted_material"),)
print(source_language_signals(sources))
print(assess_reading_sources(
    "The supplied text makes a universal claim about AI coders.", sources))
```

`SocietalReasoner.deliberate(...)` now emits:

- `source_language_signals`: only explicit wording patterns with evidence IDs,
  UTF-8 SHA-256 digests and origin, no assertions about group members or people.
- `candidates[].reading_source_alignment`: an independent source-reading
  comparison that **does not rely on the caller's proposed rationale**.
- `response_guidance.private_state_readings_not_established`: detected
  third-party private-state readings excluded from sole-answer guidance.
- `response_guidance.bounded_literal_readings_not_supported`: literal readings
  directly opposed by source reports or subject to conflicting source reports.
  In these narrow cases, an active *submitted* warrant cannot make the response
  guidance promote the opposed reading as a sole conclusion.
- The older `candidate.status` is preserved as the state of the **submitted
  argument**, not upgraded into a supported factual claim.

If a proposed social interpretation cannot be parsed, it is reported as
`unreviewable_social_or_open_language_reading`. This is not a finding that the
interpretation is false. Additional context is not automatically demanded.
A narrowly detected **third-party private-state assertion** (for example,
"The author secretly hates ..." or "Alex wants ...") is recorded as
`third_party_private_state_not_independently_established`; it cannot become
an exclusive conclusion just because it has a caller-proposed supporting
warrant. This is a deliberately partial linguistic guard, not detection of
all human states. Self-reports remain distinct from claims about other people.

`semantic_entailment_checked` stays `false` for all open-language social
readings, and `social_entailment_verified` is always `false` for the new
bounded source check. The engine does not assign private motives or human
traits based on lexical structure. The two thousand inventory entries remain
knowledge considerations, not corroborating evidence of any person's nature.

## Statuses

- `literal_reading_asserted_in_source_reports`
- `literal_reading_opposed_by_source_reports`
- `opposed_source_reports_for_literal_reading`
- `literal_reading_not_established_by_supplied_sources`
- `bounded_textual_generalization_matched`
- `textual_generalization_not_established`
- `bounded_work_product_evaluation_matched`
- `work_product_evaluation_not_established`
- `unreviewable_social_or_open_language_reading`
- `third_party_private_state_not_independently_established`

These are decisions about *source language*, not a person's truthfulness, a
real-world event, or the justification of a broader social classification.

## Verification and known gaps

```sh
python run.py deliberate examples/reading_source_alignment.json
python run.py deliberate examples/literal_reading_opposed.json
PYTHONPATH=src python -m unittest tests.test_reading_support -v
PYTHONPATH=src python -m unittest discover -s tests -q
```

The scenario cases are synthetic and authored by the implementer. Real
context-sensitive social inference, automatic general candidate generation,
independent evaluation, external source authentication, sarcasm, cultural
variation, and broad natural-language semantic entailment remain incomplete.
The original inventory remains source-transcribed and unverified against an
authenticated original export. Version designation stays **1**.
