"""CETA preservation: complete ordinary bytes and independent Git recovery data.

Capture never checks out, resets, cleans, fetches, changes refs, or changes source
configuration. Every source, Git directory, capture target and restore target is
explicitly authorized in a JSON policy. Sensitive candidates remain pending;
pending checkpoints cannot restore. Windows reparse points are inert evidence,
not usable links. No production profile, key, or source tree is replaced.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import copy
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import stat
import subprocess
import sys
import uuid
import zipfile


SCHEMA = 1
BLOCK = 1024 * 1024
REPARSE = 0x400
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
SECRET_NAMES = {"id_rsa", "id_ed25519", "credentials", "credentials.json", "auth.json"}
PRIVATE_MARKER = re.compile(br"-----BEGIN (?:[A-Z0-9 ]* )?PRIVATE KEY-----")
OID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class PreservationError(RuntimeError):
    """An observed policy, integrity, or execution conflict."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreservationError(message)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def io_path(path: Path) -> str:
    """Use extended-length Windows I/O without changing the recorded path."""
    absolute = str(path.absolute())
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def lstat(path: Path) -> os.stat_result:
    return os.lstat(io_path(path))


def exists(path: Path) -> bool:
    try:
        lstat(path)
        return True
    except FileNotFoundError:
        return False


def reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & REPARSE)


def safe_components(path: Path, *, allow_missing: bool = False) -> Path:
    require(path.is_absolute(), f"path must be absolute: {path}")
    # Reject lexical traversal before resolving it away.
    require(".." not in path.parts, f"parent traversal is forbidden: {path}")
    value = Path(os.path.abspath(path))
    cursor = Path(value.anchor)
    missing = False
    for part in value.parts[1:]:
        cursor /= part
        if not exists(cursor):
            require(allow_missing, f"declared path is missing: {cursor}")
            missing = True
            continue
        require(not missing, f"inconsistent path ancestry: {cursor}")
        require(not reparse(lstat(cursor)), f"reparse path component is forbidden: {cursor}")
    return value


def same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([os.path.normcase(str(path)), os.path.normcase(str(root))]) == os.path.normcase(str(root))
    except ValueError:
        return False


def relative_name(name: str) -> PurePosixPath:
    require(isinstance(name, str) and name != "", "empty or non-string relative path")
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and str(rel) == name and ".." not in rel.parts,
            f"unsafe relative path: {name!r}")
    for part in rel.parts:
        require(not any(c in part for c in "\\:\x00") and not part.endswith((".", " ")),
                f"unsafe Windows path component: {part!r}")
        stem = part.split(".")[0].upper()
        require(stem not in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
                and not re.fullmatch(r"(?:COM|LPT)[1-9]", stem), f"reserved Windows path: {part}")
    return rel


def child(root: Path, name: str) -> Path:
    return root.joinpath(*relative_name(name).parts)


def write_new(path: Path, data: bytes) -> None:
    with open(io_path(path), "xb") as stream:
        stream.write(data)


def write_json(path: Path, value: object) -> None:
    write_new(path, (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode())


def read_bytes(path: Path) -> bytes:
    with open_source(path) as stream:
        return stream.read()


@contextmanager
def open_source(path: Path):
    """Verify the opened Windows file handle before reading any content."""
    expected_final = os.path.realpath(io_path(path), strict=True)
    safe_components(path)
    if os.name != "nt":
        with open(io_path(path), "rb") as stream:
            yield stream
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    handle = kernel.CreateFileW(io_path(path), 0x80000000, 7, None, 3, 0x00200000, None)
    require(handle != ctypes.c_void_p(-1).value, f"cannot open ordinary source: {path}; WinError {ctypes.get_last_error()}")
    owned = True
    try:
        attributes = (wintypes.DWORD * 2)()
        require(bool(kernel.GetFileInformationByHandleEx(handle, 9, attributes, ctypes.sizeof(attributes))), "cannot inspect opened file")
        require(not attributes[0] & (REPARSE | 0x10), f"opened source is reparse or directory: {path}")
        final = ctypes.create_unicode_buffer(32768)
        length = kernel.GetFinalPathNameByHandleW(handle, final, len(final), 0)
        require(0 < length < len(final), "cannot establish opened source identity")
        require(os.path.normcase(final.value) == os.path.normcase(expected_final), f"opened file escaped source identity: {path}")
        safe_components(path)
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        owned = False
        with os.fdopen(descriptor, "rb") as stream:
            yield stream
    finally:
        if owned:
            kernel.CloseHandle(handle)


def hash_file(path: Path) -> tuple[int, str, bool]:
    count, digest, private, tail = 0, hashlib.sha256(), False, b""
    with open_source(path) as stream:
        while data := stream.read(BLOCK):
            count += len(data)
            digest.update(data)
            private |= bool(PRIVATE_MARKER.search(tail + data))
            tail = data[-128:]
    return count, digest.hexdigest(), private


def file_identity(info: os.stat_result) -> dict:
    return {"bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "mode": stat.S_IMODE(info.st_mode), "device": info.st_dev,
            "inode": info.st_ino, "attributes": getattr(info, "st_file_attributes", 0)}


class Policy:
    def __init__(self, data: dict):
        require(data.get("schema_version") == SCHEMA, "unsupported policy schema")
        self.raw = data
        self.paths = {}
        for key in ("source_roots", "git_roots", "capture_targets", "restore_targets"):
            require(isinstance(data.get(key), list), f"policy {key} must be a list")
            self.paths[key] = [safe_components(Path(p), allow_missing=key.endswith("targets")) for p in data[key]]
            require(len({os.path.normcase(str(p)) for p in self.paths[key]}) == len(self.paths[key]), f"duplicate {key}")
        require(self.paths["source_roots"], "policy has no source roots")
        self.classifications = {}
        for entry in data.get("classifications", []):
            root = self.authorize(Path(entry["source_root"]), "source_roots")
            name = str(relative_name(entry["path"]))
            require(entry.get("kind") in {"fixture_database", "public_certificate", "fixture_secret_marker", "live_profile", "private_key", "unknown"},
                    f"invalid classification: {name}")
            require(isinstance(entry.get("evidence"), str) and entry["evidence"].strip(), f"classification needs provenance evidence: {name}")
            if entry["kind"] in {"fixture_database", "public_certificate", "fixture_secret_marker"}:
                require(re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")) is not None,
                        f"transfer classification must pin exact bytes: {name}")
            identity = entry["sha256"] if entry["kind"] in {"fixture_database", "public_certificate", "fixture_secret_marker"} else "BLOCKED_CURRENT"
            key = (os.path.normcase(str(root)), name, identity)
            require(key not in self.classifications, f"duplicate exact classification: {name}")
            self.classifications[key] = entry
        for declared in data.get("declared_inputs", []):
            path = safe_components(Path(declared["path"]))
            require(any(inside(path, r) for r in self.paths["source_roots"]), f"declared input outside authorized source: {path}")
            require(stat.S_ISREG(lstat(path).st_mode), f"declared input is not ordinary: {path}")
            _, value, _ = hash_file(path)
            require(value == declared["sha256"], f"declared input hash differs: {path}")

    def authorize(self, path: Path, key: str, *, missing: bool = False) -> Path:
        actual = safe_components(path, allow_missing=missing)
        require(any(same_path(actual, p) for p in self.paths[key]), f"not explicitly authorized in {key}: {actual}")
        return actual

    def classify(self, root: Path, name: str, digest: str | None = None) -> dict | None:
        prefix = (os.path.normcase(str(root)), name)
        if digest is not None:
            return self.classifications.get((*prefix, digest))
        blocked = self.classifications.get((*prefix, "BLOCKED_CURRENT"))
        if blocked is not None:
            return blocked
        return next((v for k, v in self.classifications.items() if k[:2] == prefix), None)


def potential_sensitive(name: str) -> bool:
    path = PurePosixPath(name)
    return (path.suffix.lower() in SENSITIVE_SUFFIXES or path.name.lower() in SECRET_NAMES
            or path.name.lower() == ".env" or path.name.lower().startswith(".env.")
            or any(p.lower() in {"live-profile", "live_profiles", "private-keys"} for p in path.parts))


def validate_public_certificate(data: bytes) -> None:
    require(not PRIVATE_MARKER.search(data), "private key cannot be classified as a public certificate")
    try:
        text = data.decode("ascii")
        normalized = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", normalized, re.S)
        require(bool(blocks), "public certificate classification contains no certificate")
        residue = normalized
        for block in blocks:
            ssl.PEM_cert_to_DER_cert(block)
            residue = residue.replace(block, "", 1)
        require(not residue.strip(), "public certificate includes other content")
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=normalized)
    except (ValueError, UnicodeError, ssl.SSLError) as exc:
        raise PreservationError("public certificate classification has invalid certificate bytes") from exc


