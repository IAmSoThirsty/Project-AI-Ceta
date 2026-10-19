"""Reasoning assessment: the immutable result of a shadow evaluation.

An assessment is an internal observation record. It does not confer
authority, issue permits, modify kernel state, or override any
existing CETA decision. It is purely informational evidence that
can be attached to context or continuity records.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any


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

    def commitment(self) -> str:
        """Deterministic content hash for this assessment."""
        parts = (
            self.source_text_sha256,
            self.speaker_id,
            self.context_outcome.value,
            ":".join(self.context_refs),
            self.context_status,
            self.gate_outcome.value,
            self.gate_decision,
            self.gate_response,
            self.runtime_review_status,
            self.raw_proposal_sha256 or "",
            self.claim_id or "",
            str(self.established_fact),
            str(self.shadow_mode),
            self.assessment_id,
        )
        content = "\0".join(parts).encode("utf-8")
        return "sha256:" + hashlib.sha256(
            b"CETA:reasoning-assessment:v1\0" + content
        ).hexdigest()
