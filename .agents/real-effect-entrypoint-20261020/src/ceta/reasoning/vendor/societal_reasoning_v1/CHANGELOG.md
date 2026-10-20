# Changelog

## Version 1 — 2026-10-17 (owner-defined fixed version)

- Completed manual local source transcription of both full societal inventory volumes, 2,000 numbered entries in total.
- Compiled and loaded all 2,000 original IDs with no gaps, duplicates, or placeholder records; preserved source text, volumes, source lines, full-source SHA-256, and entry SHA-256.
- Established one default canonical source graph and preserved the earlier `starter()` API as a compatibility alias, rather than a second partial runtime path.
- Added deterministic, fail-closed source compiler, field-for-field source/derived-data checks, 2,000-entry regression tests, and release-blocking corpus verification.
- Preserved existing reasoning logic, Merriam-Webster sense registry, behavior tests, and hypothesis-labeled relationships.
- Corrected legacy ID-1909 metadata discrepancy using the full original inventory source.
- Documented manual transcription and independent textual/factual verification boundaries, plus owner-fixed Version 1.
- Did not publish to GitHub or modify CETA/Project-AI; owner has not selected a public license.

## Historical pre-Version-1 prototypes

The previous development artifacts named v0.1.0 and v0.2.0 remain preserved for lineage, but the owner has explicitly established the current project version as **1** and requested no further incremental version changes. Earlier prototype labels are historical records, not active branches or releases used by this package.

## Version 1 — Human context and attribution safeguards (development increment)

- Preserved the 2,000-entry corpus, existing classifier and API; standardized internal `__version__` to the owner-established `1`.
- Added exact speaker utterance and source span capture with SHA-256 and conservative clause/speech-act records.
- Added an advisory free-text `assess` API and CLI, with locally checked dictionary-word candidates and bounded material-sense resolution.
- Added provenance-marked supplied context and a context-difference reporter; model hypotheses remain proposals.
- Added advisory draft checks for obvious unsupported emotions/motives, misquotations, stronger commitments, changed quantities, negation and unsupported first-person ghostwriting.
- Added optional hypothetical effect notes derived only from observed draft-check findings.
- Added the owner's mission-specific planning and 120-requirement register with explicit evidence/remaining-work statuses.
- Recorded limitations in `docs/REASONING_SPEC.md`. This is a development increment, not a completed general reasoning system or a new version.

## Version 1 — Knowledge relevance and explicit corrections (development increment)

- Connected both existing reasoning entry points to canonical inventory lexical topic retrieval while retaining speaker/source hashes and reported-context origins.
- Reject model-generated context as evidence, quarantine conflicting context categories, and return no matches rather than forcing a person-category.
- Exposed one-hop **unverified** graph relationship leads without granting causal or classification authority to hypothesis edges.
- Added a deterministic inverted lexical index with resource bounds; no synonym comprehension or independent sociological verification claim.
- Added local `CorrectionLedger` with same-speaker, later-turn, explicitly marked source-span supersession, hash-linked receipts, chain follow-ups, and purge.
- Added optional draft checks for exact superseded current-user quotations, tied to a matching session and source record.
- Preserved all 2,000 original entries, earlier APIs, original reasoning rules, and previous archives. The release designation remains exactly Version 1.

## Version 1 — Further development: alternative interpretation evidence ledger

- Added validated, bounded `DeliberationCase`/`Hypothesis`/`Warrant` structures and `deliberate`/`compare_deliberations` APIs, with CLI commands and portable JSON Schema.
- Added evidence-linked pro/con hypothesis receipts, declared-context condition matching, defer-on-conflict, exclusion of prior interpretations as observations, and counterfactual case comparisons.
- Linked 2,000-entry corpus topic retrieval without promoting unreviewed topics or edges to factual claims or inferential warrants.
- Added hostile and metamorphic tests: material versus irrelevant context changes, competing readings, missing evidence, model speculation, source duplication, tampering, malformed schema, input limits, and CLI execution.
- New logic is expressly bounded: the source-to-warrant relevance is NOT semantically proven. No general NLP, motive attribution, or empirical reasoning performance is claimed. Product remains **Version 1**.

## Version 1 — continuation: source-bounded literal premise validation

- Added `WarrantPremise` and `check_premise`, with exact Unicode quote spans and strict subject/modal/polarity/action/object assertions bound to the complete source-record SHA-256. These prove source-text presence or what a supplied source asserts, **not** factual truth.
- Prevented stale, contradictory, malformed or unreviewable premise checks from being silently treated as positive supporting evidence. Existing older warrants without a declared premise remain explicitly unverified proposals.
- Detect opposed literal source reports and retain actor/event/temporal ambiguity rather than selecting a truthful party or making a claim about intent.
- Added a portable schema, synthetic CLI fixture, source-grounding documentation, adversarial regression tests and a release-gate smoke test.
- Preserved the owner-fixed Version 1 identity, complete local 2,000-record corpus, existing CLI/API contracts and all prior behavior fixtures. No general social semantic inference or independent behavioral performance is claimed.

## Version 1 - continued implementation: source-to-reading boundary

- Added source-reading alignment independent of submitted pro/con rationale: literal source reporting/opposition, cautiously parsed group-wide quantified wording, and explicitly scoped work-product evaluation wording. The latter two describe source text, **not** a person's nature or the veracity of a criticism.
- Direct literal opposition prevents a caller-supplied supporting rationale from becoming a sole-answer recommendation. A bounded third-party private-state guard prevents known ungrounded motive assertions from becoming sole-answer recommendations. Unparsed broader social interpretations remain unreviewed, not denied.
- Added hostile regression tests for edited evidence, source-origin boundaries, attribution, group-vs-artifact framing, mixed nonexclusive evidence and direct-constructor evidence-ID collisions.
- Preserved Version 1, all 2,000 entries, legacy rules, and existing API contracts. No broad natural-language entailment or verified human motive claims.
