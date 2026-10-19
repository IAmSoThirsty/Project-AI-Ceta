"""Bounded attribution guard for proposed answers; never claim complete NLP proof.

A passing surface review is NOT a general guarantee of semantic correctness.
Unverifiable first-person ghostwritten claims are explicitly held for review.
"""

from __future__ import annotations

import re
from typing import Any

from .input_boundary import Utterance

# Deliberately narrow enough not to classify ordinary expressions of empathy.
_PRIVATE = re.compile(
    r"\b(?P<actor>you|he|she|they|the user|the speaker)(?:\s+|(?=\x27re\b|\x27s\b))"
    r"(?:(?:are|is|were|was|\x27re|\x27s|seem|seems|sound|sounds)\s*(?P<label>angry|upset|afraid|scared|depressed|jealous|ashamed|lonely|hurt|happy|sad|furious|anxious)\b"
    r"|(?:feel|feels|felt)\s+(?P<feeling>angry|upset|afraid|scared|depressed|jealous|ashamed|lonely|hurt|happy|sad|furious|anxious)\b"
    r"|(?P<motive>intend|intends|believe|believes|want|wants)\b)",
    re.IGNORECASE,
)
_QUOTED_ATTRIBUTION = re.compile(
    r"\b(?:you (?:said|stated|wrote)|your (?:words|statement) (?:were|was))\s*[:,-]?\s*[\"“]([^\"”]+)[\"”]",
    re.IGNORECASE,
)
_FIRST_PERSON_FACT = re.compile(r"(?m)(?:^|[.!?]\s+)I\s+(?:am|was|have|had|will|might|may|could|did|do|don't|didn't|work|worked|spent|believe|want|intend)\b[^.!?]*", re.IGNORECASE)
_WORD = re.compile(r"\b[\w']+\b")
_MAYBE = frozenset({"may", "might", "could", "possibly", "perhaps", "maybe"})
_NEGATIVE = frozenset({"not", "never", "no", "cannot", "can't", "won't", "don't", "didn't", "doesn't"})
_MODAL_STRONG = re.compile(r"\b(?:you|i)\s+(?:will|am|are|did|do|have|had|must)\s+\w+", re.IGNORECASE)


def _words(value: str) -> set[str]:
    return set(w.group().casefold() for w in _WORD.finditer(value))


def _self_reported(user_text: str, label: str) -> bool:
    return bool(re.search(r"\b(?:I\s+(?:am|was|feel|felt)\s+|I\x27m\s+)(?:\w+\s+){0,2}" + re.escape(label) + r"\b", user_text, re.I))


def review_draft(source: Utterance, draft: str, *, writing_as_user: bool = False) -> dict[str, Any]:
    if not isinstance(draft, str) or not draft.strip() or len(draft) > 65536:
        raise ValueError("Review requires nonempty draft of at most 65536 characters")
    if not isinstance(writing_as_user, bool):
        raise ValueError("writing_as_user must be bool")
    problems: list[dict[str, Any]] = []

    def add(code: str, snippet: str, detail: str, decision: str) -> None:
        if not any(item["code"] == code and item["span"] == snippet for item in problems):
            problems.append({"code": code, "span": snippet, "reason": detail, "severity": decision})

    for item in _QUOTED_ATTRIBUTION.finditer(draft):
        if item.group(1) not in source.text:
            add("MISQUOTED_USER", item.group(), "Quoted wording is not an exact substring of the source utterance", "hold")
    for item in _PRIVATE.finditer(draft):
        label = item.group("label") or item.group("feeling")
        actor = item.group("actor").casefold()
        if label and actor in {"you", "the user", "the speaker"} and _self_reported(source.text, label):
            continue
        # Third-party claims require third-party evidence, not merely user's words.
        add("UNSUPPORTED_PERSON_STATE", item.group(), "No directly established basis for this person's asserted internal state", "hold")
    if writing_as_user:
        for match in _FIRST_PERSON_FACT.finditer(draft):
            exact = match.group().lstrip(".?! ")
            if exact not in source.text:
                add("UNVERIFIED_FIRST_PERSON_DRAFT", exact,
                    "New first-person claim is not a verbatim supported user statement; requires source mapping or review", "review_needed")
    else:
        # First-person speech in a response is not automatically the user's claim.
        pass

    # Check a particularly dangerous *lexical* commitment change without pretending
    # to establish semantic equivalence across arbitrary paraphrases.
    source_words, draft_words = _words(source.text), _words(draft)
    if (source_words & _MAYBE) and _MODAL_STRONG.search(draft):
        # Flag only where candidate and source share meaningful predicate tokens.
        overlaps = (source_words & draft_words) - {"i", "you", "am", "are", "will", "might", "may", "could", "have", "had", "do", "did", "the", "a", "to"}
        if overlaps and len(overlaps) >= 1:
            add("POSSIBLE_MODALITY_STRENGTHENING", _MODAL_STRONG.search(draft).group(),
                "Source contains uncertainty marker; candidate asserts a stronger commitment using overlapping language", "review_needed")
    if source_words & _NEGATIVE:
        # Explicit-source negation + positive second-person report; may have changed polarity.
        affirmative = re.search(r"\byou\s+(?:do|did|are|were|have|had)\s+(?!not\b|never\b|n't\b)\w+", draft, re.I)
        if affirmative and not draft_words & _NEGATIVE:
            add("POSSIBLE_NEGATION_LOSS", affirmative.group(),
                "Source contains negation and candidate may have changed its polarity", "review_needed")
    # In user-addressed numeric claims, require numeric values to have appeared in source.
    for match in re.finditer(r"\byou\s+[^.!?\n]{0,90}?\b(\d+(?:[,.]\d+)*)\b", draft, re.I):
        if match.group(1) not in source.text:
            add("UNSUPPORTED_USER_QUANTITY", match.group(), "User-attributed quantity is not present in original source", "hold")

    status = "hold" if any(p["severity"] == "hold" for p in problems) else (
        "review_needed" if problems else "pass"
    )
    return {
        "version": "1", "status": status, "issues": problems,
        "source_turn": source.turn_id, "source_sha256": source.sha256,
        "writing_as_user": writing_as_user,
        "review_scope": "bounded_surface_attribution_checks_not_complete_semantic_verification",
        "enforcement": "advisory_result_host_must_obey_to_block_or_revise",
    }
