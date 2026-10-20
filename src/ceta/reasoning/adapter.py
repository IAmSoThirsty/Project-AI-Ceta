"""Verified V1/F reasoning sessions returning bounded advisory observations.

Sessions own an ephemeral in-memory reference ledger. They do not connect to
CETA's canonical ledger, model service, authorization kernel or tool broker.
The caller explicitly supplies a proposal provider; no synthetic fallback runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass
from typing import Protocol
from types import SimpleNamespace

from .assessment import AssessmentOutcome, ReasoningAssessment, _text
from .source_loader import corpus_mapping_bytes, load_components


class ProposalProvider(Protocol):
    """A caller-supplied provider of one bounded, untrusted JSON proposal."""
    def generate_proposal(
        self, source_id: str, source_text: str, *,
        contextual_references: list[dict] | None = None,
    ) -> str: ...


@dataclass(frozen=True)
class SyntheticProposer:
    """Explicit legacy rejection fixture, never an implicit provider.

    Its deliberately unsupported ``observation`` kind and ``synthetic`` field
    exercise proposal rejection. It is not a functioning model substitute.
    """
    label: str = "synthetic-test-proposer"

    def generate_proposal(
        self, source_id: str, source_text: str, *,
        contextual_references: list[dict] | None = None,
    ) -> str:
        return json.dumps({"kind": "observation",
                           "text": f"[Synthetic evaluation of: {source_text[:200]}]",
                           "source_id": source_id, "synthetic": True})


_PASS = frozenset({"QUOTED_VERBATIM", "MEANING_REVIEWED", "SUPPORTED_BY_CHECK"})
_HOLD = frozenset({
    "HYPOTHESIS_ONLY", "HYPOTHESIS_HELD_FOR_REVIEW", "VERSION1_REVIEW_HOLD",
    "NEEDS_PERSON_EVIDENCE", "NEEDS_MEANING_REVIEW", "NEEDS_RECONSIDERATION",
    "NEEDS_SENSE_RESOLUTION", "MEANING_DISPUTED", "UNVERIFIED",
    "STALE_EVIDENCE", "DISPUTED", "INSUFFICIENT_EVIDENCE",
})
_FAIL = frozenset({"SOURCE_MISMATCH", "WITHDRAWN", "REFUTED_BY_CHECK",
                   "MODEL_PROPOSAL_REJECTED", "VERSION1_REVIEW_FAILURE"})


def _gate_outcome(decision: str) -> AssessmentOutcome:
    if decision in _PASS:
        return AssessmentOutcome.ADVISORY_PASS
    if decision in _HOLD:
        return AssessmentOutcome.ADVISORY_HOLD
    if decision in _FAIL:
        return AssessmentOutcome.REVIEW_FAILURE
    return AssessmentOutcome.NOT_EVALUATED


class SocietalReasoningAdapter:
    """Thread-confined advisory session with explicit initialization/retirement.

    Verified modules are reusable across sessions. Every session gets its own
    reasoner and in-memory reference ledger. ``shadow_mode=False`` permits
    returning the reference renderer's advisory text; it grants no attachment
    or execution authority. A closed instance is terminal; create another one.
    """

    def __init__(self, *, shadow_mode: bool = True):
        if type(shadow_mode) is not bool:
            raise TypeError("shadow_mode must be a boolean")
        self._shadow_mode = shadow_mode
        self._adapter = self._advisor = self._inspection = None
        self._pipeline = self._core = None
        self._initialized = False
        self._closed = False
        self._busy = False
        self._owner_thread: int | None = None
        self._last_error: Exception | None = None

    @property
    def shadow_mode(self) -> bool:
        return self._shadow_mode

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def last_error(self) -> Exception | None:
        """Actual last pipeline failure, without serializing provider contents."""
        return self._last_error

    def _check_thread(self) -> None:
        if self._owner_thread is not None and self._owner_thread != threading.get_ident():
            raise RuntimeError("Reasoning sessions must remain on their initializing thread")
        if self._busy:
            raise RuntimeError("Reasoning session operation is already in progress")

    def _require_ready(self) -> None:
        self._check_thread()
        if self._closed or not self._initialized:
            raise RuntimeError("An initialized, open reasoning session is required")

    def initialize(self) -> None:
        """Verify actual sources and construct one independent local session.

        Failed construction retires its core. If retirement itself fails, the
        original exception retains the secondary error and ``close`` can retry
        the retained core; initialization cannot discard that custody.
        """
        self._check_thread()
        if self._closed or self._initialized or self._core is not None:
            raise RuntimeError("Session is closed, initialized, or still owns a core")
        self._owner_thread = threading.get_ident()
        self._busy = True
        try:
            load_components()
            from truth_accountability import (
                CorpusMapping, GovernedModelBridge, GovernedTruthCore,
                SocietalGatedPipeline, VerificationRegistry, VerifierSpec,
                Version1ReadOnlyAdapter, Version1RuntimeAdvisor,
                arithmetic_only_policy, bounded_arithmetic,
            )
            from societal_reasoning import SocietalReasoner
            from .source_loader import _ARCHIVES, _V1_ARCHIVE_SHA256

            contextual = Version1ReadOnlyAdapter(
                _ARCHIVES / "Societal-Reasoning-Core-v1.zip",
                mapping=CorpusMapping(**json.loads(corpus_mapping_bytes())),
                expected_zip_sha256=_V1_ARCHIVE_SHA256,
            )
            inspection = contextual.inspect()
            advisor = Version1RuntimeAdvisor(SocietalReasoner.starter())
            registry = VerificationRegistry()
            registry.register(VerifierSpec("arithmetic", "local-arithmetic-v1", bounded_arithmetic))
            # Retain the instance before __init__: a constructor failure after
            # SQLite allocation must still leave a reachable retirement path.
            audit_key = os.urandom(32)
            self._core = GovernedTruthCore.__new__(GovernedTruthCore)
            GovernedTruthCore.__init__(self._core, registry=registry, audit_key=audit_key)
            bridge = GovernedModelBridge(self._core, arithmetic_only_policy)
            pipeline = SocietalGatedPipeline(self._core, bridge, contextual, advisor)
            self._adapter, self._inspection, self._advisor = contextual, inspection, advisor
            self._pipeline = pipeline
            self._initialized = True
        except BaseException as primary:
            if self._core is not None and "db" not in vars(self._core):
                self._core = None
            if self._core is not None:
                try:
                    self._core.close()
                except BaseException as secondary:
                    try:
                        data = BaseException.__dict__["__dict__"].__get__(primary)
                        dict.__setitem__(data, "reasoning_cleanup_error", secondary)
                    except BaseException:
                        pass  # Diagnostics cannot replace the original failure.
                else:
                    self._core = None
            raise
        finally:
            self._busy = False

    def assess(
        self, *, speaker_id: str, text: str,
        proposer: ProposalProvider | None = None,
    ) -> ReasoningAssessment:
        """Evaluate an explicitly admitted provider through the actual pipeline.

        Provider attribute admission is guarded and its callable is captured once.
        Admission errors propagate before the pipeline preserves a source. Body
        failures produce PIPELINE_ERROR and retain their actual exception locally.
        Unknown decisions withhold response and established-fact claims.
        """
        self._require_ready()
        _text(speaker_id, "speaker_id", 128)
        _text(text, "text", 65536)
        if proposer is None:
            raise ValueError("An explicit proposal provider is required")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assessment_id = "ra-" + uuid.uuid4().hex
        self._busy = True
        try:
            generate = getattr(proposer, "generate_proposal", None)
            if not callable(generate):
                raise ValueError("An explicit proposal provider is required")
            provider = SimpleNamespace(generate_proposal=generate)
            self._last_error = None
            try:
                result = self._pipeline.execute(speaker_id=speaker_id, exact_text=text, proposer=provider)
            except Exception as exc:
                self._last_error = exc
                return ReasoningAssessment(
                    text_hash, speaker_id, AssessmentOutcome.NOT_EVALUATED, (),
                    "PIPELINE_ERROR", AssessmentOutcome.REVIEW_FAILURE, "PIPELINE_ERROR",
                    "", "NOT_EXECUTED", None, None, False, self._shadow_mode, assessment_id,
                )
            context = (AssessmentOutcome.CONTEXT_FOUND if result.context_refs else
                       AssessmentOutcome.SOURCE_UNAVAILABLE
                       if result.context_status == "NO_VERSION1_SOURCE_ATTACHED" else
                       AssessmentOutcome.NO_CONTEXT)
            outcome = _gate_outcome(result.decision)
            known = outcome is not AssessmentOutcome.NOT_EVALUATED
            return ReasoningAssessment(
                source_text_sha256=text_hash, speaker_id=speaker_id,
                context_outcome=context, context_refs=result.context_refs,
                context_status=result.context_status, gate_outcome=outcome,
                gate_decision=result.decision,
                gate_response=result.response if known and not self._shadow_mode else "",
                runtime_review_status=result.version1_runtime_review,
                raw_proposal_sha256=result.raw_proposal_sha256, claim_id=result.claim_id,
                established_fact=(result.decision == "SUPPORTED_BY_CHECK" and result.established_fact is True),
                shadow_mode=self._shadow_mode, assessment_id=assessment_id,
            )
        finally:
            self._busy = False

    def context_only(self, text: str, *, limit: int = 4) -> list[dict]:
        """Return bounded, source-labelled unverified contextual candidates."""
        self._require_ready()
        _text(text, "text", 65536)
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("limit must be an integer from one through ten")
        return [
            {"entry_id": item.entry_id, "text_excerpt": item.exact_text[:512],
             "source_member": item.source_member, "text_sha256": item.text_sha256,
             "authority": "UNVERIFIED_CONTEXT_ONLY"}
            for item in self._adapter.candidates(text, limit=limit)
        ]

    def close(self) -> None:
        """Stop admission and close on the owning thread; retain failed custody.

        A failed close propagates its error and keeps the core for another
        explicit ``close`` call. It cannot continue assessment after that error.
        """
        self._check_thread()
        self._closed = True
        self._initialized = False
        if self._core is not None:
            self._core.close()
            self._core = None
        self._pipeline = self._adapter = self._advisor = self._inspection = None
