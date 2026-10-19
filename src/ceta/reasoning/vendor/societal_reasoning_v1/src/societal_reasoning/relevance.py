"""Source-attributed, deliberately non-diagnostic knowledge retrieval.

Retrieval produces candidate *topics* worth checking, not observations of people,
causal conclusions, personality labels, or validated societal mechanisms.
Only caller-supplied source material is eligible. Model hypotheses are not.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import log
import re
from typing import Iterable

from .graph import KnowledgeGraph

_WORDS = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)?", re.UNICODE)
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_STOP = frozenset((
    "a", "about", "above", "across", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "as", "at", "be", "because", "been", "before", "being",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "during",
    "each", "either", "every", "for", "from", "had", "has", "have", "having", "he",
    "her", "hers", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "just", "may", "me", "might", "more", "most", "my", "nor", "not", "of", "on",
    "one", "or", "our", "ours", "over", "she", "should", "so", "some", "someone",
    "such", "than", "that", "the", "their", "them", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "us", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "why", "will",
    "with", "would", "you", "your", "yours", "human", "humans", "people", "person",
    "persons", "society", "social", "things", "thing", "really", "very",
))
_ORIGINS = frozenset(("user_utterance", "user_report", "direct_observation", "quoted_material", "external_record"))


def terms(value: str) -> tuple[str, ...]:
    """Compact exact-token normalization; deliberately no speculative stemming."""
    return tuple(w.group().casefold().replace("\u2019", "'") for w in _WORDS.finditer(value))


def relevant_terms(value: str) -> frozenset[str]:
    return frozenset(w for w in terms(value) if (len(w) >= 3 or w == "ai") and w not in _STOP)


@dataclass(frozen=True, slots=True)
class EvidenceText:
    id: str
    text: str
    origin: str
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _SOURCE_ID.fullmatch(self.id):
            raise ValueError("Invalid retrieval source identifier")
        if not isinstance(self.text, str) or not self.text.strip() or len(self.text) > 65536:
            raise ValueError("Invalid retrieval source text")
        if self.origin not in _ORIGINS:
            raise ValueError("Only attributed non-model source origins are eligible")
        if self.source_ref is not None and (
            not isinstance(self.source_ref, str) or not self.source_ref.strip()
            or len(self.source_ref) > 512
        ):
            raise ValueError("Invalid source reference")

    def descriptor(self) -> dict:
        return {
            "source_id": self.id,
            "origin": self.origin,
            "source_ref": self.source_ref,
            "source_sha256": sha256(self.text.encode("utf-8")).hexdigest(),
            "evidence_status": "source_text_reported_not_independently_verified",
        }


class KnowledgeRelevance:
    """Reusable lexical retrieval index over the canonical concept graph.

    A concept's presence in the results *never* establishes the concept applies
    to an individual. Related edges are returned with their provenance and
    cannot contribute to a premise or boost a score.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        self._index: dict[int, tuple[frozenset[str], frozenset[str], tuple[tuple[str, ...], ...]]] = {}
        postings: dict[str, set[int]] = {}
        df: Counter[str] = Counter()
        for concept_id, concept in graph.concepts.items():
            labels = (concept.label, *concept.aliases)
            names = frozenset().union(*(relevant_terms(v) for v in labels))
            summary = relevant_terms(concept.summary)
            phrases = tuple(tuple(w for w in terms(label) if w not in _STOP)
                            for label in labels)
            self._index[concept_id] = names, summary, phrases
            for word in names | summary:
                postings.setdefault(word, set()).add(concept_id)
            df.update(names | summary)
        n = len(graph.concepts)
        self._weight = {word: round(1 + log((n + 1) / (count + 1)), 4)
                        for word, count in df.items() if count <= max(5, int(n * 0.15))}
        self._postings = {word: frozenset(ids) for word, ids in postings.items()
                          if word in self._weight}

    def suggest(self, sources: Iterable[EvidenceText], *, limit: int = 8,
                max_related_edges: int = 12) -> dict:
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit must be 1..20")
        if type(max_related_edges) is not int or not 0 <= max_related_edges <= 30:
            raise ValueError("max_related_edges must be 0..30")
        records = tuple(sources)
        if len(records) > 64:
            raise ValueError("At most 64 retrieval sources are allowed")
        if sum(len(s.text) for s in records if isinstance(s, EvidenceText)) > 131072:
            raise ValueError("Aggregate source text limit is 131072 characters")
        if not all(isinstance(s, EvidenceText) for s in records):
            raise ValueError("Retrieval sources must be EvidenceText instances")
        if len({s.id for s in records}) != len(records):
            raise ValueError("Duplicate retrieval source identifier")
        prepared = tuple((source, relevant_terms(source.text) & self._weight.keys(),
                          tuple(w for w in terms(source.text) if w not in _STOP))
                         for source in records)
        candidate_ids: set[int] = set()
        for _, source_words, _ in prepared:
            for word in source_words:
                candidate_ids.update(self._postings.get(word, ()))
        scored = []
        for cid in candidate_ids:
            names, desc, phrases = self._index[cid]
            best = None
            for source, source_words, source_sequence in prepared:
                name_overlap = names & source_words
                summary_overlap = desc & source_words
                whole_label = any(
                    phrase and any(source_sequence[i:i + len(phrase)] == phrase
                                   for i in range(len(source_sequence) - len(phrase) + 1))
                    for phrase in phrases
                )
                # Do not promote one vague token in a multiword topic into a
                # purportedly relevant social explanation. No forced match.
                title_supported = whole_label or (len(name_overlap) >= 2) or (
                    len(names) == 1 and len(name_overlap) == 1
                )
                if not title_supported and len(summary_overlap) < 3:
                    continue
                score = (8 if whole_label else 0)
                score += sum(2 * self._weight[w] for w in name_overlap)
                score += sum(self._weight[w] / 4 for w in summary_overlap)
                # A ranking value is lexical relevance, not credibility or truth.
                match_terms = sorted(name_overlap | summary_overlap)
                candidate = (score, source.id, source, match_terms, bool(whole_label))
                if best is None or score > best[0] or (score == best[0] and source.id < best[1]):
                    best = candidate
            if best is not None:
                scored.append((cid, best))
        scored.sort(key=lambda item: (-item[1][0], item[0]))
        chosen = scored[:limit]
        suggested = []
        for cid, (score, _, source, matched, whole_label) in chosen:
            concept = self.graph.concepts[cid]
            suggested.append({
                "concept_id": cid,
                "label": concept.label,
                "record_status": concept.status,
                "lexical_score_not_confidence": round(score, 4),
                "matched_terms": matched,
                "whole_label_match": whole_label,
                "source": source.descriptor(),
                "interpretation_status": "topic_to_consider_not_a_claim_about_a_person",
            })
        related = []
        primary_ids = {item["concept_id"] for item in suggested[:3]}
        if max_related_edges:
            for edge in sorted(self.graph.edges, key=lambda e: (e.source, e.target, e.type)):
                if edge.source not in primary_ids and edge.target not in primary_ids:
                    continue
                adjacent_id = edge.target if edge.source in primary_ids else edge.source
                related.append({
                    "source_concept_id": edge.source,
                    "target_concept_id": edge.target,
                    "target_label": self.graph.concepts[adjacent_id].label,
                    "relation_type": edge.type,
                    "rationale": edge.rationale,
                    "provenance": edge.provenance,
                    "assertion_status": "unverified_relationship_hypothesis_not_an_inference",
                })
                if len(related) >= max_related_edges:
                    break
        return {
            "status": "candidate_topics_only" if suggested else "no_defensible_lexical_matches",
            "method": "bounded_lexical_retrieval_not_person_classification",
            "source_count": len(records),
            "topics": suggested,
            "related_relationship_hypotheses": related,
            "limitations": [
                "A lexical match does not establish that a topic applies to the speaker or anybody else.",
                "No retrieved societal claim or relationship has been independently verified by this step.",
                "Model-suggested context and unsupported inferred traits cannot create retrieval evidence.",
                "Related edges are unreviewed hypotheses, not proof of causation or behavioral traits.",
                "No human feeling, intention, or actual effect is inferred from these topics.",
            ],
        }
