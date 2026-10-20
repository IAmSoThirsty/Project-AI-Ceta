"""Read-only CETA source checkpoint; restores only into a new fixture directory.

Live profiles, ignored model assets, keys and environments stay in place. Their
locations are recorded, never copied into a source archive. No Git checkout,
reset, clean, stash, fetch or configuration mutation is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1")
    result = subprocess.run(["git", "-C", str(root), *args], env=env,
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed ({result.returncode}): "
                           + result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def ordinary_file(root: Path, name: str) -> Path:
    rel = PurePosixPath(name)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe source path")
    if any("\\" in part or ":" in part or part == ".git" for part in rel.parts):
        raise ValueError("unsafe source path")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink() or current.is_junction():
            raise ValueError("reparse source requires separate preservation")
    current.resolve().relative_to(root.resolve())
    if not current.is_file():
        raise ValueError("source is not a regular file")
    return current


def inventory(root: Path) -> dict:
    actual = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if actual != root.resolve():
        raise ValueError("requested root is not the exact Git root")
    names = set(git(root, "ls-files", "-z", "--cached", "--others",
                    "--exclude-standard").decode("utf-8").split("\0")) - {""}
    files, sensitive, absent = [], [], []
    for name in sorted(names):
        path = root / name
        if path.is_symlink() or path.is_junction():
            raise ValueError("reparse source requires separate preservation")
        if not path.exists():
            absent.append(name)
            continue
        path = ordinary_file(root, name)
        if path.suffix.lower() in SENSITIVE_SUFFIXES:
            sensitive.append({"path": name, "contents": "NOT_READ"})
            continue
        data = path.read_bytes()
        files.append({"path": name, "bytes": len(data), "sha256": digest(data)})
    return {
        "root": str(actual),
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "branch": git(root, "branch", "--show-current").decode().strip(),
        "status": git(root, "status", "--porcelain=v1", "-uall").decode(),
        "refs": git(root, "show-ref").decode(),
        "worktrees": git(root, "worktree", "list", "--porcelain").decode(),
        "files": files, "absent_tracked_paths": absent,
        "sensitive_locations_not_read": sensitive,
        "ignored_locations_not_copied": git(root, "ls-files", "--others", "--ignored",
                                            "--exclude-standard", "--directory").decode().splitlines(),
    }


def verify_restore(archive: Path, expected: dict, destination: Path) -> dict:
    # Refuse overwrite even if the directory is empty: every restore is new.
    if destination.exists() or destination.is_symlink() or destination.is_junction():
        raise ValueError("restore destination already exists")
    destination.parent.resolve(strict=True)
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        expected_files = {item["path"]: item for item in expected["files"]}
        if len(members) != len(expected_files) or set(source.namelist()) != set(expected_files):
            raise ValueError("archive members do not match source inventory")
        # Validate every member before creating any output.
        for member in members:
            rel = PurePosixPath(member.filename)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise ValueError("unsafe archive member")
            if any("\\" in part or ":" in part or part == ".git" for part in rel.parts):
                raise ValueError("unsafe archive member")
            expected_member = expected_files[member.filename]
            if member.file_size != expected_member["bytes"]:
                raise ValueError("archive member size changed")
            if digest(source.read(member)) != expected_member["sha256"]:
                raise ValueError("archive member hash changed")
        destination.mkdir()
        for member in members:
            path = destination.joinpath(*PurePosixPath(member.filename).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(source.read(member))
        for name, item in expected_files.items():
            data = ordinary_file(destination, name).read_bytes()
            if len(data) != item["bytes"] or digest(data) != item["sha256"]:
                raise ValueError("restored source differs")
    return {"result": "PASS", "files": len(expected_files),
            "restoration_root": str(destination.resolve()),
            "qualification": "SOURCE_BYTES_ONLY_NOT_LIVE_PROFILE_OR_RUNTIME"}


def checkpoint(root: Path, destination: Path) -> dict:
    root = root.resolve(strict=True)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink() or destination.is_junction():
        raise ValueError("checkpoint destination already exists")
    destination.parent.resolve(strict=True)
    if destination.is_relative_to(root):
        raise ValueError("checkpoint must be outside the source worktree")
    before = inventory(root)
    if before["sensitive_locations_not_read"]:
        raise ValueError("source contains sensitive paths; separate protected checkpoint required")
    destination.mkdir()
    archive = destination / "working-source.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for item in before["files"]:
            data = ordinary_file(root, item["path"]).read_bytes()
            if len(data) != item["bytes"] or digest(data) != item["sha256"]:
                raise RuntimeError("source changed during archive creation")
            output.writestr(item["path"], data)
    # Preserve both working and staged diffs, including binary changes.
    for filename, args in (("working.patch", ("diff", "--binary", "--full-index")),
                           ("staged.patch", ("diff", "--cached", "--binary", "--full-index"))):
        (destination / filename).write_bytes(git(root, *args))
    bundle = destination / "references.bundle"
    git(root, "bundle", "create", str(bundle), "--all")
    bundle_verification = git(root, "bundle", "verify", str(bundle)).decode()
    after = inventory(root)
    if before != after:
        raise RuntimeError("source/Git state changed during checkpoint; checkpoint invalid")
    (destination / "inventory.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
    restored = verify_restore(archive, before, destination / "restoration-proof")
    final = inventory(root)
    if final != before:
        raise RuntimeError("source/Git state changed during restoration; checkpoint invalid")
    evidence = {
        "schema_version": "1", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS", "root": str(root), "head": before["head"],
        "branch": before["branch"], "status": before["status"],
        "source_files": len(before["files"]), "source_unchanged": True,
        "artifacts": [{"path": name, "sha256": digest((destination / name).read_bytes())}
                      for name in ("working-source.zip", "references.bundle", "working.patch",
                                   "staged.patch", "inventory.json")],
        "bundle_verification": bundle_verification, "restoration": restored,
        "live_profile_contents": "NOT_READ_OR_COPIED",
        "ignored_assets": "PRESERVED_IN_PLACE_NOT_COPIED",
        "reflog_only_objects": "PRESERVED_IN_PLACE_NOT_INCLUDED_IN_REF_BUNDLE",
        "runtime_qualification": "NOT_RUN",
    }
    (destination / "checkpoint.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        evidence = checkpoint(args.root, args.destination)
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