def validate_fixture_marker(data: bytes) -> None:
    """Known producer-owned invalid markers may not authorize actual key material."""
    require(PRIVATE_MARKER.search(data) is not None, "fixture marker classification contains no private-key marker")
    for match in PRIVATE_MARKER.finditer(data):
        body = data[match.end():].split(b"-----END ", 1)[0]
        # Legacy encrypted PEM includes Proc-Type/DEK-Info headers. Those headers
        # must not turn a real encoded payload into an accepted invalid fixture.
        base64_lines = [line.strip() for line in body.splitlines()
                        if re.fullmatch(br"[A-Za-z0-9+/]+={0,2}", line.strip())]
        for compact in (re.sub(br"\s+", b"", body), b"".join(base64_lines)):
            try:
                decoded = base64.b64decode(compact, validate=True)
            except (ValueError, binascii.Error):
                continue
            require(len(decoded) < 32, "fixture marker classification contains potential private-key material")


def assess_file(path: Path, root: Path, name: str, policy: Policy) -> dict:
    first = lstat(path)
    require(stat.S_ISREG(first.st_mode) and not reparse(first), f"not an ordinary file: {path}")
    result = {"path": name, "kind": "file", **file_identity(first)}
    classification = policy.classify(root, name)
    if classification and classification["kind"] in {"live_profile", "private_key", "unknown"}:
        return {**result, "kind": "pending_sensitive", "contents": "NOT_READ_OR_COPIED", "classification": classification}
    if potential_sensitive(name) and not classification:
        return {**result, "kind": "pending_sensitive", "contents": "NOT_READ_OR_COPIED", "classification": "PROVENANCE_REQUIRED"}
    count, digest, private = hash_file(path)
    require(file_identity(first) == file_identity(lstat(path)), f"file changed while hashing: {path}")
    require(count == first.st_size, f"file size changed while hashing: {path}")
    if classification:
        classification = policy.classify(root, name, digest)
        if classification is None:
            return {**result, "kind": "pending_sensitive", "contents": "HASHED_UNCLASSIFIED_CURRENT_BYTES_NOT_COPIED",
                    "sha256": digest, "classification": "EXACT_CURRENT_BYTES_PROVENANCE_REQUIRED"}
    marker_fixture = bool(classification and classification["kind"] == "fixture_secret_marker")
    if private and not marker_fixture:
        return {**result, "kind": "pending_sensitive", "contents": "SCANNED_PRIVATE_KEY_NOT_COPIED", "sha256": digest,
                "classification": "PRIVATE_KEY_MARKER_OBSERVED"}
    if classification:
        require(digest == classification["sha256"], f"classified bytes changed: {name}")
        if classification["kind"] == "public_certificate":
            validate_public_certificate(read_bytes(path))
        elif classification["kind"] == "fixture_database":
            with open_source(path) as stream:
                require(stream.read(16) == b"SQLite format 3\x00", f"fixture database is not a SQLite file: {name}")
        elif marker_fixture:
            validate_fixture_marker(read_bytes(path))
        result["classification"] = classification
    # Repository config is metadata, but URLs containing credentials are still protected.
    if name.endswith("config") or PurePosixPath(name).name.lower() in {".netrc", "_netrc"}:
        with open_source(path) as stream:
            config = stream.read(4 * BLOCK)
        if re.search(br"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/]+:[^\s/@]+@", config):
            return {**result, "kind": "pending_sensitive", "contents": "SCANNED_CREDENTIAL_LOCATION_NOT_COPIED",
                    "classification": "CREDENTIAL_URL_OBSERVED"}
    return {**result, "sha256": digest}


