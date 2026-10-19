"""Adapter bridging Societal Reasoning Core V1 into CETA's architecture.

This adapter wraps the original V1 SocietalReasoner and the F-layer
Version1ReadOnlyAdapter/Version1RuntimeAdvisor to provide contextual
retrieval and runtime review as CETA-native operations.

The adapter does not create authority, issue permits, or modify kernel
state. All results are ReasoningAssessment records suitable for shadow
observation or advisory attachment to context compilation.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from .assessment import AssessmentOutcome, ReasoningAssessment
from .source_loader import is_loaded, load_components


class ProposalProvider(Protocol):
    """Minimal contract for generating a model proposal."""
    def generate_proposal(
        self, source_id: str, source_text: str, *,
        contextual_references: list[dict] | None = None
    ) -> str: ...


@dataclass(frozen=True)
class SyntheticProposer:
    """A non-model proposer for testing without Ollama.

    Returns a fixed structured response that the governed bridge
    will evaluate deterministically. This is not a mock passed off
    as live integration — it is explicitly labelled synthetic.
    """
    label: str = "synthetic-test-proposer"

    def generate_proposal(
        self, source_id: str, source_text: str, *,
        contextual_references: list[dict] | None = None
    ) -> str:
        import json
        return json.dumps({
            "kind": "observation",
            "text": f"[Synthetic evaluation of: {source_text[:200]}]",
            "source_id": source_id,
            "synthetic": True,
        })


class SocietalReasoningAdapter:
    """CETA adapter for V1 societal reasoning + F truth accountability.

    Operates in shadow mode by default. Shadow mode means:
    - Assessments are computed and returned
    - No CETA kernel state is modified
    - No permits are issued or consumed
    - Results are advisory observations only

    When shadow_mode=False (future, requires owner authorization):
    - Assessments could be bound to context compilation
    - Still cannot independently issue permits or override kernel
    """

    def __init__(self, *, shadow_mode: bool = True):
        self._shadow_mode = shadow_mode
        self._adapter = None
        self._advisor = None
        self._inspection = None
        self._pipeline = None
        self._core = None
        self._initialized = False

    @property
    def shadow_mode(self) -> bool:
        return self._shadow_mode

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        """Load and verify vendor components, build the governed pipeline.

        Raises RuntimeError if source verification fails. Must be called
        exactly once before assess().
        """
        if self._initialized:
            raise RuntimeError("Already initialized")

        verification = load_components()

        from truth_accountability import (
            CorpusMapping, Version1ReadOnlyAdapter, Version1RuntimeAdvisor,
            GovernedTruthCore, GovernedModelBridge, SocietalGatedPipeline,
            arithmetic_only_policy,
        )
        import societal_reasoning

        self._adapter = Version1ReadOnlyAdapter.__new__(Version1ReadOnlyAdapter)
        # Re-use the already-verified adapter from the loader path.
        # The loader has already confirmed 2000 records and archive identity.
        from .source_loader import _ARCHIVES, _F_ROOT, _V1_ARCHIVE_SHA256
        import json
        mapping_path = _F_ROOT / "configs" / "version1_canonical_mapping.json"
        mapping_data = json.loads(mapping_path.read_text("utf-8"))
        self._adapter = Version1ReadOnlyAdapter(
            _ARCHIVES / "Societal-Reasoning-Core-v1.zip",
            mapping=CorpusMapping(**mapping_data),
            expected_zip_sha256=_V1_ARCHIVE_SHA256,
        )
        self._inspection = self._adapter.inspect()

        self._advisor = Version1RuntimeAdvisor(
            societal_reasoning.SocietalReasoner.starter()
        )

        # Ephemeral session key. No durable audit claim.
        self._core = GovernedTruthCore(audit_key=os.urandom(32))
        bridge = GovernedModelBridge(self._core, arithmetic_only_policy)
        self._pipeline = SocietalGatedPipeline(
            self._core, bridge, self._adapter, self._advisor
        )
        self._initialized = True

    def assess(
        self, *, speaker_id: str, text: str,
        proposer: ProposalProvider | None = None,
    ) -> ReasoningAssessment:
        """Run a shadow assessment through the full V1+F pipeline.

        Returns a frozen ReasoningAssessment. When shadow_mode is True
        (default), this result is purely advisory and does not affect
        any CETA operation.
        """
        if not self._initialized:
            raise RuntimeError("Call initialize() first")
        if not speaker_id or not isinstance(text, str) or not text.strip():
            raise ValueError("Non-empty speaker_id and text required")

        if proposer is None:
            proposer = SyntheticProposer()

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assessment_id = f"ra-{uuid.uuid4().hex[:16]}"

        try:
            result = self._pipeline.execute(
                speaker_id=speaker_id,
                exact_text=text,
                proposer=proposer,
            )
        except Exception as exc:
            return ReasoningAssessment(
                source_text_sha256=text_hash,
                speaker_id=speaker_id,
                context_outcome=AssessmentOutcome.SOURCE_UNAVAILABLE,
                context_refs=(),
                context_status="PIPELINE_ERROR",
                gate_outcome=AssessmentOutcome.REVIEW_FAILURE,
                gate_decision=f"ERROR:{type(exc).__name__}",
                gate_response="",
                runtime_review_status="NOT_EXECUTED",
                raw_proposal_sha256=None,
                claim_id=None,
                established_fact=False,
                shadow_mode=self._shadow_mode,
                assessment_id=assessment_id,
            )

        # Map pipeline result to assessment outcomes
        if result.context_refs:
            ctx_outcome = AssessmentOutcome.CONTEXT_FOUND
        elif result.context_status == "NO_VERSION1_SOURCE_ATTACHED":
            ctx_outcome = AssessmentOutcome.SOURCE_UNAVAILABLE
        else:
            ctx_outcome = AssessmentOutcome.NO_CONTEXT

        if result.decision in ("ACCEPTED", "ESTABLISHED_FACT"):
            gate_outcome = AssessmentOutcome.ADVISORY_PASS
        elif result.decision in ("VERSION1_REVIEW_HOLD", "NEEDS_PERSON_EVIDENCE"):
            gate_outcome = AssessmentOutcome.ADVISORY_HOLD
        elif result.decision in ("VERSION1_REVIEW_FAILURE", "MODEL_PROPOSAL_REJECTED"):
            gate_outcome = AssessmentOutcome.REVIEW_FAILURE
        else:
            gate_outcome = AssessmentOutcome.NOT_EVALUATED

        return ReasoningAssessment(
            source_text_sha256=text_hash,
            speaker_id=speaker_id,
            context_outcome=ctx_outcome,
            context_refs=result.context_refs,
            context_status=result.context_status,
            gate_outcome=gate_outcome,
            gate_decision=result.decision,
            gate_response=result.response if not self._shadow_mode else "",
            runtime_review_status=result.version1_runtime_review,
            raw_proposal_sha256=result.raw_proposal_sha256,
            claim_id=result.claim_id,
            established_fact=result.established_fact,
            shadow_mode=self._shadow_mode,
            assessment_id=assessment_id,
        )

    def context_only(self, text: str, *, limit: int = 4) -> list[dict]:
        """Retrieve V1 contextual candidates without running the full pipeline.

        Returns a list of candidate dicts with entry_id, text excerpt,
        and source_member. Does not invoke any model or truth gate.
        """
        if not self._initialized:
            raise RuntimeError("Call initialize() first")
        if self._adapter is None:
            return []

        candidates = self._adapter.candidates(text, limit=limit)
        return [
            {
                "entry_id": c.entry_id,
                "text_excerpt": c.exact_text[:512] if c.exact_text else "",
                "source_member": c.source_member,
                "text_sha256": c.text_sha256,
                "authority": "UNVERIFIED_CONTEXT_ONLY",
            }
            for c in candidates
        ]

    def close(self) -> None:
        """Release the ephemeral truth core session."""
        if self._core is not None:
            try:
                self._core.close()
            except Exception:
                pass
            self._core = None
