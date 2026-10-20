"""Strict data boundaries for concepts, relationships, evidence, and scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Status = Literal["seed_summary_pending_transcription", "source_transcribed", "independently_verified"]
EvidenceOrigin = Literal[
    "direct_observation", "user_report", "quoted_material", "external_record", "interpretation"
]
EDGE_TYPES = frozenset({
    "enables", "depends_on", "reinforces", "constrains", "contradicts",
    "contextualizes", "may_cause", "mitigates", "is_a", "influences",
})
ORIGINS = frozenset({
    "direct_observation", "user_report", "quoted_material", "external_record", "interpretation"
})
STATUSES = frozenset({
    "seed_summary_pending_transcription", "source_transcribed", "independently_verified"
})


def _check_unknown(data: dict[str, Any], allowed: set[str], kind: str) -> None:
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"Unexpected {kind} fields: {sorted(extra)}")


@dataclass(frozen=True, slots=True)
class Concept:
    id: int
    label: str
    summary: str
    domains: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    original_text: str | None = None
    source: dict[str, Any] = field(default_factory=dict)
    status: Status = "seed_summary_pending_transcription"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Concept:
        _check_unknown(data, {"id", "label", "summary", "domains", "aliases", "original_text", "source", "status"}, "concept")
        item = cls(
            id=data["id"], label=data["label"], summary=data["summary"],
            domains=tuple(data.get("domains", [])),
            aliases=tuple(data.get("aliases", [])),
            original_text=data.get("original_text"),
            source=dict(data.get("source", {})),
            status=data.get("status", "seed_summary_pending_transcription"),
        )
        item.validate()
        return item

    def validate(self) -> None:
        if type(self.id) is not int or not 1 <= self.id <= 200000:
            raise ValueError(f"Invalid concept ID: {self.id!r}")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError(f"Blank label for {self.id}")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError(f"Blank summary for {self.id}")
        if self.status not in STATUSES:
            raise ValueError(f"Unrecognized status for {self.id}: {self.status}")
        if not isinstance(self.source, dict) or not self.source:
            raise ValueError(f"Missing provenance for concept {self.id}")
        if not all(isinstance(x, str) and x.strip() for x in (*self.domains, *self.aliases)):
            raise ValueError(f"Invalid domain or alias in {self.id}")
        if self.status == "source_transcribed" and not self.original_text:
            raise ValueError(f"Transcribed concept {self.id} has no preserved source text")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Edge:
    source: int
    target: int
    type: str
    rationale: str
    provenance: str = "curator_hypothesis"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        _check_unknown(data, {"source", "target", "type", "rationale", "provenance"}, "edge")
        edge = cls(**data)
        if type(edge.source) is not int or type(edge.target) is not int:
            raise ValueError("Relationship endpoints must be integer concept IDs")
        if edge.type not in EDGE_TYPES:
            raise ValueError(f"Unsupported relationship type: {edge.type}")
        if not edge.rationale.strip() or not edge.provenance.strip():
            raise ValueError("Relationships require rationale and provenance")
        return edge

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    statement: str
    origin: EvidenceOrigin
    cues: tuple[str, ...] = ()
    source_ref: str | None = None

    def __post_init__(self) -> None:
        # Direct construction is a public API path, not a bypass of from_dict.
        if self.origin not in ORIGINS or not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Evidence requires a recognized origin and ID")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("Evidence statement must not be empty")
        if (not isinstance(self.cues, tuple) or
                any(not isinstance(cue, str) or not cue.strip() for cue in self.cues)):
            raise ValueError("Evidence cues must be a tuple of nonempty text")
        if self.source_ref is not None and (not isinstance(self.source_ref, str) or not self.source_ref.strip()):
            raise ValueError("Evidence source reference must be nonempty or null")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        _check_unknown(data, {"id", "statement", "origin", "cues", "source_ref"}, "evidence")
        evidence = cls(
            id=data["id"], statement=data["statement"], origin=data["origin"],
            cues=tuple(data.get("cues", [])), source_ref=data.get("source_ref"),
        )
        if evidence.origin not in ORIGINS or not evidence.id.strip() or not evidence.statement.strip():
            raise ValueError("Evidence requires recognized origin, ID, and nonempty statement")
        if not all(isinstance(cue, str) and cue.strip() for cue in evidence.cues):
            raise ValueError("Invalid evidence cue")
        return evidence

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MaterialTerm:
    term: str
    sense_id: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> MaterialTerm:
        if not isinstance(row, dict):
            raise ValueError("Material term must be a JSON object")
        _check_unknown(row, {"term", "sense_id"}, "material term")
        term = row.get("term")
        sense_id = row.get("sense_id")
        if not isinstance(term, str) or not term.strip():
            raise ValueError("Material term requires a nonempty word")
        if sense_id is not None and (not isinstance(sense_id, str) or not sense_id.strip()):
            raise ValueError("Invalid material term sense_id")
        return cls(term=term.strip().casefold(), sense_id=sense_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    question: str
    evidence: tuple[Evidence, ...]
    context: dict[str, str] = field(default_factory=dict)
    unknowns: tuple[str, ...] = ()
    material_terms: tuple[MaterialTerm, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        _check_unknown(data, {"id", "question", "evidence", "context", "unknowns", "material_terms"}, "scenario")
        terms = data.get("material_terms", [])
        if not isinstance(terms, (list, tuple)):
            raise ValueError("material_terms must be an array")
        scenario = cls(
            id=data["id"], question=data["question"],
            evidence=tuple(Evidence.from_dict(e) for e in data["evidence"]),
            context=dict(data.get("context", {})),
            unknowns=tuple(data.get("unknowns", [])),
            material_terms=tuple(MaterialTerm.from_dict(row) for row in terms),
        )
        if not scenario.id.strip() or not scenario.question.strip():
            raise ValueError("Scenario ID and question are required")
        if len({e.id for e in scenario.evidence}) != len(scenario.evidence):
            raise ValueError("Duplicate evidence IDs")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in scenario.context.items()):
            raise ValueError("Context fields must be descriptive string pairs")
        if not all(isinstance(x, str) and x.strip() for x in scenario.unknowns):
            raise ValueError("Invalid unknown")
        if len({x.term for x in scenario.material_terms}) != len(scenario.material_terms):
            raise ValueError("Duplicate material term")
        return scenario

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
