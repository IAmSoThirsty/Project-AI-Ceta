"""Merge source-transcribed inventory volumes into a canonical graph without silent loss."""

from __future__ import annotations

from pathlib import Path

from .graph import read_jsonl
from .ingest import write_jsonl
from .models import Concept


_STATUS_ORDER = {
    "seed_summary_pending_transcription": 0,
    "source_transcribed": 1,
    "independently_verified": 2,
}


def merge_concepts(groups: list[list[Concept]]) -> tuple[list[Concept], dict]:
    merged: dict[int, Concept] = {}
    upgrades = []
    for group in groups:
        for item in group:
            item.validate()
            before = merged.get(item.id)
            if before is None:
                merged[item.id] = item
                continue
            if before.label.casefold().strip() != item.label.casefold().strip():
                raise ValueError(f"Conflicting labels for inventory ID {item.id}: {before.label!r} != {item.label!r}")
            prev_quality = _STATUS_ORDER[before.status]
            new_quality = _STATUS_ORDER[item.status]
            if new_quality > prev_quality:
                merged[item.id] = item
                upgrades.append(item.id)
            elif new_quality == prev_quality and before.to_dict() != item.to_dict():
                raise ValueError(f"Competing equal-status records for ID {item.id}; manual reconciliation required")
    records = [merged[k] for k in sorted(merged)]
    return records, {
        "merged_count": len(records), "upgraded_from_lower_status_count": len(upgrades),
        "upgraded_ids": upgrades,
        "source_transcribed_count": sum(c.status == "source_transcribed" for c in records),
        "independently_verified_count": sum(c.status == "independently_verified" for c in records),
        "seed_summary_count": sum(c.status == "seed_summary_pending_transcription" for c in records),
    }


def merge_files(paths: list[Path], output: Path) -> dict:
    if len(paths) < 2:
        raise ValueError("Provide at least two files to merge")
    if output.resolve() in [p.resolve() for p in paths]:
        raise ValueError("Output path must not overwrite a source file")
    groups = [[Concept.from_dict(data) for data in read_jsonl(path)] for path in paths]
    records, report = merge_concepts(groups)
    write_jsonl(records, output)
    return {"output": str(output), **report}
