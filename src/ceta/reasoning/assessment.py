"""Reasoning assessment: the immutable result of a shadow evaluation.

An assessment is an internal observation record. It does not confer
authority, issue permits, modify kernel state, or override any
existing CETA decision. It is purely informational evidence that
can be attached to context or continuity records.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum


def _text(value: str, name: str, maximum: int, *, empty: bool = False) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    if (not empty and not value.strip()) or "\0" in value:
        raise ValueError(f"{name} must be nonempty and contain no NUL")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{name} exceeds {maximum} UTF-8 bytes")


def _digest(value: str, name: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


class AssessmentOutcome(str, Enum):
    """Bounded outcome labels for shadow assessments."""
    ADVISORY_PASS = "ADVISORY_PASS"
    ADVISORY_HOLD = "ADVISORY_HOLD"
    CONTEXT_FOUND = "CONTEXT_FOUND"
    NO_CONTEXT = "NO_CONTEXT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    REVIEW_FAILURE = "REVIEW_FAILURE"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class ReasoningAssessment:
    """Frozen record of a single reasoning evaluation.

    Fields are evidence-typed: they record what was observed, not what
    was authorized. No field here creates a permit, alters a kernel
    decision, or establishes an independently verified fact.
    """
    # What was assessed
    source_text_sha256: str
    speaker_id: str

    # V1 contextual retrieval
    context_outcome: AssessmentOutcome
    context_refs: tuple[str, ...]
    context_status: str

    # Truth accountability gate result
    gate_outcome: AssessmentOutcome
    gate_decision: str
    gate_response: str

    # V1 runtime review
    runtime_review_status: str

    # Provenance
    raw_proposal_sha256: str | None
    claim_id: str | None
    established_fact: bool

    # Shadow-mode metadata
    shadow_mode: bool
    assessment_id: str

    def __post_init__(self) -> None:
        _digest(self.source_text_sha256, "source_text_sha256")
        if self.raw_proposal_sha256 is not None:
            _digest(self.raw_proposal_sha256, "raw_proposal_sha256")
        _text(self.speaker_id, "speaker_id", 128)
        _text(self.assessment_id, "assessment_id", 128)
        if type(self.context_outcome) is not AssessmentOutcome or type(self.gate_outcome) is not AssessmentOutcome:
            raise TypeError("Outcomes must be AssessmentOutcome values")
        if type(self.context_refs) is not tuple:
            raise TypeError("context_refs must be an immutable tuple")
        if len(self.context_refs) > 10:
            raise ValueError("At most ten context references are permitted")
        for ref in self.context_refs:
            _text(ref, "context reference", 128)
        for name in ("context_status", "gate_decision", "runtime_review_status"):
            value = getattr(self, name)
            _text(value, name, 128)
            if re.fullmatch(r"[A-Z][A-Z0-9_:]*", value) is None:
                raise ValueError(f"{name} must be an explicit status identifier")
        _text(self.gate_response, "gate_response", 65536, empty=True)
        if self.claim_id is not None:
            _text(self.claim_id, "claim_id", 128)
        if type(self.established_fact) is not bool or type(self.shadow_mode) is not bool:
            raise TypeError("established_fact and shadow_mode must be booleans")
        if self.shadow_mode and self.gate_response:
            raise ValueError("Shadow assessments must withhold rendered responses")

    def canonical_bytes(self) -> bytes:
        """Versioned, typed JSON; sequence and null boundaries are explicit."""
        record = {
            "schema": "ceta.reasoning-assessment.v2",
            "source_text_sha256": self.source_text_sha256,
            "speaker_id": self.speaker_id,
            "context_outcome": self.context_outcome.value,
            "context_refs": list(self.context_refs),
            "context_status": self.context_status,
            "gate_outcome": self.gate_outcome.value,
            "gate_decision": self.gate_decision,
            "gate_response": self.gate_response,
            "runtime_review_status": self.runtime_review_status,
            "raw_proposal_sha256": self.raw_proposal_sha256,
            "claim_id": self.claim_id,
            "established_fact": self.established_fact,
            "shadow_mode": self.shadow_mode,
            "assessment_id": self.assessment_id,
        }
        return json.dumps(record, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")

    def commitment(self) -> str:
        """Deterministic content hash for this assessment."""
        return "sha256:" + hashlib.sha256(
            b"CETA:reasoning-assessment:v2\0" + self.canonical_bytes()
        ).hexdigest()
