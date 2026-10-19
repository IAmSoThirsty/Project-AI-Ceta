"""Source-bounded checks of proposed *readings*, distinct from premise checks.

This module deliberately supports only two claims about evidence: (1) whether
an unconditional literal proposition is stated or opposed by supplied reports,
and (2) whether supplied wording contains an explicit universal quantified
claim. Both are statements *about source language*, not about a person's
traits, intended social function, real-world truth, or actual effects.

An unparseable interpretation remains UNREVIEWED, not false. A successful
source match must NEVER be reported as proof of a human's private motive.
"""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from .models import Evidence
from .semantic_support import _asserted_atom

# Only the complete, unquoted, unconditional surface pattern is considered.
# Fullmatch is intentional; text surrounding a claim can change its meaning.
_UNIVERSAL = re.compile(
    r"(?P<quantifier>All|Every|No) +"
    r"(?P<group>[A-Za-z][A-Za-z -]{0,78}?) +"
    r"(?P<operator>are|were|can|cannot|will|must|should|do|does|have|has|is) +"
    r"(?P<predicate>[A-Za-z][A-Za-z0-9 '-]{0,128}?)\.?",
    re.IGNORECASE,
)
_READING_UNIVERSAL = re.compile(
    r"The supplied text makes a universal claim about +"
    r"(?P<group>[A-Za-z][A-Za-z -]{0,78}?)\.", re.IGNORECASE,
)
_ARTIFACT_EVALUATION = re.compile(
    r"(?:The|This) +(?P<artifact>patch|build|program|module|function|app|"
    r"code|codebase|test|website|report|feature|commit|release) +"
    r"(?P<verb>fails|failed|passes|passed|contains|contained|lacks|lacked) +"
    r"(?P<detail>[A-Za-z0-9][A-Za-z0-9 '-]{0,128}?)\.", re.IGNORECASE,
)
_READING_ARTIFACT = re.compile(
    r"The supplied text evaluates the +"
    r"(?P<artifact>patch|build|program|module|function|app|code|codebase|"
    r"test|website|report|feature|commit|release)\.", re.IGNORECASE,
)
_HEDGES_AND_SCOPE = re.compile(
    r"\b(?:if|unless|when|assuming|because|although|perhaps|probably|allegedly|"
    r"supposedly|reportedly|maybe|likely|possibly|apparently|according|some|not|never|but|however)\b",
    re.IGNORECASE,
)
_POSSIBILITY = frozenset({"may", "might", "could", "can"})
# High-precision subset of third-person private-state assertions. A source
# mentioning behavior or a quote about a person does not authorize a claim
# about their actual internal experience. Not a complete person-state detector.
_PRIVATE_STATE = re.compile(
    r"^(?:(?i:the) +)?(?:(?i:author|poster|writer|speaker|user|person|developer|"
    r"he|she|they)|[A-Z][a-z]+) +(?:(?i:secretly|clearly|obviously|really|definitely) +)?"
    r"(?i:hates?|loves?|feels?|wants?|intends?|believes?|thinks?|"
    r"is +(?:angry|upset|afraid|scared|depressed|jealous|ashamed|anxious))\b",
)
# Grammatically simple speculation about *meaning* is not a literal report
# about the world. Parsing it as a modal assertion is not semantic validation.
_INTERPRETIVE_PREDICATES = frozenset({
    "function", "mean", "imply", "suggest", "signify", "represent",
    "indicate", "intend", "feel", "believe", "think", "seem",
    "appear", "prove", "demonstrate", "symbolize", "reveal", "hurt",
})


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _report_ref(e: Evidence) -> dict[str, Any]:
    return {"evidence_id": e.id, "source_ref": e.source_ref,
            "source_origin": e.origin, "evidence_sha256": _sha(e.statement)}


