"""Verify supplied source bytes and coverage without promoting conformance.

Only registered paths below the caller's project root are opened. This is an
engineering integrity checker, not an OS sandbox or an authority issuer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_MANIFEST_SHA256 = "ea6d515e6437d0933b58e178ac5d9b747b71aba5bcfd54ff70dd463c47bda311"
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, strict_loads


def safe_path(root: Path, relative: str) -> Path:
    if type(relative) is not str or not relative or "\\" in relative or ":" in relative:
        raise ContractError("UNSAFE_SOURCE_PATH")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts:
        raise ContractError("UNSAFE_SOURCE_PATH")
    current = root
    for part in parts.parts:
        current = current / part
        if current.is_symlink() or current.is_junction():
            raise ContractError("SOURCE_LINK_NOT_ALLOWED")
    if not current.resolve().is_relative_to(root.resolve()):
        raise ContractError("SOURCE_PATH_ESCAPE")
    return current


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(root: Path, paths: list[str]) -> dict[str, str]:
    return {rel: digest(safe_path(root, rel)) for rel in paths}


def require_unchanged(before: dict[str, str], after: dict[str, str]) -> None:
    if before != after:
        raise ContractError("SOURCE_CHANGED_DURING_VERIFICATION")


def require_read_inputs_unchanged(wires: dict[str, bytes], before: dict[str, str]) -> None:
    """Bind parsed metadata to the first snapshot, including the earlier read."""
    if any(before.get(path) != hashlib.sha256(wire).hexdigest() for path, wire in wires.items()):
        raise ContractError("SOURCE_CHANGED_DURING_VERIFICATION")


def require_summary_consistency(document: dict) -> dict[str, int]:
    """Reject cached counts that disagree with the detailed applicability rows."""
    rows = document["sections"]
    if any(row["applicability"] not in {"DIRECT", "SUPPORTING", "NOT_APPLICABLE", "UNRESOLVED"}
           for row in rows):
        raise ContractError("UNKNOWN_APPLICABILITY")
    total = len(rows)
    pending = sum(row["applicability"] == "UNRESOLVED" for row in rows)
    assessed = total - pending
    expected = f"{total}_SOURCE_SECTIONS_PRESENT_{assessed}_APPLICABILITY_ASSESSED_{pending}_PENDING"
    original_pending = f"{total}_SOURCE_SECTIONS_PRESENT_APPLICABILITY_PENDING"
    if document.get("coverage_state") != expected and not (
            pending == total and document.get("coverage_state") == original_pending):
        raise ContractError("SOURCE_COVERAGE_SUMMARY_MISMATCH")
    return {"total": total, "assessed": assessed, "unresolved": pending}


def check_ids(rows: list[dict], key: str, expected: set, code: str) -> None:
    values = [r[key] for r in rows]
    if len(values) != len(expected) or set(values) != expected:
        raise ContractError(code)


def require_original_bindings(current: list[dict], baseline: list[dict], key: str) -> None:
    originals = {row[key]: row for row in baseline}
    if len(originals) != len(baseline):
        raise ContractError("DUPLICATE_ORIGINAL_IDENTIFIER")
    for row in current:
        original = originals.get(row[key])
        if original is None:
            raise ContractError("UNSUPPORTED_ORIGINAL_IDENTIFIER")
        bound_fields = {"path", "sha256", "bytes", "volume", "volume_pdf", "section", "pages", "lifecycle_range"}
        bound_fields.update(field for field in original if field.startswith("original_"))
        if any(row.get(field) != original.get(field) for field in bound_fields):
            raise ContractError("ORIGINAL_IDENTIFIER_REBOUND")


def preserved_registry(root: Path, original: dict, path: str) -> dict:
    restored = safe_path(root, ".local-build-cache/restoration-proof/" + path)
    wire = restored.read_bytes()
    row = original[path]
    if len(wire) != row["bytes"] or hashlib.sha256(wire).hexdigest() != row["sha256"]:
        raise ContractError("PRESERVED_REGISTRY_CHANGED")
    return strict_loads(wire)


def verify(root: Path) -> dict:
    root = root.resolve(strict=True)
    errors: list[str] = []
    coverage = []
    verified_files = 0
    input_hashes: dict[str, str] = {}
    checker_hash = None
    inputs_unchanged = None
    try:
        checker_path = Path(__file__).resolve()
        checker_hash = digest(checker_path)
        input_paths = ("PACKAGE_MANIFEST.json", "standards/volume_register.json",
                       "standards/lifecycle_coverage.json", "acceptance/scenarios.json",
                       "requirements/requirements.json")
        input_wires = {path: safe_path(root, path).read_bytes() for path in input_paths}
        input_hashes = {path: hashlib.sha256(wire).hexdigest() for path, wire in input_wires.items()}
        manifest_wire = input_wires["PACKAGE_MANIFEST.json"]
        if hashlib.sha256(manifest_wire).hexdigest() != ORIGINAL_MANIFEST_SHA256:
            raise ContractError("ORIGINAL_MANIFEST_CHANGED")
        manifest = strict_loads(manifest_wire)
        volumes = strict_loads(input_wires["standards/volume_register.json"])["volumes"]
        coverage_document = strict_loads(input_wires["standards/lifecycle_coverage.json"])
        coverage = coverage_document["sections"]
        cases = strict_loads(input_wires["acceptance/scenarios.json"])["scenarios"]
        requirements = strict_loads(input_wires["requirements/requirements.json"])["requirements"]
        check_ids(volumes, "volume", set(range(1, 21)), "VOLUME_SET_INCOMPLETE")
        check_ids(coverage, "section", {f"{n:03}" for n in range(1, 407)}, "SECTION_SET_INCOMPLETE")
        check_ids(cases, "id", {f"B{n:03}" for n in range(1, 129)}, "ACCEPTANCE_SET_INCOMPLETE")
        requirement_ids = {r["id"] for r in requirements}
        rows = manifest["files"]
        row_paths = [r["path"] for r in rows]
        if len(row_paths) != len(set(row_paths)):
            raise ContractError("DUPLICATE_MANIFEST_PATH")
        original = {r["path"]: r for r in rows}
        require_original_bindings(coverage, preserved_registry(root, original,
                                  "standards/lifecycle_coverage.json")["sections"], "section")
        require_original_bindings(volumes, preserved_registry(root, original,
                                  "standards/volume_register.json")["volumes"], "volume")
        immutable = [r for r in rows if r["path"].startswith(("sources/", "acceptance/cases/"))]
        watch = [r["path"] for r in immutable]
        watch += ["PACKAGE_MANIFEST.json", "standards/volume_register.json", "standards/lifecycle_coverage.json",
                  "acceptance/scenarios.json", "requirements/requirements.json"]
        before = snapshot(root, watch)
        require_read_inputs_unchanged(input_wires, before)
        for row in immutable:
            path = safe_path(root, row["path"])
            if path.stat().st_size != row["bytes"] or before[row["path"]] != row["sha256"]:
                errors.append("ORIGINAL_BYTES_CHANGED:" + row["path"])
            else:
                verified_files += 1
        for row in volumes + coverage:
            registered = original.get(row["path"])
            if registered is None or (row["bytes"], row["sha256"]) != (registered["bytes"], registered["sha256"]):
                errors.append("UNSUPPORTED_SOURCE_IDENTITY:" + row["path"])
            if not safe_path(root, row["path"]).is_file():
                errors.append("SOURCE_MISSING:" + row["path"])
        for row in coverage:
            if row["applicability"] not in {"DIRECT", "SUPPORTING", "NOT_APPLICABLE", "UNRESOLVED"}:
                errors.append("UNKNOWN_APPLICABILITY:" + row["section"])
            if not set(row.get("requirement_ids", [])).issubset(requirement_ids):
                errors.append("UNKNOWN_REQUIREMENT_REFERENCE:" + row["section"])
            if row["applicability"] != "UNRESOLVED" and not row.get("decision_reason"):
                errors.append("APPLICABILITY_REASON_MISSING:" + row["section"])
            # Presence and a reason alone never close the substantive review gate.
            if row["applicability"] != "UNRESOLVED" and not row.get("inspection_evidence_refs"):
                errors.append("SOURCE_INSPECTION_EVIDENCE_MISSING:" + row["section"])
        require_summary_consistency(coverage_document)
        require_unchanged(before, snapshot(root, watch))
        require_unchanged({"checker": checker_hash}, {"checker": digest(checker_path)})
        inputs_unchanged = True
    except (ContractError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    unresolved = [r["section"] for r in coverage if r.get("applicability") == "UNRESOLVED"]
    return {"scope": "SUPPLIED_SOURCE_INTEGRITY_AND_COVERAGE_ONLY",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "result": "FAIL" if errors else "PASS", "errors": errors,
            "original_files_verified": verified_files,
            "metadata_input_sha256": input_hashes, "checker_sha256": checker_hash,
            "watched_inputs_unchanged": inputs_unchanged,
            "unresolved_section_count": len(unresolved), "unresolved_sections": unresolved,
            "source_reconciliation": "OPEN" if errors or unresolved else "REVIEW_REQUIRED",
            "gate_a": "NOT_CLOSED", "runtime_qualification": "NOT_RUN"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-reconciliation", action="store_true")
    args = parser.parse_args()
    result = verify(ROOT)
    print(json.dumps(result, indent=2))
    return 1 if result["result"] != "PASS" or (args.require_reconciliation and result["unresolved_section_count"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