def reparse_descriptor(path: Path) -> dict:
    result = {"target": None, "raw_descriptor_b64": None, "usable_link_restored": False}
    try:
        result["target"] = os.readlink(io_path(path))
    except OSError:
        pass
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                          ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(io_path(path), 0, 7, None, 3, 0x02000000 | 0x00200000, None)
        require(handle != ctypes.c_void_p(-1).value, f"cannot open reparse descriptor: {path}")
        try:
            buffer, used = ctypes.create_string_buffer(16384), wintypes.DWORD()
            okay = kernel.DeviceIoControl(handle, 0x000900A8, None, 0, buffer, len(buffer), ctypes.byref(used), None)
            require(bool(okay), f"cannot preserve reparse descriptor: {path}; WinError {ctypes.get_last_error()}")
            result["raw_descriptor_b64"] = base64.b64encode(buffer.raw[:used.value]).decode()
        finally:
            kernel.CloseHandle(handle)
    require(result["target"] is not None or result["raw_descriptor_b64"] is not None, f"unreadable reparse entry: {path}")
    return result


def tree_inventory(root: Path, policy: Policy, *, exclude: Path | None = None,
                   skip_git: bool = False, skip_objects: bool = False) -> list[dict]:
    entries = []
    stack = [(root, "")]
    while stack:
        current, prefix = stack.pop()
        with os.scandir(io_path(current)) as listing:
            children = sorted(listing, key=lambda e: e.name)
        for item in children:
            path = current / item.name
            name = prefix + item.name
            relative_name(name)
            if exclude is not None and same_path(path, exclude):
                continue
            if not prefix and ((skip_git and item.name == ".git") or (skip_objects and item.name == "objects")):
                continue
            info = item.stat(follow_symlinks=False)
            if reparse(info):
                entries.append({"path": name, "kind": "reparse", **file_identity(info), "descriptor": reparse_descriptor(path)})
            elif stat.S_ISDIR(info.st_mode):
                # Directory mtime changes on creation of the exact active output; child names,
                # files, modes and identities establish stability without directory mtime.
                entries.append({"path": name, "kind": "directory", "mode": stat.S_IMODE(info.st_mode)})
                stack.append((path, name + "/"))
            elif stat.S_ISREG(info.st_mode):
                entries.append(assess_file(path, root, name, policy))
            else:
                raise PreservationError(f"unsupported nonordinary source entry: {path}")
    names = [e["path"].casefold() for e in entries]
    require(len(names) == len(set(names)), "Windows case-colliding source paths")
    return sorted(entries, key=lambda e: e["path"])


def git_environment() -> dict:
    result = {name: value for name, value in os.environ.items() if not name.upper().startswith("GIT_")}
    result.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
                  GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1")
    return result


def git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    completed = subprocess.run(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-c", "core.fsmonitor=false",
                                "-c", "submodule.recurse=false", "-C", str(root), *args],
                               input=data, capture_output=True, env=git_environment())
    require(completed.returncode == 0,
            f"git {args[0]} failed ({completed.returncode}): {completed.stderr.decode('utf-8', errors='replace')[:1200]}")
    return completed.stdout


def text_git(root: Path, *args: str) -> str:
    return git(root, *args).decode("utf-8", errors="strict").strip()


def discover_git_dirs(root: Path, policy: Policy) -> tuple[Path, Path]:
    marker = root / ".git"
    require(not reparse(lstat(marker)), "Git marker may not be a reparse entry")
    if stat.S_ISDIR(lstat(marker).st_mode):
        local = safe_components(marker)
    else:
        pointer = read_bytes(marker).decode("utf-8").strip()
        require(pointer.startswith("gitdir: ") and "\n" not in pointer, "invalid Git directory pointer")
        raw = Path(pointer[8:])
        local = safe_components(Path(os.path.abspath(raw if raw.is_absolute() else root / raw)))
    require(any(inside(local, p) for p in policy.paths["git_roots"]), "worktree Git directory outside exact authorization")
    if exists(local / "commondir"):
        pointer = read_bytes(local / "commondir").decode("utf-8").strip()
        require(pointer and "\n" not in pointer, "invalid common Git directory pointer")
        raw = Path(pointer)
        common = policy.authorize(Path(os.path.abspath(raw if raw.is_absolute() else local / raw)), "git_roots")
    else:
        common = policy.authorize(local, "git_roots")
    for config in (common / "config", local / "config.worktree"):
        if exists(config):
            data = read_bytes(config)
            require(not re.search(br"(?im)^\s*\[\s*(?:include|includeIf|filter)\b", data),
                    f"Git includes or executable filters need separate review: {config}")
            require(not re.search(br"(?im)^\s*partialclone\s*=|^\s*promisor\s*=\s*true", data), "partial Git history is not complete")
    for path in (common / "objects" / "info" / "alternates", common / "info" / "grafts"):
        require(not exists(path) or not read_bytes(path).strip(), f"external object storage or grafts need separate review: {path}")
    return local, common


