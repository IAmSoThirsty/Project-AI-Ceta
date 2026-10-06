"""Restore the preserved reference PDF from two ordinary Git blobs.

Only Python's standard library is required. Existing output is never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

LIMIT = 100 * 1024 * 1024
BLOCK = 1024 * 1024


def digest(path: Path) -> tuple[int, str]:
    count = 0
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(BLOCK):
            count += len(block)
            sha.update(block)
    return count, sha.hexdigest()


def load_manifest(path: Path) -> dict:
    if path.stat().st_size > 65536:
        raise ValueError("Manifest exceeds 64 KiB")
    data = json.loads(path.read_bytes())
    if data.get("schema") != "ceta.reference-pdf-parts.v1":
        raise ValueError("Unsupported manifest schema")
    parts = data.get("parts")
    if not isinstance(parts, list) or len(parts) != 2:
        raise ValueError("Exactly two parts are required")
    names = set()
    for entry in [data, *parts]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid manifest entry")
        name = entry.get("file")
        if not isinstance(name, str) or not name or name in (".", "..") or any(c in name for c in "/\\:"):
            raise ValueError("File names must be local base names")
        if type(entry.get("bytes")) is not int or entry["bytes"] <= 0:
            raise ValueError("Invalid file size")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("Invalid SHA256")
    for entry in parts:
        if entry["file"] in names or entry["file"] == data["file"]:
            raise ValueError("Part names must be distinct")
        names.add(entry["file"])
        if entry["bytes"] >= LIMIT:
            raise ValueError("Part exceeds the ordinary Git size limit")
    if sum(entry["bytes"] for entry in parts) != data["bytes"]:
        raise ValueError("Combined size does not match the manifest")
    return data


def assemble(manifest_path: Path, output: Path) -> str:
    data = load_manifest(manifest_path)
    if output.is_symlink():
        raise FileExistsError("Refusing a symbolic-link output")
    if output.exists():
        if output.is_file() and digest(output) == (data["bytes"], data["sha256"]):
            return "ALREADY_VERIFIED"
        raise FileExistsError("Existing output differs; it was preserved")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".ceta-pdf-", suffix=".tmp", dir=output.parent, delete=False) as target:
            temporary = Path(target.name)
            combined = hashlib.sha256()
            combined_size = 0
            for entry in data["parts"]:
                part = manifest_path.parent / entry["file"]
                if part.is_symlink() or not part.is_file() or part.stat().st_size != entry["bytes"]:
                    raise ValueError("Missing, linked or incorrectly sized part: " + entry["file"])
                sha = hashlib.sha256()
                count = 0
                with part.open("rb") as source:
                    while block := source.read(min(BLOCK, entry["bytes"] + 1 - count)):
                        count += len(block)
                        if count > entry["bytes"]:
                            raise ValueError("Part grew during reading")
                        sha.update(block)
                        combined.update(block)
                        combined_size += len(block)
                        target.write(block)
                if (count, sha.hexdigest()) != (entry["bytes"], entry["sha256"]):
                    raise ValueError("Part checksum mismatch: " + entry["file"])
            if (combined_size, combined.hexdigest()) != (data["bytes"], data["sha256"]):
                raise ValueError("Reassembled PDF checksum mismatch")
            target.flush()
            os.fsync(target.fileno())
        # Same-directory hard linking publishes atomically without replacing a
        # destination that appeared during verification, on Windows and POSIX.
        os.link(temporary, output)
        return "REASSEMBLED_AND_VERIFIED"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=root / "assets/reference-parts/codex-foundations.parts.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_manifest(args.manifest)
    output = args.output or root / "sources/codex" / data["file"]
    status = assemble(args.manifest, output)
    print(json.dumps({"status": status, "output": str(output), "bytes": data["bytes"], "sha256": data["sha256"]}))


if __name__ == "__main__":
    main()
