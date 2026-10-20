"""Provenance-preserving context. Facts are reports; hypotheses stay hypotheses.

A contextual difference is a *reason to reconsider*, never proof of emotion,
intention, harm, consent, or personal identity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CATEGORIES = frozenset({"audience", "setting", "relationship", "history", "channel", "power", "culture", "stakes", "chronology", "other"})
ORIGINS = frozenset({"user_report", "quoted_material", "external_record", "direct_observation", "model_hypothesis"})
POTENTIALLY_MATERIAL = CATEGORIES - {"other"}


@dataclass(frozen=True, slots=True)
class ContextFactor:
    id: str
    category: str
    value: str
    origin: str
    source_ref: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ContextFactor:
        if not isinstance(row, dict) or set(row) - {"id", "category", "value", "origin", "source_ref"}:
            raise ValueError("Unexpected context factor shape")
        for field in ("id", "category", "value", "origin"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Missing or invalid context factor {field}")
        ref = row.get("source_ref")
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            raise ValueError("Invalid context source reference")
        if row["category"] not in CATEGORIES or row["origin"] not in ORIGINS:
            raise ValueError("Unsupported context category or origin")
        if len(row["value"]) > 1024 or len(row["id"]) > 128:
            raise ValueError("Context factor resource bound exceeded")
        return cls(row["id"], row["category"], row["value"], row["origin"], ref)

    def to_dict(self) -> dict:
        return {**asdict(self), "epistemic_status": (
            "model_proposal_not_observed" if self.origin == "model_hypothesis"
            else "reported_or_recorded_not_independently_verified"
        )}


def assemble_context(raw_facts: tuple[dict, ...]) -> dict[str, Any]:
    if not isinstance(raw_facts, tuple) or len(raw_facts) > 64:
        raise ValueError("Context must be a tuple of at most 64 factors")
    facts = [ContextFactor.from_dict(item) for item in raw_facts]
    if len({x.id for x in facts}) != len(facts):
        raise ValueError("Duplicate context factor IDs")
    conflicts = []
    grouped: dict[str, set[str]] = {}
    for item in facts:
        if item.origin == "model_hypothesis":
            continue
        grouped.setdefault(item.category, set()).add(item.value.casefold())
    for category, values in grouped.items():
        if len(values) > 1:
            conflicts.append({"category": category, "different_reports": sorted(values),
                              "status": "unresolved_not_automatically_reconciled"})
    return {
        "reported_or_proposed_factors": [x.to_dict() for x in facts],
        "source_conflicts": conflicts,
        "scope": "caller_supplied_reports_and_hypotheses_not_verified_person_attributes",
    }


def compare_context(before: tuple[dict, ...], after: tuple[dict, ...]) -> dict[str, Any]:
    left = assemble_context(before)
    right = assemble_context(after)
    def grouped(facts: dict) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in facts["reported_or_proposed_factors"]:
            # Model proposals must never become the basis for asserted contextual change.
            if item["origin"] == "model_hypothesis":
                continue
            result.setdefault(item["category"], []).append(item["value"])
        return {key: sorted(set(values)) for key, values in result.items()}
    old, new = grouped(left), grouped(right)
    changed = [{"category": cat, "before": old.get(cat, []), "after": new.get(cat, []),
                "possibly_material": cat in POTENTIALLY_MATERIAL}
               for cat in sorted(set(old) | set(new)) if old.get(cat, []) != new.get(cat, [])]
    return {
        "changed_factors": changed,
        "requires_reconsideration": any(item["possibly_material"] for item in changed),
        "changed_facts_are_reported_not_verified": True,
        "cannot_infer": ["participant motive", "emotional state", "actual effect", "final interpretation"],
    }