def _universal_pattern(text: str) -> dict[str, str] | None:
    if not isinstance(text, str) or not 10 <= len(text) <= 4096:
        return None
    if any(char in text for char in '\n\r?!:;"\u201c\u201d[]{}()'):
        return None
    cleaned = text.strip()
    match = _UNIVERSAL.fullmatch(cleaned)
    if match is None:
        return None
    group, predicate = match.group("group").strip(), match.group("predicate").strip().rstrip(".")
    # Do not mistake a hedge, embedded clause or negated predicate for an
    # unconditional quantified sentence. This rejects many real expressions,
    # deliberately, rather than silently changing their meaning.
    if (not group or not predicate or _HEDGES_AND_SCOPE.search(group) or
            _HEDGES_AND_SCOPE.search(predicate) or len(group.split()) > 10 or
            len(predicate.split()) > 24):
        return None
    return {"quantifier": match.group("quantifier").casefold(),
            "subject_phrase": " ".join(group.split()),
            "operator": match.group("operator").casefold(),
            "predicate_phrase": " ".join(predicate.split())}


def _artifact_pattern(text: str) -> dict[str, str] | None:
    if not isinstance(text, str) or not 10 <= len(text) <= 4096:
        return None
    if any(char in text for char in '\n\r?!:;"\u201c\u201d[]{}()'):
        return None
    match = _ARTIFACT_EVALUATION.fullmatch(text.strip())
    if match is None or _HEDGES_AND_SCOPE.search(match.group("detail")):
        return None
    return {"artifact_phrase": match.group("artifact").casefold(),
            "predicate": match.group("verb").casefold(),
            "detail": " ".join(match.group("detail").split())}


def source_language_signals(evidence: tuple[Evidence, ...]) -> list[dict[str, Any]]:
    """Find two narrowly patterned kinds of wording (not real-world truth).

    A quoted source is eligible as *wording*. Model interpretations are not.
    No group can be assigned the quoted descriptor by this function.
    """
    if (not isinstance(evidence, tuple) or len(evidence) > 64 or
            any(not isinstance(e, Evidence) or len(e.statement) > 4096 for e in evidence)):
        raise ValueError("Expected no more than 64 bounded Evidence records")
    if len({e.id for e in evidence}) != len(evidence):
        raise ValueError("Duplicate evidence identifiers")
    signals = []
    for e in sorted(evidence, key=lambda row: row.id):
        if e.origin == "interpretation":
            continue
        patterns = (("explicit_universal_quantifier_in_source_text", _universal_pattern(e.statement)),
                    ("explicit_work_product_evaluation_in_source_text", _artifact_pattern(e.statement)))
        for kind, pattern in patterns:
            if pattern is None:
                continue
            signals.append({**_report_ref(e), "kind": kind,
                            "surface_form": pattern,
                            "scope": "language_in_supplied_evidence_only",
                            "independently_verified_truth": False,
                            "speaker_endorsement_proven": False,
                            "actual_social_function_proven": False,
                            "personal_attribute_proven": False})
    return signals


