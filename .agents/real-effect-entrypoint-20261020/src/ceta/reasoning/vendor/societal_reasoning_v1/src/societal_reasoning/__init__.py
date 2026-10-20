"""Societal Reasoning Core: auditable contextual interpretation (prototype)."""

from .engine import SocietalReasoner
from .corrections import CorrectionLedger
from .deliberation import DeliberationCase, Hypothesis, Warrant
from .semantic_support import WarrantPremise, check_premise, find_opposed_source_assertions
from .reading_support import assess_reading_sources, source_language_signals
from .relevance import EvidenceText, KnowledgeRelevance
from .graph import KnowledgeGraph
from .models import Concept, Edge, Evidence, Scenario

__version__ = "1"
__all__ = ["SocietalReasoner", "CorrectionLedger", "DeliberationCase", "Hypothesis", "Warrant", "WarrantPremise", "check_premise", "find_opposed_source_assertions", "assess_reading_sources", "source_language_signals", "EvidenceText", "KnowledgeRelevance", "KnowledgeGraph", "Concept", "Edge", "Evidence", "Scenario"]
