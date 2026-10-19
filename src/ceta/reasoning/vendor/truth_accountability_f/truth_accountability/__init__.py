"""Reference v1 ledger and the new host-gated governed implementation."""
from .core import TruthLedger, CheckResult, Verdict, ClaimKind
from .governed import AuthenticatedActor, Decision, GovernedTruthCore
from .semantic import PropositionAnnotation, SpeechAct, Modality, semantic_warnings
from .bridge import GatedResponse, GovernedModelBridge, arithmetic_only_policy, conservative_policy
from .ollama_adapter import LocalOllamaProposalClient
from .societal_v1 import (SourceRejected, CorpusMapping, ContextCandidate,
                          SourceInspection, Version1ReadOnlyAdapter)
from .societal_pipeline import SocietalGatedPipeline, SocietalGatedResult
from .version1_runtime import Version1RuntimeAdvisor, Version1RuntimeReview
from .verifiers import (EvidenceFinding, EvidenceVerdict, VerifierSpec,
                        VerificationRegistry, bounded_arithmetic)

__all__ = [
    "TruthLedger", "CheckResult", "Verdict", "ClaimKind",
    "AuthenticatedActor", "Decision", "GovernedTruthCore",
    "GatedResponse", "GovernedModelBridge", "arithmetic_only_policy", "conservative_policy",
    "LocalOllamaProposalClient",
    "SourceRejected", "CorpusMapping", "ContextCandidate", "SourceInspection",
    "Version1ReadOnlyAdapter", "SocietalGatedPipeline", "SocietalGatedResult",
    "Version1RuntimeAdvisor", "Version1RuntimeReview",
    "PropositionAnnotation", "SpeechAct", "Modality", "semantic_warnings",
    "EvidenceFinding", "EvidenceVerdict", "VerifierSpec",
    "VerificationRegistry", "bounded_arithmetic",
]
