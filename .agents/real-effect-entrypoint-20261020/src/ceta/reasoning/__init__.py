"""Societal Reasoning Core V1 + Truth Accountability F: CETA integration.

This package adapts the original Societal Reasoning Core Version 1 and
Truth Accountability Increment F for use within Project-AI: CETA's
governed intelligence architecture.

The integration operates in shadow mode by default: reasoning assessments
are computed and recorded but do not independently alter authorization
results of existing canonical operations.

Source components under vendor/ retain their original identities and must
not be modified. Integration adapters in this package map their APIs onto
CETA's existing contract interfaces without creating a second sovereign
component, execution controller, or authoritative state.
"""
from .adapter import ProposalProvider, SocietalReasoningAdapter, SyntheticProposer
from .assessment import AssessmentOutcome, ReasoningAssessment
from .shadow import ModeTransition, ShadowLevel, ShadowModeController

__all__ = [
    "SocietalReasoningAdapter",
    "ProposalProvider",
    "SyntheticProposer",
    "AssessmentOutcome",
    "ReasoningAssessment",
    "ShadowLevel",
    "ModeTransition",
    "ShadowModeController",
]