def assess_reading_sources(reading: str, evidence: tuple[Evidence, ...]) -> dict[str, Any]:
    """Check a *candidate reading* against sources without trusting warrants.

    A literal reading can align with, or be directly opposed by, simple source
    assertions. A restricted textual reading can confirm that specified source
    wording universally quantifies a named group. Every other natural-language
    interpretation remains outside this validator, not disproved by it.
    """
    if not isinstance(reading, str) or not reading.strip() or len(reading) > 4096:
        raise ValueError("Reading must be a nonblank string of at most 4096 characters")
    signals = source_language_signals(evidence)
    source_assertion = _asserted_atom(reading)
    result: dict[str, Any] = {
        "reading": reading,
        "status": "unreviewable_social_or_open_language_reading",
        "check_method": "none_open_language_out_of_scope",
        "matches": [], "oppositions": [], "unresolved_modality": [],
        "source_text_only_not_factual_truth": True,
        "independent_authenticity_checked": False,
        "social_entailment_verified": False,
        "private_motive_or_attribute_verified": False,
    }
    # An explicit third-person internal-state claim requires attribution and
    # evidence beyond literal wording about somebody. Do not promote it merely
    # because someone wrote the same assertion into a source record.
    if _PRIVATE_STATE.search(reading.strip()):
        return {**result, "status": "third_party_private_state_not_independently_established",
                "check_method": "bounded_private_state_attribution_guard",
                "reason": "A statement about someone's private state is not established by lexical agreement or a submitted rationale"}

    # Class I: the reading itself is a restricted literal statement.
    if source_assertion is not None and source_assertion["predicate"] not in _INTERPRETIVE_PREDICATES:
        matches = []
        oppositions = []
        uncertain_modality = []
        for ev in sorted(evidence, key=lambda x: x.id):
            if ev.origin in {"interpretation", "quoted_material"}:
                continue
            stated = _asserted_atom(ev.statement)
            if stated is None:
                continue
            if any(stated[key] != source_assertion[key]
                   for key in ("subject", "predicate", "object")):
                continue
            if stated["modal"] != source_assertion["modal"]:
                # A change in tense or modality is not literal entailment.
                uncertain_modality.append({**_report_ref(ev), "reason": "modality_or_tense_differs"})
            elif stated["polarity"] == source_assertion["polarity"]:
                matches.append(_report_ref(ev))
            elif stated["modal"] in _POSSIBILITY:
                uncertain_modality.append({**_report_ref(ev), "reason": "positive_and_negative_possibilities_can_coexist"})
            else:
                oppositions.append(_report_ref(ev))
        if matches and oppositions:
            status = "opposed_source_reports_for_literal_reading"
        elif matches:
            status = "literal_reading_asserted_in_source_reports"
        elif oppositions:
            status = "literal_reading_opposed_by_source_reports"
        else:
            status = "literal_reading_not_established_by_supplied_sources"
        return {**result, "status": status,
                "check_method": "restricted_literal_claim_alignment",
                "literal_reading": source_assertion,
                "matches": matches, "oppositions": oppositions,
                "unresolved_modality": uncertain_modality}

    # Class II: a narrow textual statement about universal quantifier use.
    match = _READING_UNIVERSAL.fullmatch(reading.strip())
    if match is not None:
        target = " ".join(match.group("group").split()).casefold()
        matching = [signal for signal in signals
                    if signal["kind"] == "explicit_universal_quantifier_in_source_text"
                    and signal["surface_form"]["subject_phrase"].casefold() == target]
        return {**result,
                "status": "bounded_textual_generalization_matched" if matching else
                          "textual_generalization_not_established",
                "check_method": "universal_quantifier_surface_alignment",
                "matches": [
                    {"evidence_id": s["evidence_id"], "source_ref": s["source_ref"],
                     "source_origin": s["source_origin"], "evidence_sha256": s["evidence_sha256"],
                     "surface_form": s["surface_form"]} for s in matching
                ],
                "social_entailment_verified": False,
                "reading_is_about_source_wording_not_group_members": True}
    match = _READING_ARTIFACT.fullmatch(reading.strip())
    if match is not None:
        target = match.group("artifact").casefold()
        matching = [signal for signal in signals
                    if signal["kind"] == "explicit_work_product_evaluation_in_source_text"
                    and signal["surface_form"]["artifact_phrase"] == target]
        return {**result,
                "status": "bounded_work_product_evaluation_matched" if matching else
                          "work_product_evaluation_not_established",
                "check_method": "work_product_evaluation_surface_alignment",
                "matches": [
                    {"evidence_id": s["evidence_id"], "source_ref": s["source_ref"],
                     "source_origin": s["source_origin"], "evidence_sha256": s["evidence_sha256"],
                     "surface_form": s["surface_form"]} for s in matching
                ],
                "reported_evaluation_is_not_verified_defect": True}
    return result
