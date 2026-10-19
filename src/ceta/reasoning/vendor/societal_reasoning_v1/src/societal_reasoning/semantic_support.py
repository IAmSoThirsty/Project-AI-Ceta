"""Bounded checks that a warrant's *literal premise* appears in its source.

The domain of this validator is deliberately narrow. A successful check establishes
only that supplied text contains a specified excerpt or an explicitly asserted
proposition with the same actor, modal, predicate, scope, and polarity. It does
NOT establish factual truth, authentic authorship, relevance to a social reading,
or the validity of a proposed supporting/challenging inference.

Never treat a partial word match, inferred synonym, translated text, quoted
speech, or unparsed conditional as entailment.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any

from .models import Evidence

_SHA = re.compile(r"^[a-f0-9]{64}$")
_MODAL = "will|may|might|can|could|did|does|do"
_ATOM = re.compile(
    rf"(?P<subject>[A-Za-z][A-Za-z-]*(?: +[A-Za-z][A-Za-z-]*){{0,2}}) +"
    rf"(?P<modal>{_MODAL}) +(?P<negative>not +)?"
    r"(?P<verb>[A-Za-z]+)(?: +(?P<object>[A-Za-z0-9][A-Za-z0-9 /'-]*))?\.?",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(r"\b(?:if|unless|when|although|because|provided|assuming|probably|perhaps|maybe|reportedly|allegedly|supposedly)\b", re.I)
_INVALID_SUBJECT_PARTS = {"think", "thought", "said", "says", "believe", "believed", "claim", "claims", "tell", "told"}


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _asserted_atom(text: str) -> dict[str, Any] | None:
    """Parse one restricted literal declaration; no general NLP is attempted."""
    if not isinstance(text, str) or not 3 <= len(text) <= 512:
        return None
    if any(c in text for c in '\n\r?;:!"\u201c\u201d()[]{}') or "'" in text and not re.search(r"[A-Za-z]'[A-Za-z]", text):
        return None
    if _CONDITIONAL.search(text):
        return None
    raw = text.strip()
    match = _ATOM.fullmatch(raw)
    if match is None:
        return None
    subject = match.group("subject").split()
    if len(subject) > 1:
        # A short named entity (Alex Carter), or one explicit noun phrase
        # (the programmer). A nested clause such as 'they said they' fails.
        if (subject[0].casefold() not in {"the", "a", "an"}
                and not all(word[0].isupper() for word in subject)):
            return None
    if any(word.casefold() in _INVALID_SUBJECT_PARTS for word in subject):
        return None
    obj = (match.group("object") or "").strip()
    if re.search(r"\b(?:and|or|but|not|never|no|cannot|can't|won't|didn't|doesn't|don't)\b", obj, re.I):
        return None
    return {
        "subject": " ".join(subject).casefold(),
        "modal": match.group("modal").casefold(),
        "predicate": match.group("verb").casefold(),
        "object": " ".join(obj.split()).casefold(),
        "polarity": "negative" if match.group("negative") else "positive",
    }


@dataclass(frozen=True, slots=True)
class WarrantPremise:
    """Optional, digest-bound claim about the exact supplied evidence text.

    For verbatim_span, `text` must match the specified [start,end) Unicode
    character offsets. For literal_assertion, the text must parse in the
    restricted grammar and match one complete source assertion.
    """

    kind: str
    text: str
    evidence_sha256: str
    start: int | None = None
    end: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"verbatim_span", "literal_assertion"}:
            raise ValueError("Unsupported premise check type")
        if not isinstance(self.text, str) or not self.text.strip() or len(self.text) > 512:
            raise ValueError("Premise text must be 1..512 nonblank characters")
        if not isinstance(self.evidence_sha256, str) or not _SHA.fullmatch(self.evidence_sha256):
            raise ValueError("Expected a lowercase SHA-256 fingerprint of the complete source record")
        if self.kind == "verbatim_span":
            if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end:
                raise ValueError("Verbatim check requires exact character start/end offsets")
            if self.end - self.start != len(self.text):
                raise ValueError("Verbatim span length differs from quoted text")
        else:
            if self.start is not None or self.end is not None or _asserted_atom(self.text) is None:
                raise ValueError("Literal assertion must match the restricted grammar and omit offsets")

    @classmethod
    def from_dict(cls, row: dict) -> WarrantPremise:
        if not isinstance(row, dict):
            raise ValueError("Premise check must be an object")
        expected = {"kind", "text", "evidence_sha256"}
        allowed = expected | {"start", "end"}
        if not expected <= set(row) or set(row) - allowed:
            raise ValueError("Invalid premise-check fields")
        if row.get("kind") == "literal_assertion" and ("start" in row or "end" in row):
            raise ValueError("Literal assertion may not supply source offsets")
        return cls(kind=row["kind"], text=row["text"], evidence_sha256=row["evidence_sha256"],
                   start=row.get("start"), end=row.get("end"))

    def to_dict(self) -> dict[str, Any]:
        result = {"kind": self.kind, "text": self.text, "evidence_sha256": self.evidence_sha256}
        if self.kind == "verbatim_span":
            result.update({"start": self.start, "end": self.end})
        return result


def check_premise(evidence: Evidence, premise: WarrantPremise) -> dict[str, Any]:
    """Return a narrow source-claim relation, NEVER a verdict on people or truth."""
    if not isinstance(evidence, Evidence) or not isinstance(premise, WarrantPremise):
        raise ValueError("Expected an Evidence and WarrantPremise")
    base: dict[str, Any] = {
        "kind": premise.kind,
        "evidence_id": evidence.id,
        "source_origin": evidence.origin,
        "actual_source_sha256": _digest(evidence.statement),
        "expected_source_sha256": premise.evidence_sha256,
        "factual_truth_checked": False,
        "external_authenticity_checked": False,
        "social_inference_validated": False,
    }
    if base["actual_source_sha256"] != premise.evidence_sha256:
        return {**base, "status": "stale_source_binding", "reason": "Evidence text changed from the digest bound by this premise"}
    if evidence.origin == "interpretation":
        return {**base, "status": "excluded_prior_interpretation", "reason": "A prior interpretation cannot establish observational evidence"}
    if premise.kind == "verbatim_span":
        start, end = premise.start, premise.end
        assert start is not None and end is not None
        if end > len(evidence.statement) or evidence.statement[start:end] != premise.text:
            return {**base, "status": "not_established", "reason": "Exact Unicode source text absent at the supplied offsets"}
        return {**base, "status": "source_text_matched", "reason": "Specified bytes are present in the supplied source; no meaning or factual truth inferred",
                "matched_span": {"start": start, "end": end, "text": premise.text,
                                 "sha256": _digest(premise.text)}}
    if evidence.origin == "quoted_material":
        return {**base, "status": "unreviewable_attribution", "reason": "Quoted material cannot be assigned to the quoting speaker as an assertion"}
    asserted = _asserted_atom(evidence.statement)
    wanted = _asserted_atom(premise.text)
    if asserted is None or wanted is None:
        return {**base, "status": "unreviewable_source_syntax",
                "reason": "Source is not one unquoted, unconditional declaration in the restricted grammar"}
    if asserted["subject"] != wanted["subject"]:
        return {**base, "status": "actor_scope_mismatch", "source_atom": asserted,
                "reason": "The source describes a different grammatical subject"}
    if any(asserted[key] != wanted[key] for key in ("predicate", "object")):
        return {**base, "status": "predicate_or_scope_mismatch", "source_atom": asserted,
                "reason": "Action or specified object/time differs; no paraphrase or temporal inference"}
    if asserted["modal"] != wanted["modal"]:
        return {**base, "status": "modality_mismatch", "source_atom": asserted,
                "reason": "Different modal/tense markers do not license an inference"}
    if asserted["polarity"] != wanted["polarity"]:
        if asserted["modal"] in {"may", "might", "could", "can"}:
            # 'May attend' and 'may not attend' express different possibilities;
            # neither unambiguously denies the other. Do not call this a contradiction.
            return {**base, "status": "modal_polarity_undetermined", "source_atom": asserted,
                    "reason": "Positive and negative possibilities are not automatically contradictory"}
        return {**base, "status": "source_explicitly_opposes_claim", "source_atom": asserted,
                "reason": "Same literal subject, action, scope and modal, but opposite polarity is stated"}
    return {**base, "status": "source_asserts_literal_proposition", "source_atom": asserted,
            "reason": "The supplied source explicitly asserts this bounded proposition; reality and wider interpretation are unverified"}


def find_opposed_source_assertions(evidence_records: tuple[Evidence, ...]) -> list[dict[str, Any]]:
    """Find source records *saying* opposite literals; never decide who is right.

    No equivalence of synonyms, contexts or independent authenticity is inferred.
    Modal possibility ('may' / 'may not') is never treated as an opposition.
    """
    if not isinstance(evidence_records, tuple) or len(evidence_records) > 64 or any(
        not isinstance(e, Evidence) for e in evidence_records
    ):
        raise ValueError("Expected up to 64 source evidence records")
    available: dict[tuple[str, str, str, str], list[tuple[Evidence, dict[str, Any]]]] = {}
    for ev in evidence_records:
        if ev.origin in {"quoted_material", "interpretation"}:
            continue
        atom = _asserted_atom(ev.statement)
        if atom is None or atom["modal"] in {"may", "might", "could", "can"}:
            continue
        key = tuple(atom[field] for field in ("subject", "modal", "predicate", "object"))
        available.setdefault(key, []).append((ev, atom))
    found: list[dict[str, Any]] = []
    for key in sorted(available):
        items = available[key]
        pos = [e for e, a in items if a["polarity"] == "positive"]
        neg = [e for e, a in items if a["polarity"] == "negative"]
        for yes in pos:
            for no in neg:
                # IDs are unique in the enclosing scenario; the returned
                # status concerns two statements, never an adjudicated fact.
                found.append({
                    "evidence_ids": [yes.id, no.id],
                    "source_refs": [yes.source_ref, no.source_ref],
                    "source_sha256": [_digest(yes.statement), _digest(no.statement)],
                    "literal_scope": {k: v for k, v in zip(("subject", "modal", "predicate", "object"), key)},
                    "status": "opposed_literal_source_reports_not_a_factual_verdict",
                    "external_source_authenticity_checked": False,
                    "same_event_or_time_independently_established": False,
                    "subject_coreference_independently_established": False,
                })
    return found
