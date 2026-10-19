"""Ingest Markdown numbered societal inventory without rewriting source claims."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from .models import Concept

ENTRY = re.compile(r"^\s*(\d{1,6})\.\s+\*\*(.+?)\*\*\s*(.*)\s*$")
HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")


class InventoryImportError(ValueError):
    pass


def import_markdown(
    markdown: str,
    *,
    volume: int,
    source_title: str,
    expected_start: int | None = None,
    expected_end: int | None = None,
    require_contiguous: bool = False,
) -> tuple[list[Concept], dict]:
    if type(volume) is not int or volume < 1 or not source_title.strip():
        raise InventoryImportError("Volume and source title must be valid")
    entries: list[Concept] = []
    source_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    encountered: set[int] = set()
    current_section = "Unsectioned"
    pending: dict | None = None

    def flush() -> None:
        nonlocal pending
        if pending is None:
            return
        original = "\n".join(pending["raw_lines"]).rstrip()
        description = " ".join(part.strip() for part in pending["lines"] if part.strip())
        label = pending["label"].strip().rstrip(":").strip()
        # First line contains the entire original text after the bold label.
        if not description:
            raise InventoryImportError(f"No description for entry {pending['id']}")
        data = {
            "id": pending["id"], "label": label, "summary": description,
            "domains": [pending["section"]], "aliases": [],
            "original_text": original,
            "status": "source_transcribed",
            "source": {"kind": "source_document", "title": source_title,
                       "volume": volume, "entry_id": pending["id"],
                       "line_start": pending["line"],
                       "source_sha256": source_sha256,
                       "entry_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest()},
        }
        entries.append(Concept.from_dict(data))
        pending = None

    for lineno, line in enumerate(markdown.splitlines(), 1):
        match = ENTRY.match(line)
        if match:
            flush()
            identifier = int(match.group(1))
            if identifier in encountered:
                raise InventoryImportError(f"Duplicate inventory entry {identifier} at line {lineno}")
            if expected_start is not None and identifier < expected_start:
                raise InventoryImportError(f"Entry {identifier} is below expected volume range")
            if expected_end is not None and identifier > expected_end:
                raise InventoryImportError(f"Entry {identifier} is above expected volume range")
            encountered.add(identifier)
            pending = {
                "id": identifier, "label": match.group(2), "section": current_section,
                "line": lineno, "lines": [match.group(3).strip()] if match.group(3).strip() else [],
                "raw_lines": [line],
            }
        elif HEADING.match(line):
            flush()
            current_section = HEADING.match(line).group(1).strip()
        elif pending is not None:
            # Paragraphs and new unnumbered lists are boundaries; indented wrapped
            # description text is preserved. No auto-generated replacement claims.
            if not line.strip() or re.match(r"^\s*[-*]\s+", line):
                flush()
            else:
                pending["lines"].append(line.rstrip())
                pending["raw_lines"].append(line)
    flush()
    ids = sorted(encountered)
    missing = [i for i in range(expected_start, expected_end + 1) if i not in encountered] if expected_start is not None and expected_end is not None else []
    if require_contiguous and missing:
        raise InventoryImportError(f"Missing {len(missing)} IDs; first missing: {missing[:12]}")
    report = {
        "volume": volume, "source_title": source_title, "source_sha256": source_sha256, "imported": len(entries),
        "range": [ids[0], ids[-1]] if ids else None,
        "expected_range": [expected_start, expected_end] if expected_start is not None and expected_end is not None else None,
        "missing_expected_ids": missing,
        "duplicate_ids": [],
        "verification_status": "source_transcribed_not_independently_verified",
    }
    return entries, report


def write_jsonl(concepts: list[Concept], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for entry in sorted(concepts, key=lambda item: item.id):
            stream.write(json.dumps(entry.to_dict(), sort_keys=True, ensure_ascii=False) + "\n")
