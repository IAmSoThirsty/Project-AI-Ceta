"""Strict offline concept and relationship graph with explicit provenance."""

from __future__ import annotations

import json
import re
from collections import Counter
from importlib.resources import files
from pathlib import Path
from typing import Iterable

from .models import Concept, Edge

TOKEN = re.compile(r"[\w'-]+", re.UNICODE)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{lineno}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected object at {path}:{lineno}")
            rows.append(value)
    return rows


def _tokens(value: str) -> set[str]:
    return set(TOKEN.findall(value.casefold()))


class KnowledgeGraph:
    def __init__(self, concepts: Iterable[Concept], edges: Iterable[Edge] = ()) -> None:
        self.concepts: dict[int, Concept] = {}
        self.edges: list[Edge] = list(edges)
        for concept in concepts:
            concept.validate()
            if concept.id in self.concepts:
                raise ValueError(f"Duplicate concept ID: {concept.id}")
            self.concepts[concept.id] = concept
        seen = set()
        for edge in self.edges:
            if edge.source not in self.concepts or edge.target not in self.concepts:
                raise ValueError(f"Dangling edge: {edge.source} -> {edge.target}")
            identity = edge.source, edge.target, edge.type
            if identity in seen:
                raise ValueError(f"Duplicate edge: {identity}")
            seen.add(identity)

    @classmethod
    def canonical(cls) -> KnowledgeGraph:
        """Load the one authoritative, compiled 2,000-record corpus."""
        resources = files("societal_reasoning").joinpath("resources")
        with resources.joinpath("concepts.full.jsonl").open(encoding="utf-8") as source:
            concepts = [Concept.from_dict(json.loads(line)) for line in source if line.strip()]
        ids = {item.id for item in concepts}
        if len(concepts) != 2000 or ids != set(range(1, 2001)):
            raise ValueError("Canonical 2000-entry inventory is incomplete or duplicated")
        with resources.joinpath("relationships.starter.jsonl").open(encoding="utf-8") as source:
            edges = [Edge.from_dict(json.loads(line)) for line in source if line.strip()]
        return cls(concepts, edges)

    @classmethod
    def starter(cls) -> KnowledgeGraph:
        """Backward-compatible API name; loads the full canonical inventory."""
        return cls.canonical()

    @classmethod
    def from_files(cls, concepts_path: str | Path, edges_path: str | Path | None = None) -> KnowledgeGraph:
        concepts = [Concept.from_dict(row) for row in read_jsonl(Path(concepts_path))]
        edges = [Edge.from_dict(row) for row in read_jsonl(Path(edges_path))] if edges_path else []
        return cls(concepts, edges)

    def get(self, concept_id: int) -> Concept | None:
        return self.concepts.get(concept_id)

    def search(self, query: str, limit: int = 10) -> list[Concept]:
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        tokens = _tokens(query)
        if not tokens:
            return []
        scored = []
        for concept in self.concepts.values():
            names = _tokens(" ".join((concept.label, *concept.aliases)))
            desc = _tokens(concept.summary)
            overlap = tokens & names
            score = 4 * len(overlap) + len(tokens & desc)
            if query.strip().casefold() == concept.label.casefold():
                score += 10
            if score > 0:
                scored.append((-score, concept.id, concept))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [row[2] for row in scored[:limit]]

    def neighbors(self, concept_id: int, *, depth: int = 1, limit: int = 100) -> list[dict]:
        if concept_id not in self.concepts:
            raise KeyError(f"Unknown concept {concept_id}")
        if not 0 <= depth <= 4 or not 1 <= limit <= 10000:
            raise ValueError("depth must be 0-4 and limit must be 1-10000")
        visited = {concept_id}
        frontier = {concept_id}
        results: list[dict] = []
        for hop in range(1, depth + 1):
            new_frontier: set[int] = set()
            for edge in self.edges:
                if edge.source in frontier and edge.target not in visited and edge.target not in new_frontier:
                    other = edge.target
                    direction = "outgoing"
                elif edge.target in frontier and edge.source not in visited and edge.source not in new_frontier:
                    other = edge.source
                    direction = "incoming"
                else:
                    continue
                results.append({"hop": hop, "concept": self.concepts[other].to_dict(), "via": edge.to_dict(), "direction": direction})
                new_frontier.add(other)
                if len(results) >= limit:
                    return results
            visited |= new_frontier
            frontier = new_frontier
            if not frontier:
                break
        return results

    def audit(self) -> dict:
        status_counts = Counter(c.status for c in self.concepts.values())
        volumes = Counter(str(c.source.get("volume", "unknown")) for c in self.concepts.values())
        edge_counts = Counter(e.type for e in self.edges)
        identifiers = sorted(self.concepts)
        missing_between = [n for n in range(identifiers[0], identifiers[-1] + 1) if n not in self.concepts] if identifiers else []
        return {
            "concept_count": len(self.concepts),
            "relationship_count": len(self.edges),
            "concept_range": [identifiers[0], identifiers[-1]] if identifiers else None,
            "unpopulated_ids_within_range_count": len(missing_between),
            "unpopulated_ids_sample": missing_between[:20],
            "status_counts": dict(sorted(status_counts.items())),
            "volume_counts": dict(sorted(volumes.items())),
            "relationship_types": dict(sorted(edge_counts.items())),
            "independently_verified_count": status_counts.get("independently_verified", 0),
            "original_two_volume_inventory_target": 2000,
            "original_inventory_ids_not_present": len(set(range(1, 2001)) - set(self.concepts)),
        }
