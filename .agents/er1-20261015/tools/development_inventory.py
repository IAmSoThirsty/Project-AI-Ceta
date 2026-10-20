"""Reproducible source inventory; no private/cache payloads are opened."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path

PROFILE = "ceta-development-inventory-v1"
EXCLUDED_DIRECTORIES = frozenset({
    ".git", ".agents", "__pycache__", ".agents/fixtures", ".local-build-cache", ".venv",
    ".private", ".local-runtime", ".local-models", ".local-credentials", ".local-profiles",
})
EXCLUDED_FILE_GLOBS = ("*.py[cod]", "*.key", "*.pem", "*.p12", "*.pfx")
EXCLUDED_PREFIXES = ("native/canonical_reference/target/",)
WATCHED_DIRECTORIES = ("src/", "tests/contract/", "tools/", "contracts/", "native/sqlite_runtime/")
WATCHED_FILES = frozenset({
    "requirements-contract-tests.txt", "requirements-contract-tests.lock",
    "native/canonical_reference/Cargo.toml", "native/canonical_reference/Cargo.lock",
    "native/canonical_reference/rust-toolchain.toml", "native/canonical_reference/src/main.rs",
})


def watched(relative: str) -> bool:
    return relative in WATCHED_FILES or relative.startswith(WATCHED_DIRECTORIES)


def _walk_error(error: OSError) -> None:
    raise ValueError("INVENTORY_SCAN_FAILED") from error


def _paths(root: Path) -> list[str]:
    paths = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
        base = Path(directory)
        keep = []
        for name in sorted(names):
            path = base / name
            relative = path.relative_to(root).as_posix() + "/"
            if name.casefold() in EXCLUDED_DIRECTORIES or relative.casefold().startswith(EXCLUDED_PREFIXES):
                continue
            if path.is_symlink() or path.is_junction():
                raise ValueError("SOURCE_LINK_NOT_ALLOWED: " + relative)
            keep.append(name)
        names[:] = keep
        for name in sorted(files):
            if any(fnmatch.fnmatchcase(name.lower(), pattern) for pattern in EXCLUDED_FILE_GLOBS):
                continue
            path = base / name
            if path.is_symlink() or path.is_junction():
                raise ValueError("SOURCE_LINK_NOT_ALLOWED: " + path.relative_to(root).as_posix())
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _read(root: Path, paths: list[str]) -> dict:
    result = {}
    for relative in paths:
        path = root / relative
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root):
            raise ValueError("SOURCE_LINK_NOT_ALLOWED: " + relative)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        result[relative] = {"sha256": digest.hexdigest(), "bytes": size,
                            "source_test_watched": watched(relative)}
    return result


def inventory(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("INVENTORY_ROOT_NOT_DIRECTORY")
    paths = _paths(root)
    first = _read(root, paths)
    second_paths = _paths(root)
    second = _read(root, second_paths)
    if paths != second_paths or first != second:
        raise ValueError("SOURCE_CHANGED_DURING_INVENTORY")
    return {"profile": PROFILE, "root": str(root), "files": second,
            "inventory_file_count": len(second),
            "source_test_watched_count": sum(row["source_test_watched"] for row in second.values()),
            "rules": {"excluded_directory_names": sorted(EXCLUDED_DIRECTORIES),
                      "excluded_file_globs_case_insensitive": list(EXCLUDED_FILE_GLOBS),
                      "excluded_prefixes": list(EXCLUDED_PREFIXES),
                      "exclusion_case_rule": "WINDOWS_CASE_INSENSITIVE_NAMES_AND_PREFIXES",
                      "scan_errors": "REJECT_OBSERVATION_WITH_INVENTORY_SCAN_FAILED",
                      "watched_directories": list(WATCHED_DIRECTORIES),
                      "watched_files": sorted(WATCHED_FILES),
                      "links": "REJECT_UNEXCLUDED_SYMLINKS_AND_JUNCTIONS",
                      "unknown_unexcluded_files": "INCLUDE_WITH_EXACT_HASH",
                      "gitignore_interpretation": "EXPLICIT_RULES_ABOVE_NOT_AMBIENT_GIT_OR_RG_SETTINGS"},
            "claim": "SOURCE_IDENTITIES_AT_TWO_BOUNDARIES_NOT_SEMANTIC_REVIEW_OR_RUNTIME_QUALIFICATION"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = inventory(args.root)
    report["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    wire = json.dumps(report, indent=2) + "\n"
    if args.report:
        with args.report.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(wire)
        print(json.dumps({"report": str(args.report), "inventory_file_count": report["inventory_file_count"],
                          "source_test_watched_count": report["source_test_watched_count"]}))
    else:
        print(wire, end="")


if __name__ == "__main__":
    main()
