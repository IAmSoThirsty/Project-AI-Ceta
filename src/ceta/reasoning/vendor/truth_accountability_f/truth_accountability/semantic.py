"""Deterministic semantic *risk indicators*, NOT proof of entailment.

Model-generated annotations are never trusted to establish someone else's meaning.
The host must require source-speaker or authorized reviewer confirmation for
non-verbatim attributions. The limited checks here target known failure modes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SpeechAct(str, Enum):
    ASSERTION = "assertion"
    QUESTION = "question"
    REQUEST = "request"
    OFFER = "offer"
    COMMITMENT = "commitment"
    HYPOTHESIS = "hypothesis"
    EXPERIENCE_REPORT = "experience_report"
    UNKNOWN = "unknown"


class Modality(str, Enum):
    ASSERTED = "asserted"
    POSSIBLE = "possible"
    PROBABLE = "probable"
    NECESSARY = "necessary"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PropositionAnnotation:
    speech_act: SpeechAct = SpeechAct.UNKNOWN
    modality: Modality = Modality.UNKNOWN
    negated: bool | None = None
    quantifier: str = "unspecified"
    time_scope: str = "unspecified"
    spatial_scope: str = "unspecified"
    referent: str = "unspecified"


def _has(phrase: str, terms: str) -> bool:
    return bool(re.search(r"\b(?:" + terms + r")\b", phrase, re.IGNORECASE))


def semantic_warnings(source: str, candidate: str) -> tuple[str, ...]:
    """Surface mismatches only; no warning DOES NOT mean semantically equivalent."""
    result: list[str] = []
    s, c = source.strip(), candidate.strip()
    if _has(s, r"not|never|no|cannot|can't|didn't|doesn't|won't") and not _has(
        c, r"not|never|no|cannot|can't|didn't|doesn't|won't"
    ):
        result.append("POSSIBLE_NEGATION_LOSS")
    if _has(s, r"may|might|could|possibly|perhaps") and _has(
        c, r"will|must|certainly|definitely|always"
    ):
        result.append("POSSIBLE_MODALITY_ESCALATION")
    if _has(s, r"some|several|a few") and _has(c, r"all|every|everyone|always"):
        result.append("POSSIBLE_QUANTIFIER_ESCALATION")
    if _has(s, r"ask|asked|asking|request|requested|please") and _has(
        c, r"demand|demanded|forced|ordered|commanded"
    ):
        result.append("POSSIBLE_SPEECH_ACT_ESCALATION")
    if _has(s, r"understand|understanding|listen|listening") and _has(
        c, r"obey|obedience|comply|compliance|submission"
    ):
        result.append("POSSIBLE_OBJECT_SUBSTITUTION")
    if _has(s, r"yesterday|last week|previously") and _has(c, r"tomorrow|next week|will"):
        result.append("POSSIBLE_TIME_SCOPE_DRIFT")
    # A risk signal only: inferred emotions, beliefs and intentions MUST NOT be
    # presented as the person's own meaning without that speaker's confirmation.
    if _has(c, r"want(?:s|ed|ing)?|feel(?:s|ing)?|felt|angry|hate(?:s|d)?|lov(?:e|es|ed|ing)|intend(?:s|ed|ing)?|intention|motives?|motivated|believ(?:e|es|ed|ing)|think(?:s|ing)?|thought|fear(?:s|ed)?|resent(?:s|ed)?|secretly") and not _has(
        s, r"want(?:s|ed|ing)?|feel(?:s|ing)?|felt|angry|hate(?:s|d)?|lov(?:e|es|ed|ing)|intend(?:s|ed|ing)?|intention|motives?|motivated|believ(?:e|es|ed|ing)|think(?:s|ing)?|thought|fear(?:s|ed)?|resent(?:s|ed)?|secretly"
    ):
        result.append("POSSIBLE_UNSTATED_MENTAL_STATE")
    # Detect exact numeric drift, without claiming all number words are covered.
    numbers_s = set(re.findall(r"(?<!\w)-?\d+(?:\.\d+)?\b", s))
    numbers_c = set(re.findall(r"(?<!\w)-?\d+(?:\.\d+)?\b", c))
    if numbers_s and numbers_c and numbers_s != numbers_c:
        result.append("POSSIBLE_QUANTITY_DRIFT")
    return tuple(dict.fromkeys(result))
