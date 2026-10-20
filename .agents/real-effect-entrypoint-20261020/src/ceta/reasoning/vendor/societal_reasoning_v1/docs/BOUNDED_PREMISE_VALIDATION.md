# Version 1 - Bounded source-to-premise validation

## Scope and why it exists

The previous deliberation implementation accepted caller-authored reasons for why a
source allegedly supported a proposed social interpretation. It kept those reasons
unverified, but did not catch the simplest source contradictions. This increment
adds an **optional** premise check to each warrant and identifies opposing literal
source reports. It does NOT adjudicate social meaning, true intentions, the factual
accuracy of a source, or general English semantic entailment.

This is a useful narrow step, not completion of independent reasoning about human
complexity. The system must not classify a human by a single premise or create
claims on anyone's behalf.

## Input contracts

A `warrant` may include a `premise` whose `evidence_sha256` binds it to the
**complete exact source statement**, calculated over UTF-8. The two supported
`kind` values are:

1. `verbatim_span`: `text` plus Unicode character offsets `start` and `end`;
   verifies that the precise string occurs at those positions in the exact
   source. A quote can be present even when it is false, sarcastic, or denied.
2. `literal_assertion`: `text` must be a simple, unconditional, unquoted,
   single-sentence English clause in the restricted pattern
   `subject [will|may|might|can|could|did|does|do] [not] verb [object]`.
   It compares grammatical subject, modal, verb, object (including literal time
   references), and polarity against a single source statement parsed in the
   same restrictive fashion. No synonyms, psychological inferences, embedded
   conditions, factual interpretation, automatic pronoun resolution, or
   cross-sentence inference are permitted.

Sources tagged `quoted_material` can prove literal text presence, but cannot
be promoted to a direct speaker assertion by the second mechanism. Sources tagged
`interpretation` cannot ground either mechanism. Each successful check means
**source text presence** or **the source asserts this narrow proposition**, NOT
that the proposition is an independently verified real-world fact.

If the evidence hash changes, the premise is stale and the warrant is excluded.
If the same literal subject, action, object/time and definite modal differ only
in polarity, the checker reports source opposition. This is a textual opposition,
not proof that either person's report is false. Under `may`, `might`, `can`, and
`could`, opposite possibilities are *not* reported as contradictions.

The caller's *inference* linking a checked premise to a social reading is
**never** independently verified. The original `rationale_semantically_verified`
and `semantic_entailment_checked` flags remain `false`. Even a legitimate
literal premise may have an absurd, irrelevant or manipulative proposed rationale.

### Output states

- `source_text_matched`: exact source span is present; no claim about meaning.
- `source_asserts_literal_proposition`: same narrowly parsed statement is
  explicitly present; authenticity and real-world truth unverified.
- `source_explicitly_opposes_claim`: direct stated polarity opposition under
  `will`, `did`, `do`, or `does` with identical literal actor/action/object scope.
- `stale_source_binding`: expected whole-record digest does not match source.
- `unreviewable_attribution`: literal-assertion check requested of quotation.
- `unreviewable_source_syntax`: non-simple, hedged, quoted or conditional text.
- `modal_polarity_undetermined`: positive/negative possibilities are not
  inherently exclusive.
- `actor_scope_mismatch`, `predicate_or_scope_mismatch`, `modality_mismatch`:
  insufficient literal equivalence.
- `not_established`: the exact span at the specified offsets is absent.
- `excluded_prior_interpretation`: an interpretation cannot become observation.
- `not_requested`: backward-compatible, still unverified legacy warrant.

Failed binding and explicit polarity opposition prevent a warrant from being
counted as active. Other unsupported checks defer it. Legacy no-premise warrants
retain their old *proposal-only* active status, to avoid silently changing
existing callers; the new field `bounded_premises_verified` distinguishes them.

## Cross-source disagreement

`find_opposed_source_assertions()` examines up to 64 **simple, unquoted**
source statements. When the same literal grammatical subject, modal, action and
object/time have both positive and negative reports, the engine emits
`literal_source_oppositions`. It does not presume the same actor referent,
real-world event, time, source independence, authenticity, or motives. Related
candidates expose the conflicting report references. The response guidance
prefers presenting the unresolved records to selecting one person's account.
The caller may need more context; this is not an automatic interrogation.

## Reproduce

```sh
python run.py deliberate examples/bounded_semantic_premises.json
PYTHONPATH=src python -m unittest tests.test_semantic_support -v
PYTHONPATH=src python -m unittest discover -s tests -q
```

The synthetic example contains two opposed attendance reports, one verbatim
caption excerpt, and an excluded private-motive interpretation. Its output is
an evidentiary **proposal review**, not a social/factual verdict. No external
network or model is required. JSON Schema lives in `schemas/premise.schema.json`
and the parent case schema; Python runtime validation is authoritative.

## Known missing capabilities

- Open-domain entailment or inference from unstructured, idiomatic or sarcastic
  human communication; inference-model support and independent validation.
- Reliable identity/time resolution when different reports use the same name
  or tense; two apparent oppositions can both be true in different contexts.
- Authentication of user reports, external sources or textual quotations.
- Independent proof that evidence is relevant to a proposed social explanation.
- General cause-and-effect reasoning, automatic hypothesis generation and
  strong behavioral evaluation against unseen social cases.

**No proof, no claim:** 1,850 previously migrated entries were not changed or
independently fact-verified by this increment. The corpus remains 2,000 locally
preserved entries, not 2,000 certified empirical facts.