def create_read_view(root: Path, policy: Policy, target: Path) -> dict | None:
    """Private index observation prevents Git's split-index mtime writes to source."""
    if not exists(root / ".git"):
        return None
    local, common = discover_git_dirs(root, policy)
    require(not exists(target), "index observation target already exists")
    os.mkdir(io_path(target))
    os.mkdir(io_path(target / "objects"))
    os.mkdir(io_path(target / "refs"))
    os.mkdir(io_path(target / "info"))
    write_new(target / "HEAD", read_bytes(local / "HEAD"))
    object_format = text_git(root, "rev-parse", "--show-object-format")
    config = b"[core]\n\trepositoryformatversion = " + (b"1" if object_format == "sha256" else b"0") + b"\n\tbare = false\n"
    for key in ("autocrlf", "eol", "filemode", "ignorecase", "symlinks"):
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "config", "--no-includes", "--get", "core." + key],
                                capture_output=True, env=git_environment())
        require(result.returncode in {0, 1}, f"cannot observe core.{key}")
        if result.returncode == 0:
            value = result.stdout.decode("ascii").strip()
            require(value in {"true", "false", "input", "lf", "crlf", "native"}, f"unqualified core.{key} value")
            config += ("\t" + key + " = " + value + "\n").encode()
    if object_format == "sha256":
        config += b"[extensions]\n\tobjectformat = sha256\n"
    write_new(target / "config", config)
    for line in text_git(root, "for-each-ref", "--format=%(refname) %(objectname)").splitlines():
        name, oid = line.split()
        git(root, "check-ref-format", name)
        path = child(target, name)
        os.makedirs(io_path(path.parent), exist_ok=True)
        write_new(path, (oid + "\n").encode())
    with os.scandir(io_path(local)) as listing:
        for entry in listing:
            if entry.name == "index" or re.fullmatch(r"sharedindex\.[0-9a-f]+", entry.name):
                write_new(target / entry.name, read_bytes(local / entry.name))
    for name in ("exclude", "attributes"):
        path = common / "info" / name
        if exists(path):
            write_new(target / "info" / name, read_bytes(path))
    return {"directory": str(target), "objects": str(common / "objects")}


def view_git(root: Path, view: dict, *args: str) -> bytes:
    env = git_environment()
    # Git for Windows has a separate GIT_DIR environment length check. Relative
    # generated-view locations avoid it without borrowing or linking source data.
    env.update(GIT_DIR=os.path.relpath(view["directory"], root), GIT_WORK_TREE=str(root),
               GIT_INDEX_FILE=os.path.relpath(Path(view["directory"]) / "index", root),
               GIT_OBJECT_DIRECTORY=os.path.relpath(view["objects"], root))
    completed = subprocess.run(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-c", "core.fsmonitor=false",
                                "-c", "submodule.recurse=false", "-C", str(root), *args], capture_output=True, env=env)
    require(completed.returncode == 0, f"Git index observation failed ({args[0]}): {completed.stderr.decode(errors='replace')[:1200]}")
    return completed.stdout


def validate_active_exclusion(root: Path, policy: Policy, exclusion: Path | None) -> None:
    if exclusion is None or not exists(root / ".git"):
        return
    local, common = discover_git_dirs(root, policy)
    require(not inside(exclusion, common) and not inside(exclusion, local), "active output cannot be placed in Git metadata")
    name = exclusion.relative_to(root).as_posix()
    relative_name(name)
    for commit in text_git(root, "rev-list", "--all", "--reflog").splitlines():
        require(not git(root, "ls-tree", "-r", "-z", commit, "--", name), "active output exclusion intersects historical work")


