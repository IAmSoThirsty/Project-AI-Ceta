"""Explicit host-supplied Societal Reasoning Core Version 1 advisory API bridge.

The adapter never imports the user's ZIP automatically. The trusted host must
install or import the checksum-verified SocietalReasoner separately, then inject
its instance. Its output is a *second conservative review* under one host gate:
it is not independent evidence, social truth, or permission for model assertions.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Version1RuntimeReview:
    status: str
    proposed_response_mode: str
    issue_codes: tuple[str, ...]
    source_sha256: str
    api_schema: str
    advisory_only: bool = True


class Version1RuntimeAdvisor:
    """Bridge two actual public V1 methods; fail closed on malformed results."""

    def __init__(self, reasoner: Any):
        if not callable(getattr(reasoner, "assess_text", None)) or not callable(
            getattr(reasoner, "review_draft", None)
        ):
            raise TypeError("Trusted host must supply actual V1 reasoner API")
        self.reasoner = reasoner

    def review(self, *, speaker_id: str, source_id: str,
               exact_text: str, gated_draft: str) -> Version1RuntimeReview:
        if not isinstance(exact_text, str) or not isinstance(gated_draft, str):
            raise TypeError("Source and gated draft must be strings")
        if len(exact_text.encode("utf-8")) > 1024 * 1024 or len(gated_draft) > 65536:
            raise ValueError("Version 1 text exceeds bounded contract")
        # V1 turn IDs and speaker fields use constrained references; a stable
        # pseudonym is used for unsupported host names, without attributing a
        # different human identity or changing any source text.
        identifier = source_id if re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", source_id) else             "turn-" + hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]
        safe_speaker = speaker_id if re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", speaker_id) else             "speaker-" + hashlib.sha256(speaker_id.encode("utf-8")).hexdigest()[:20]
        assessment = self.reasoner.assess_text(exact_text, turn_id=identifier,
                                               speaker=safe_speaker)
        if not isinstance(assessment, dict) or assessment.get("schema") != "text_assessment.v1":
            raise ValueError("V1 assessment schema mismatch")
        received = assessment.get("utterance")
        expected_digest = hashlib.sha256(exact_text.encode("utf-8")).hexdigest()
        if not isinstance(received, dict) or received.get("text") != exact_text or                 received.get("sha256") != expected_digest or received.get("speaker") != safe_speaker:
            raise ValueError("V1 assessment did not preserve the exact speaker/source")
        result = self.reasoner.review_draft(assessment, gated_draft)
        if not isinstance(result, dict) or result.get("status") not in {"pass", "review_needed", "hold"}:
            raise ValueError("V1 review returned unknown verdict")
        issues = result.get("issues")
        if not isinstance(issues, list) or any(not isinstance(x, dict) or
                not isinstance(x.get("code"), str) for x in issues):
            raise ValueError("V1 review has invalid issue structure")
        # A positive V1 surface review is explicitly NOT general entailment.
        verdict = "REVIEW_HOLD" if result["status"] != "pass" or issues else "ADVISORY_PASS"
        return Version1RuntimeReview(verdict, assessment.get("response_mode", "unknown"),
                                     tuple(x["code"] for x in issues), expected_digest,
                                     "text_assessment.v1")