def git_state(root: Path, policy: Policy, exclusion: Path | None = None, view: dict | None = None,
              protected_paths: list[str] | None = None) -> dict | None:
    if not exists(root / ".git"):
        return None
    local, common = discover_git_dirs(root, policy)
    actual = Path(text_git(root, "rev-parse", "--show-toplevel"))
    require(same_path(actual, root), "source must be the exact Git worktree root")
    require(not exists(common / "shallow"), "shallow history cannot satisfy complete recovery")
    objects = []
    for line in text_git(root, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)").splitlines():
        oid, kind, size = line.split()
        require(OID.fullmatch(oid) is not None and kind in {"blob", "tree", "commit", "tag"}, "invalid object identity")
        objects.append({"oid": oid, "type": kind, "bytes": int(size)})
    # Missing objects referenced by refs/reflogs are a concrete error, not an empty inventory.
    reachable = text_git(root, "rev-list", "--all", "--reflog").splitlines()
    refs = []
    for line in text_git(root, "for-each-ref", "--format=%(refname) %(objectname)").splitlines():
        name, oid = line.split()
        git(root, "check-ref-format", name)
        refs.append({"name": name, "oid": oid})
    for ref in refs:
        git(root, "cat-file", "-e", ref["oid"])
    pathspec = ["--", "."]
    protected_paths = sorted(protected_paths or [])
    require(view is not None, "Git index observations require a private read view")
    if exclusion is not None:
        name = exclusion.relative_to(root).as_posix()
        relative_name(name)
        require(not inside(exclusion, common) and not inside(exclusion, local), "active output cannot be placed in Git metadata")
        # An absent working path can still contain deleted tracked or historical
        # work. Never hide it using an output exclusion.
        require(not view_git(root, view, "ls-files", "-z", "--", name), "active output exclusion intersects indexed history")
        for commit in reachable:
            require(not git(root, "ls-tree", "-r", "-z", commit, "--", name), "active output exclusion intersects historical work")
        pathspec.append(":(exclude,literal)" + name)
    for name in protected_paths:
        relative_name(name)
        pathspec.append(":(exclude,literal)" + name)
    head = read_bytes(local / "HEAD").decode("ascii").strip()
    metadata = {"common": tree_inventory(common, policy, skip_objects=True)}
    roots = {"common": str(common)}
    if not same_path(common, local):
        metadata["worktree"] = tree_inventory(local, policy)
        roots["worktree"] = str(local)
    pointer = read_bytes(root / ".git") if stat.S_ISREG(lstat(root / ".git").st_mode) else None
    return {"source_root": str(root), "common_dir": str(common), "worktree_git_dir": str(local), "metadata_roots": roots,
            "object_format": text_git(root, "rev-parse", "--show-object-format"), "head": head,
            "refs": refs, "objects": sorted(objects, key=lambda o: o["oid"]), "ref_reflog_commits": sorted(set(reachable)),
            "status_b64": base64.b64encode(view_git(root, view, "status", "--porcelain=v2", "-z", "--untracked-files=all", *pathspec)).decode(),
            "worktrees_b64": base64.b64encode(git(root, "worktree", "list", "--porcelain", "-z")).decode(),
            "working_patch_b64": None if protected_paths else base64.b64encode(view_git(root, view, "diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv", *pathspec)).decode(),
            "staged_patch_b64": None if protected_paths else base64.b64encode(view_git(root, view, "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "--no-textconv", *pathspec)).decode(),
            "protected_working_paths": protected_paths,
            "git_pointer_b64": base64.b64encode(pointer).decode() if pointer is not None else None, "metadata": metadata,
            "original_object_storage": tree_inventory(common / "objects", policy)}


def snapshot(root: Path, policy: Policy, exclusion: Path | None, view: dict | None = None) -> dict:
    entries = tree_inventory(root, policy, exclude=exclusion, skip_git=True)
    protected = [e["path"] for e in entries if e["kind"] == "pending_sensitive"]
    return {"source_root": str(root), "entries": entries, "git": git_state(root, policy, exclusion, view, protected)}


def stream_object_blobs(root: Path, objects: list[dict]):
    """Read each blob once through Git plumbing; no lazy fetch or external process filters."""
    # communicate would retain all blob bytes. One request/response bounds memory per chunk.
    proc = subprocess.Popen(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-C", str(root), "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=git_environment())
    try:
        assert proc.stdin is not None and proc.stdout is not None
        for obj in objects:
            if obj["type"] != "blob":
                continue
            proc.stdin.write((obj["oid"] + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode("ascii").strip().split()
            require(header == [obj["oid"], "blob", str(obj["bytes"])], f"Git blob stream differs from object inventory: {header!r}")
            remaining, tail, private, sample = obj["bytes"], b"", False, bytearray()
            while remaining:
                data = proc.stdout.read(min(BLOCK, remaining))
                require(bool(data), "Git blob stream ended early")
                remaining -= len(data)
                private |= bool(PRIVATE_MARKER.search(tail + data))
                tail = data[-128:]
                if len(sample) < 4096:
                    sample.extend(data[:4096 - len(sample)])
            require(proc.stdout.read(1) == b"\n", "Git blob boundary differs")
            yield obj["oid"], private, bytes(sample)
        proc.stdin.close()
        require(proc.wait(timeout=30) == 0, "Git blob inspection failed")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None and not stream.closed:
                stream.close()


def git_sensitive(root: Path, state: dict, policy: Policy) -> list[dict]:
    pending = []
    # Enumerate every committed tree, including reflog-only commits. A SQLite path
    # is a candidate, not an assertion that a disposable fixture is live data.
    by_blob = {}
    for commit in state["ref_reflog_commits"]:
        for item in git(root, "ls-tree", "-r", "-z", commit).split(b"\0"):
            if not item:
                continue
            metadata, raw_name = item.split(b"\t", 1)
            _, kind, oid = metadata.decode("ascii").split()
            name = raw_name.decode("utf-8")
            if kind == "blob":
                by_blob.setdefault(oid, set()).add(name)
    for oid, private, sample in stream_object_blobs(root, state["objects"]):
        if private:
            approved_marker = False
            for name in sorted(by_blob.get(oid, set())):
                data = git(root, "cat-file", "blob", oid)
                classification = policy.classify(root, name, sha(data))
                if classification and classification["kind"] == "fixture_secret_marker":
                    if sha(data) == classification["sha256"]:
                        validate_fixture_marker(data)
                        approved_marker = True
                        break
            if not approved_marker:
                pending.append({"git_object": oid, "kind": "private_key_candidate", "contents": "SCANNED_NOT_COPIED"})
                continue
        if sample.startswith(b"SQLite format 3\x00") and oid not in by_blob:
            pending.append({"git_object": oid, "kind": "unclassified_database", "contents": "SCANNED_NOT_COPIED"})
        for name in sorted(by_blob.get(oid, set())):
            if not potential_sensitive(name):
                continue
            data = git(root, "cat-file", "blob", oid)
            classification = policy.classify(root, name, sha(data))
            if not classification or classification["kind"] not in {"fixture_database", "public_certificate", "fixture_secret_marker"}:
                pending.append({"git_object": oid, "path": name, "kind": "provenance_required", "contents": "NOT_COPIED"})
                continue
            if sha(data) != classification["sha256"]:
                pending.append({"git_object": oid, "path": name, "kind": "historical_bytes_not_classified", "contents": "NOT_COPIED"})
            elif classification["kind"] == "public_certificate":
                validate_public_certificate(data)
            elif classification["kind"] == "fixture_secret_marker":
                validate_fixture_marker(data)
            else:
                require(data.startswith(b"SQLite format 3\x00"), f"classified Git object is not fixture SQLite: {name}")
    return pending


def add_file(archive: zipfile.ZipFile, source: Path, entry: dict, name: str) -> None:
    before = lstat(source)
    require(not reparse(before) and stat.S_ISREG(before.st_mode), f"file became nonordinary: {source}")
    require(file_identity(before) == {k: entry[k] for k in file_identity(before)}, f"file identity changed before copy: {source}")
    count, digest = 0, hashlib.sha256()
    with open_source(source) as stream, archive.open(name, "w", force_zip64=True) as target:
        while data := stream.read(BLOCK):
            count += len(data)
            digest.update(data)
            target.write(data)
    require(count == entry["bytes"] and digest.hexdigest() == entry["sha256"], f"source changed during copy: {source}")
    require(file_identity(before) == file_identity(lstat(source)), f"source identity changed during copy: {source}")


def archive_tree(path: Path, root: Path, entries: list[dict]) -> None:
    with zipfile.ZipFile(io_path(path), "x", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for entry in entries:
            if entry["kind"] == "file":
                add_file(archive, child(root, entry["path"]), entry, entry["path"])


def export_objects(root: Path, state: dict, path: Path) -> None:
    data = "".join(o["oid"] + "\n" for o in state["objects"]).encode()
    with open(io_path(path), "xb") as stream:
        completed = subprocess.run(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-C", str(root), "pack-objects", "--stdout"],
                                   input=data, stdout=stream, stderr=subprocess.PIPE, env=git_environment())
    require(completed.returncode == 0, "independent Git object export failed")


def capture(root: Path, destination: Path, policy: Policy, *, active_output_exclusion: Path | None = None) -> dict:
    root = policy.authorize(root, "source_roots")
    destination = policy.authorize(destination, "capture_targets", missing=True)
    require(not exists(destination), "capture destination already exists; overwrite refused")
    safe_components(destination.parent)
    require(not any(inside(source, destination) for source in policy.paths["source_roots"]), "capture target contains an authorized source")
    require(not any(inside(destination, area) or inside(area, destination) for area in policy.paths["git_roots"]),
            "capture target intersects original Git metadata")
    if exists(root / ".git"):
        discover_git_dirs(root, policy)
    enclosing = [s for s in policy.paths["source_roots"] if inside(destination, s)]
    if enclosing:
        require(active_output_exclusion is not None and same_path(destination, Path(os.path.abspath(active_output_exclusion))),
                "inside-source capture requires the exact active-output exclusion")
        require(inside(destination, root), "output cannot be placed inside another authorized source")
    else:
        require(active_output_exclusion is None, "outside-source capture does not accept an exclusion")
    exclusion = destination if enclosing else None
    validate_active_exclusion(root, policy, exclusion)
    os.mkdir(io_path(destination))
    started = utc()
    artifacts = []
    try:
        view = create_read_view(root, policy, destination / "git-index-observation")
        before = snapshot(root, policy, exclusion, view)
        pending = [e for e in before["entries"] if e["kind"] == "pending_sensitive"]
        state = before["git"]
        if state:
            for scope, entries in state["metadata"].items():
                pending.extend({**e, "git_metadata_scope": scope} for e in entries if e["kind"] == "pending_sensitive")
            pending.extend(git_sensitive(root, state, policy))
        archive_tree(destination / "working-tree.zip", root, before["entries"])
        artifacts.append("working-tree.zip")
        if state:
            for scope, entries in state["metadata"].items():
                name = f"git-{scope}-metadata.zip"
                archive_tree(destination / name, Path(state["metadata_roots"][scope]), entries)
                artifacts.append(name)
            if not pending:
                for name, key in (("working.patch", "working_patch_b64"), ("staged.patch", "staged_patch_b64")):
                    write_new(destination / name, base64.b64decode(state[key]))
                    artifacts.append(name)
                export_objects(root, state, destination / "git-objects.pack")
                artifacts.append("git-objects.pack")
        after_view = create_read_view(root, policy, destination / "git-index-observation-after")
        after = snapshot(root, policy, exclusion, after_view)
        require(before == after, "source or Git metadata changed during capture; checkpoint rejected")
        recorded = copy.deepcopy(before)
        if pending and state:
            for key in ("working_patch_b64", "staged_patch_b64"):
                encoded = recorded["git"][key]
                recorded["git"][key.replace("_b64", "_sha256")] = sha(base64.b64decode(encoded)) if encoded is not None else None
                recorded["git"][key] = None
            recorded["git"]["diff_contents"] = "WITHHELD_PENDING_SENSITIVE"
        write_json(destination / "inventory.json", recorded)
        artifacts.append("inventory.json")
        artifact_records = []
        for name in artifacts:
            size, digest, _ = hash_file(destination / name)
            artifact_records.append({"path": name, "bytes": size, "sha256": digest})
        manifest = {"schema_version": SCHEMA, "started_at": started, "finished_at": utc(), "source_root": str(root),
                    "policy_sha256": sha(json.dumps(policy.raw, sort_keys=True).encode()), "source_unchanged": True if not pending else None,
                    "observed_regular_bytes_and_git_metadata_unchanged": True,
                    "sensitive_content_stability": "NOT_CLAIMED_FOR_UNREAD_PENDING_FILES" if pending else "NO_PENDING_FILES",
                    "complete": not pending, "pending": pending, "active_output_exclusion": str(exclusion) if exclusion else None,
                    "result": "CAPTURED_COMPLETE" if not pending else "CAPTURED_INCOMPLETE_PENDING_SENSITIVE",
                    "git_preservation": ("ALL_OBJECTS_REFS_REFLOG_METADATA_INDEX_AND_BINARY_DIFFS" if not pending
                                         else "INCOMPLETE_PENDING_SENSITIVE") if state else "NOT_A_GIT_WORKTREE",
                    "reparse_entries": sum(e["kind"] == "reparse" for e in before["entries"]), "usable_links_restored": False,
                    "private_index_observation": "CAPTURE_TARGET_ONLY_NOT_RESTORED",
                    "artifacts": artifact_records}
        write_json(destination / "checkpoint.json", manifest)
        write_new(destination / "COMMITTED", (sha(read_bytes(destination / "checkpoint.json")) + "\n").encode())
        return manifest
    except Exception as exc:
        if not exists(destination / "FAILED.json"):
            write_json(destination / "FAILED.json", {"result": "FAILED_NOT_RESTORABLE", "at": utc(), "error": str(exc)})
        raise


def load_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(read_bytes(path), object_pairs_hook=unique)


def verify_archive(path: Path, entries: list[dict]) -> None:
    files = {e["path"]: e for e in entries if e["kind"] == "file"}
    require(len(files) == sum(e["kind"] == "file" for e in entries), "duplicate inventory files")
    all_names = [e["path"] for e in entries]
    for name in all_names:
        relative_name(name)
    require(len({n.casefold() for n in all_names}) == len(all_names), "case-colliding inventory entries")
    with zipfile.ZipFile(io_path(path)) as archive:
        require(len(archive.infolist()) == len(files) and set(archive.namelist()) == set(files), "archive membership differs")
        for item in archive.infolist():
            relative_name(item.filename)
            require(not stat.S_ISLNK(item.external_attr >> 16), "archive symlink is forbidden")
            expected = files[item.filename]
            require(item.file_size == expected["bytes"], "archive member size differs")
            digest = hashlib.sha256()
            with archive.open(item) as stream:
                while data := stream.read(BLOCK):
                    digest.update(data)
            require(digest.hexdigest() == expected["sha256"], "archive member hash differs")


def verify_checkpoint(path: Path, policy: Policy) -> tuple[dict, dict]:
    path = policy.authorize(path, "capture_targets")
    require(exists(path / "COMMITTED") and not exists(path / "FAILED.json"), "checkpoint is not committed")
    manifest_bytes = read_bytes(path / "checkpoint.json")
    require(read_bytes(path / "COMMITTED").decode().strip() == sha(manifest_bytes), "checkpoint manifest seal differs")
    manifest = load_json(path / "checkpoint.json")
    require(manifest.get("schema_version") == SCHEMA, "invalid checkpoint schema")
    require(manifest.get("complete") is True and manifest.get("pending") == [], "partial checkpoint cannot restore")
    require(manifest.get("source_unchanged") is True, "invalid checkpoint state")
    source = policy.authorize(Path(manifest["source_root"]), "source_roots")
    names = [e["path"] for e in manifest["artifacts"]]
    require(len(names) == len(set(names)), "duplicate checkpoint artifacts")
    for artifact in manifest["artifacts"]:
        relative_name(artifact["path"])
        target = safe_components(child(path, artifact["path"]))
        size, digest, _ = hash_file(target)
        require(size == artifact["bytes"] and digest == artifact["sha256"], f"checkpoint artifact differs: {artifact['path']}")
    inventory = load_json(path / "inventory.json")
    require(same_path(Path(inventory["source_root"]), source), "inventory source identity differs")
    expected = {"working-tree.zip", "inventory.json"}
    require(not any(relative_name(e["path"]).parts[0].lower() == ".git" for e in inventory["entries"]),
            "working inventory cannot inject active Git metadata")
    verify_archive(path / "working-tree.zip", inventory["entries"])
    state = inventory["git"]
    if state:
        expected |= {"git-objects.pack", "working.patch", "staged.patch"}
        for scope, entries in state["metadata"].items():
            require(scope in {"common", "worktree"}, "unknown Git metadata scope")
            name = f"git-{scope}-metadata.zip"
            expected.add(name)
            verify_archive(path / name, entries)
        for obj in state["objects"]:
            require(OID.fullmatch(obj["oid"]) is not None, "unsafe object identity")
        for ref in state["refs"]:
            require(ref["name"].startswith("refs/") and "\n" not in ref["name"] and OID.fullmatch(ref["oid"]) is not None,
                    "unsafe preserved ref")
        require(state["object_format"] in {"sha1", "sha256"}, "unsupported Git object format")
    require(set(names) == expected, "checkpoint has missing or unexpected artifacts")
    return manifest, inventory


def extract_tree(archive_path: Path, target: Path, entries: list[dict]) -> None:
    for entry in entries:
        if entry["kind"] == "directory":
            os.makedirs(io_path(child(target, entry["path"])), exist_ok=True)
    files = {e["path"]: e for e in entries if e["kind"] == "file"}
    with zipfile.ZipFile(io_path(archive_path)) as archive:
        for name, entry in files.items():
            path = child(target, name)
            os.makedirs(io_path(path.parent), exist_ok=True)
            with archive.open(name) as stream, open(io_path(path), "xb") as output:
                shutil.copyfileobj(stream, output, BLOCK)
            require(hash_file(path)[:2] == (entry["bytes"], entry["sha256"]), f"restored bytes differ: {name}")
            os.utime(io_path(path), ns=(entry["mtime_ns"], entry["mtime_ns"]))
            os.chmod(io_path(path), entry["mode"])


def publish_new(stage: Path, destination: Path) -> None:
    require(not exists(destination), "restore target appeared during recovery; overwrite refused")
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
        kernel.MoveFileExW.restype = wintypes.BOOL
        # No REPLACE_EXISTING. The kernel refuses a racing destination atomically.
        require(bool(kernel.MoveFileExW(io_path(stage), io_path(destination), 8)),
                f"restore publish refused: WinError {ctypes.get_last_error()}")
    else:
        raise PreservationError("atomic no-overwrite publication is qualified only on Windows")


def restore(checkpoint: Path, destination: Path, policy: Policy, *, allow_inert_reparse: bool = False) -> dict:
    destination = policy.authorize(destination, "restore_targets", missing=True)
    require(not exists(destination), "restore destination already exists; overwrite refused")
    safe_components(destination.parent)
    require(not any(inside(destination, root) or inside(root, destination) for root in policy.paths["source_roots"]),
            "restore must be separate from every original source")
    require(not any(inside(destination, root) or inside(root, destination) for root in policy.paths["git_roots"]),
            "restore must be separate from original Git metadata")
    checkpoint = policy.authorize(checkpoint, "capture_targets")
    require(not inside(destination, checkpoint) and not inside(checkpoint, destination), "restore may not contain or recurse into checkpoint")
    manifest, inventory = verify_checkpoint(checkpoint, policy)
    links = [e for e in inventory["entries"] if e["kind"] == "reparse"]
    state = inventory["git"]
    if state:
        links += [e for entries in state["metadata"].values() for e in entries if e["kind"] == "reparse"]
    require(not links or allow_inert_reparse, "usable links are not restored; explicit inert-descriptor acceptance required")
    stage = destination.with_name(destination.name + ".incomplete-" + uuid.uuid4().hex)
    require(not exists(stage), "restore staging path already exists")
    os.mkdir(io_path(stage))
    try:
        working, metadata = stage / "working-tree", stage / "preservation-metadata"
        os.mkdir(io_path(working))
        os.mkdir(io_path(metadata))
        extract_tree(checkpoint / "working-tree.zip", working, inventory["entries"])
        write_json(metadata / "reparse-descriptors.json", {"entries": links, "usable_links_restored": False})
        write_new(metadata / "checkpoint.json", read_bytes(checkpoint / "checkpoint.json"))
        write_new(metadata / "inventory.json", read_bytes(checkpoint / "inventory.json"))
        if state:
            git(working, "init", "--object-format=" + state["object_format"])
            with open(io_path(checkpoint / "git-objects.pack"), "rb") as stream:
                completed = subprocess.run(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-C", str(working), "index-pack", "--stdin"],
                                           stdin=stream, capture_output=True, env=git_environment())
            require(completed.returncode == 0, "Git pack cannot be independently restored")
            for ref in state["refs"]:
                git(working, "check-ref-format", ref["name"])
            commands = "".join(f"create {ref['name']} {ref['oid']}\n" for ref in state["refs"])
            if commands:
                git(working, "update-ref", "--stdin", data=commands.encode())
            if state["head"].startswith("ref: "):
                git(working, "symbolic-ref", "HEAD", state["head"][5:])
            else:
                require(OID.fullmatch(state["head"]) is not None, "invalid preserved HEAD")
                git(working, "update-ref", "--no-deref", "HEAD", state["head"])
            # Keep every reflog-reachable commit alive independently of copied logs.
            for oid in state["ref_reflog_commits"]:
                require(OID.fullmatch(oid) is not None, "invalid reflog commit")
                git(working, "update-ref", "refs/ceta-preserved/reflog/" + oid, oid)
            for scope, entries in state["metadata"].items():
                area = metadata / ("original-git-" + scope)
                os.mkdir(io_path(area))
                extract_tree(checkpoint / ("git-" + scope + "-metadata.zip"), area, entries)
            index_scope = "worktree" if "worktree" in state["metadata"] else "common"
            index_source = metadata / ("original-git-" + index_scope) / "index"
            if exists(index_source):
                write_new(working / ".git" / "index", read_bytes(index_source))
            for entry in state["metadata"][index_scope]:
                name = entry["path"]
                if entry["kind"] == "file" and re.fullmatch(r"sharedindex\.[0-9a-f]+", name):
                    write_new(working / ".git" / name, read_bytes(metadata / ("original-git-" + index_scope) / name))
            expected_objects = [f"{o['oid']} {o['type']} {o['bytes']}" for o in state["objects"]]
            observed_objects = git(working, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                                   data="".join(o["oid"] + "\n" for o in state["objects"]).encode()).decode("ascii").splitlines()
            require(observed_objects == expected_objects, "restored Git objects differ from complete inventory")
            read_policy = Policy({"schema_version": SCHEMA, "source_roots": [str(working)], "git_roots": [str(working / ".git")],
                                  "capture_targets": [], "restore_targets": []})
            validation_view = create_read_view(working, read_policy, metadata / "index-view")
            assert validation_view is not None
            view_git(working, validation_view, "fsck", "--full", "--no-reflogs")
            require(view_git(working, validation_view, "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "--no-textconv")
                    == base64.b64decode(state["staged_patch_b64"]), "restored staged difference differs")
            # Inert reparse entries intentionally cannot reproduce link worktree diffs.
            if not links:
                require(view_git(working, validation_view, "diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv")
                        == base64.b64decode(state["working_patch_b64"]), "restored working difference differs")
            write_new(metadata / "working.patch", read_bytes(checkpoint / "working.patch"))
            write_new(metadata / "staged.patch", read_bytes(checkpoint / "staged.patch"))
        # Prove the subject checkpoint did not change while extraction was in progress.
        verify_checkpoint(checkpoint, policy)
        result = {"schema_version": SCHEMA, "result": "RESTORED_ORDINARY_BYTES_AND_INDEPENDENT_GIT",
                  "restored_at": utc(), "destination": str(destination), "source_root": inventory["source_root"],
                  "ordinary_files": sum(e["kind"] == "file" for e in inventory["entries"]),
                  "git_objects": len(state["objects"]) if state else 0, "original_refs": len(state["refs"]) if state else 0,
                  "reflog_commits": len(state["ref_reflog_commits"]) if state else 0,
                  "inert_reparse_descriptors": len(links), "usable_links_restored": False,
                  "historical_git_configuration": "PRESERVED_INERT_NOT_APPLIED", "runtime_qualification": "NOT_RUN"}
        write_json(metadata / "restore-receipt.json", result)
        publish_new(stage, destination)
        return result
    except Exception as exc:
        # Keep the unsuccessful stage as evidence. Never publish a partial destination.
        if not exists(stage / "FAILED.json"):
            write_json(stage / "FAILED.json", {"result": "FAILED_NOT_PUBLISHED", "at": utc(), "error": str(exc)})
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    sub = parser.add_subparsers(dest="operation", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--source", required=True, type=Path)
    c.add_argument("--output", required=True, type=Path)
    c.add_argument("--active-output-exclusion", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("--checkpoint", required=True, type=Path)
    r = sub.add_parser("restore")
    r.add_argument("--checkpoint", required=True, type=Path)
    r.add_argument("--destination", required=True, type=Path)
    r.add_argument("--allow-inert-reparse", action="store_true")
    args = parser.parse_args(argv)
    try:
        policy = Policy(load_json(args.policy))
        if args.operation == "capture":
            result = capture(args.source, args.output, policy, active_output_exclusion=args.active_output_exclusion)
            status = 0 if result["complete"] else 2
        elif args.operation == "verify":
            manifest, _ = verify_checkpoint(args.checkpoint, policy)
            result, status = {"result": "VERIFIED_CAPTURE_ARTIFACTS", "source_root": manifest["source_root"],
                              "runtime_qualification": "NOT_RUN"}, 0
        else:
            result = restore(args.checkpoint, args.destination, policy, allow_inert_reparse=args.allow_inert_reparse)
            status = 0
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return status
    except (PreservationError, OSError, ValueError, zipfile.BadZipFile, KeyError, TypeError) as exc:
        print(json.dumps({"result": "FAILED", "error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
