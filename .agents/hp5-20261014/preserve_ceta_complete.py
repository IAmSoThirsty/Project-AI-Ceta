"""CETA preservation: complete ordinary bytes and independent Git recovery data.

Capture never checks out, resets, cleans, fetches, changes refs, or changes source
configuration. Every source, Git directory, capture target and restore target is
explicitly authorized in a JSON policy. Sensitive candidates remain pending;
pending checkpoints cannot restore. Windows reparse points are inert evidence,
not usable links. No production profile, key, or source tree is replaced.
"""
from __future__ import annotations

import argparse
import ast
import base64
import binascii
import copy
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import functools
import json
import importlib.util
import io
import marshal
import msvcrt
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import stat
import struct
import subprocess
import sys
import tokenize
import types
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


@functools.cache
def windows_ordinal_comparator():
    """One read-only Windows ordinal comparator; never a linguistic fold."""
    compare = ctypes.WinDLL("kernel32", use_last_error=True).CompareStringOrdinal
    compare.argtypes = [wintypes.LPCWSTR, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int, wintypes.BOOL]
    compare.restype = ctypes.c_int
    return compare


def equivalent_blocked_path(first: str, second: str) -> bool:
    """Compare safe relative spellings without granting new positive admission.

    Original names stay in policy/proof/archive records. Case-sensitive Windows
    directories can be conservatively blocked by this predicate; positive
    classifications and content provenance still require exact spelling/bytes.
    """
    relative_name(first)
    relative_name(second)
    require(all(len(value.encode("utf-16-le", errors="surrogatepass")) // 2 <= 32767
                for value in (first, second)), "relative policy path exceeds Windows comparison bound")
    if first == second:
        return True
    if os.name != "nt":
        return False
    result = windows_ordinal_comparator()(first, -1, second, -1, True)
    require(result in {1, 2, 3}, "Windows ordinal path comparison failed")
    return result == 2


def write_new(path: Path, data: bytes) -> None:
    with open(io_path(path), "xb") as stream:
        stream.write(data)


def write_json(path: Path, value: object) -> None:
    write_new(path, (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode())


def read_bytes(path: Path) -> bytes:
    with open_source(path) as stream:
        return stream.read()


@contextmanager
def open_source(path: Path, *, exclusive: bool = False):
    """Verify the opened Windows file handle before reading any content."""
    expected_final = os.path.realpath(io_path(path), strict=True)
    safe_components(path)
    require(not exclusive or os.name == "nt", "immutable copy admission requires native Windows sharing")
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
    # A copy lease permits readers only; existing or new writers/deleters make
    # the native open fail before any output member can be created.
    sharing = 1 if exclusive else 7
    handle = kernel.CreateFileW(io_path(path), 0x80000000, sharing, None, 3, 0x00200000, None)
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


class ProtectionScanner:
    """Bounded stream inspection; an authority token is never stored in memory."""
    def __init__(self):
        self.private = False
        self.credential = False
        self.private_tail = b""
        self.url_tail = b""
        self.authority = False

    def feed(self, data: bytes) -> None:
        self.private |= bool(PRIVATE_MARKER.search(self.private_tail + data))
        self.private_tail = (self.private_tail + data)[-128:]
        if self.credential:
            return
        # Recognizing any :// is conservative. A scheme prefix cannot hide a
        # credential, however long it is or wherever a chunk boundary falls.
        payload = data if self.authority else self.url_tail + data
        self.url_tail = b""
        cursor = 0
        while cursor < len(payload):
            if not self.authority:
                start = payload.find(b"://", cursor)
                if start < 0:
                    self.url_tail = payload[cursor:][-2:]
                    break
                self.authority = True
                cursor = start + 3
            delimiter = None
            for match in re.finditer(br"[@/?#\s]", payload[cursor:]):
                value = match.group()
                if value == b"@":
                    # Userinfo need not contain a colon (RFC 3986, 3.2.1).
                    self.credential = True
                    return
                else:
                    delimiter = cursor + match.end()
                    break
            if delimiter is None:
                break
            self.authority = False
            cursor = delimiter


def hash_and_protection(path: Path) -> tuple[int, str, bool, bool]:
    count, digest, scanner = 0, hashlib.sha256(), ProtectionScanner()
    with open_source(path) as stream:
        while data := stream.read(BLOCK):
            count += len(data)
            digest.update(data)
            scanner.feed(data)
    return count, digest.hexdigest(), scanner.private, scanner.credential


def hash_file(path: Path) -> tuple[int, str, bool]:
    count, digest, private, _ = hash_and_protection(path)
    return count, digest, private


def file_identity(info: os.stat_result) -> dict:
    return {"bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "mode": stat.S_IMODE(info.st_mode), "device": info.st_dev,
            "inode": info.st_ino, "attributes": getattr(info, "st_file_attributes", 0)}


TRUSTED_PROVENANCE_REPORT_SHA256 = "59d6b4fe06d0baf9b43199b7c7c9ff7a5825d71227ef217b9732076c3c96a65c"
PROVENANCE_MAX_BYTES = 64 * BLOCK
PROOF_MAX_BYTES = 32 * BLOCK
PROVENANCE_KINDS = {
    "public_wheel_member": {"PUBLISHED_PYTHON_SYNTAX_OR_DOCUMENTATION_LITERAL", "PUBLISHED_PE_BINARY_PATTERN", "PUBLISHED_FORMAT_MARKER_P4_VALIDATED"},
    "owned_test_literal": {"OWNED_TEST_FIXTURE_LITERAL", "VERSION_SPECIFIC_TEST_FIXTURE_LITERAL"},
    "generated_cache": {"CURRENT_SOURCE_EQUIVALENT_GENERATED_CACHE", "HISTORICAL_SOURCE_EQUIVALENT_GENERATED_CACHE"},
}


def canonical_proof(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def bounded_proof_read(path: Path, maximum: int = PROOF_MAX_BYTES) -> bytes:
    before = lstat(path)
    require(stat.S_ISREG(before.st_mode) and not reparse(before) and before.st_size <= maximum,
            "provenance input is not an ordinary bounded file")
    with open_source(path) as stream:
        data = stream.read(maximum + 1)
    require(len(data) == before.st_size and len(data) <= maximum and file_identity(before) == file_identity(lstat(path)),
            "provenance input changed while reading")
    return data


def strict_proof_json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate provenance JSON key")
            result[key] = value
        return result
    def invalid_constant(_):
        raise PreservationError("non-finite provenance JSON value")
    try:
        result = json.loads(data, object_pairs_hook=unique, parse_constant=invalid_constant)
        require(isinstance(result, dict), "provenance document must be an object")
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise PreservationError("malformed provenance JSON") from None


def protected_positions(data: bytes) -> dict:
    # All occurrences are retained. The existing streaming scanner still gates
    # unknown bytes, including cross-block and unbounded URI authorities.
    private = [{"start": m.start(), "end": m.end()} for m in PRIVATE_MARKER.finditer(data)]
    uri = [{"scheme_separator_offset": m.start(), "at_offset": m.end() - 1}
           for m in re.finditer(br"://[^@/?#\s]*@", data)]
    require(len(private) + len(uri) <= 4096, "too many protected provenance positions")
    return {"private_markers": private, "userinfo": uri}


def position_binding(value: dict) -> dict:
    require(isinstance(value, dict) and set(value) == {"private_markers", "userinfo"}, "invalid position binding")
    result = {}
    for name, keys in (("private_markers", ("start", "end")), ("userinfo", ("scheme_separator_offset", "at_offset"))):
        require(isinstance(value[name], list) and len(value[name]) <= 4096, "invalid position list")
        rows = []
        for row in value[name]:
            require(isinstance(row, dict) and all(type(row.get(k)) is int and row[k] >= 0 for k in keys), "invalid protected position")
            require(row[keys[0]] < row[keys[1]], "invalid protected position interval")
            rows.append({k: row[k] for k in keys})
        require(rows == sorted(rows, key=lambda r: r[keys[0]]) and len({tuple(r.values()) for r in rows}) == len(rows),
                "duplicate or unordered protected position")
        result[name] = rows
    require(sum(map(len, result.values())) <= 4096, "too many bound positions")
    return result


def python_literal_constraints(data: bytes, positions: dict, *, owned_test: bool) -> None:
    try:
        text = data.decode("utf-8")
        tree = ast.parse(text, filename="<bound-provenance>")
        lines = text.splitlines(keepends=True)
        offsets, total = [], 0
        for line in lines:
            offsets.append(total)
            total += len(line.encode("utf-8"))
        def byte_at(line, col, *, ast_column=False):
            return offsets[line - 1] + (col if ast_column else len(lines[line - 1][:col].encode("utf-8")))
        constants, joined = [], []
        class Literals(ast.NodeVisitor):
            owner = "<module>"
            def visit_FunctionDef(self, node):
                old = self.owner
                self.owner = node.name
                self.generic_visit(node)
                self.owner = old
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_Constant(self, node):
                if isinstance(node.value, (str, bytes)):
                    value = node.value.encode("utf-8") if isinstance(node.value, str) else node.value
                    constants.append((byte_at(node.lineno, node.col_offset, ast_column=True),
                                      byte_at(node.end_lineno, node.end_col_offset, ast_column=True), self.owner, value))
            def visit_JoinedStr(self, node):
                joined.append((byte_at(node.lineno, node.col_offset, ast_column=True),
                               byte_at(node.end_lineno, node.end_col_offset, ast_column=True)))
                self.generic_visit(node)
        Literals().visit(tree)
        token_spans = [(byte_at(t.start[0], t.start[1]), byte_at(t.end[0], t.end[1]))
                       for t in tokenize.generate_tokens(io.StringIO(text).readline)
                       if t.type in {tokenize.STRING, tokenize.COMMENT}]
        for p in positions["userinfo"]:
            start, end = p["scheme_separator_offset"], p["at_offset"] + 1
            if owned_test:
                require(any(a <= start < end <= b and owner.startswith("test_") for a, b, owner, _ in constants),
                        "protected literal is not inside its bound test function")
            else:
                require(any(a <= start and start + 3 <= b for a, b in token_spans + joined),
                        "published pattern is not a Python literal, syntax template or comment")
        for p in positions["private_markers"]:
            require(any(a <= p["start"] < p["end"] <= b and PRIVATE_MARKER.fullmatch(value)
                        and (not owned_test or owner.startswith("test_")) for a, b, owner, value in constants),
                    "private marker is not an exact marker-only literal")
        if positions["private_markers"]:
            validate_fixture_marker(data)
    except (SyntaxError, UnicodeError, tokenize.TokenError, ValueError, IndexError, RecursionError):
        raise PreservationError("bound Python literal format cannot be validated") from None


def pe_pattern_constraints(data: bytes, positions: dict) -> None:
    require(len(data) >= 64 and data[:2] == b"MZ", "published binary is not a PE image")
    offset = struct.unpack_from("<I", data, 60)[0]
    require(64 <= offset <= len(data) - 24 and data[offset:offset + 4] == b"PE\0\0", "invalid PE header")
    sections, optional = struct.unpack_from("<H", data, offset + 6)[0], struct.unpack_from("<H", data, offset + 20)[0]
    table = offset + 24 + optional
    require(1 <= sections <= 96 and optional >= 64 and table + sections * 40 <= len(data), "invalid PE section table")
    require(struct.unpack_from("<H", data, offset + 24)[0] in {0x10B, 0x20B}, "unsupported PE optional header")
    for n in range(sections):
        size, start = struct.unpack_from("<II", data, table + n * 40 + 16)
        require(start + size <= len(data), "PE section exceeds the exact published member")
    for p in positions["userinfo"]:
        prefix = data[p["scheme_separator_offset"] + 3:p["at_offset"]]
        require(any(c < 32 or c == 127 for c in prefix), "binary candidate contains a printable authority requiring further proof")
    for p in positions["private_markers"]:
        require(data.rfind(b"\0", 0, p["start"]) + 1 == p["start"] and data.find(b"\0", p["end"]) == p["end"],
                "published binary private marker is not a marker-only C string")
    if positions["private_markers"]:
        validate_fixture_marker(data)


def code_shape(code: types.CodeType, depth: int = 0) -> tuple:
    require(depth < 100, "generated code nesting exceeds bounds")
    def constant(value, nesting=depth):
        require(nesting < 100, "generated constant nesting exceeds bounds")
        if isinstance(value, types.CodeType):
            return ("code", code_shape(value, nesting + 1))
        if isinstance(value, (tuple, frozenset)):
            require(depth < 100 and len(value) <= 100000, "generated constant nesting exceeds bounds")
            # Sets have no serialization order. Tuple order remains significant.
            children = [constant(v, nesting + 1) for v in value]
            return (type(value).__name__, frozenset(children) if isinstance(value, frozenset) else tuple(children))
        require(value is Ellipsis or type(value) in {str, bytes, int, bool, float, complex, type(None)}, "unsupported generated constant")
        return (type(value).__name__, value)
    fields = ("co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals", "co_stacksize", "co_flags", "co_code",
              "co_names", "co_varnames", "co_freevars", "co_cellvars", "co_name", "co_qualname", "co_firstlineno", "co_linetable", "co_exceptiontable")
    return tuple(getattr(code, name) for name in fields) + (tuple(constant(v) for v in code.co_consts),)


def cache_literal_constraints(code: types.CodeType) -> None:
    stack, visited = [(code, 0)], 0
    while stack:
        value, depth = stack.pop()
        visited += 1
        require(depth < 100 and visited <= 100000, "generated literal traversal exceeds bounds")
        if isinstance(value, types.CodeType):
            scanner = ProtectionScanner()
            scanner.feed(value.co_filename.encode("utf-8"))
            require(not scanner.private and not scanner.credential, "cache filename contains additional protected content")
            stack.extend((v, depth + 1) for v in value.co_consts)
        elif isinstance(value, (tuple, frozenset)):
            stack.extend((v, depth + 1) for v in value)
        elif isinstance(value, (str, bytes)):
            literal = value.encode("utf-8") if isinstance(value, str) else value
            if PRIVATE_MARKER.search(literal):
                require(PRIVATE_MARKER.fullmatch(literal), "cache contains encoded or extended private-marker content")


class ContentProvenance:
    """A bounded consumer of the root-vetted HP2 proof, not a proof issuer."""
    def __init__(self, data: dict, policy):
        require(isinstance(data, dict) and set(data) == {"proof_bundle", "snapshot_inventory", "report_sha256", "entries"}, "invalid content provenance declaration")
        require(data["report_sha256"] == TRUSTED_PROVENANCE_REPORT_SHA256, "provenance report is not the root-vetted frozen anchor")
        self.policy = policy
        self.observed_generator_aliases = None
        self.bundle = safe_components(Path(data["proof_bundle"]))
        self.inputs = {}
        def document(path, digest):
            payload = bounded_proof_read(path)
            require(sha(payload) == digest, "frozen provenance proof hash differs")
            self.inputs[str(path)] = digest
            return strict_proof_json(payload)
        self.report = document(self.bundle / "HP2-FINAL-REPORT.json", data["report_sha256"])
        require(self.report.get("schema_version") == 1 and self.report.get("held_count") == 69 and self.report.get("admitted_count") == 0,
                "invalid frozen provenance report shape")
        self.source_root = policy.authorize(Path(self.report["approved_source_root"]), "source_roots")
        self.evidence = {}
        for name, item in self.report["evidence"].items():
            require(relative_name(name).name == name, "proof member must be one safe filename")
            self.evidence[name] = document(self.bundle / name, item["sha256"])
        inventory_path = safe_components(Path(data["snapshot_inventory"]))
        inventory = document(inventory_path, self.report["sealed_HP1_checkpoint_current_hashes"]["inventory_sha256"])
        require(same_path(Path(inventory["source_root"]), self.source_root) and inventory.get("git"), "frozen alias inventory identity differs")
        self.aliases = inventory["git"]["object_path_provenance"]["blobs"]
        self.records = {e["entry_id"]: e for e in self.report["entries"]}
        require(len(self.records) == len(self.report["entries"]) == 69, "duplicate frozen entry identity")
        self.entries, self.locations = {}, {}
        require(isinstance(data["entries"], list) and len(data["entries"]) <= 69, "invalid content provenance entry list")
        for original in data["entries"]:
            entry = copy.deepcopy(original)
            require(isinstance(entry, dict), "invalid content provenance entry")
            base_keys = {"entry_id", "kind", "source_root", "sha256"}
            require(set(entry) in (base_keys | {"path"}, base_keys | {"git_oid", "aliases"}), "invalid provenance identity fields")
            record = self.records.get(entry["entry_id"])
            require(record is not None and entry["kind"] in PROVENANCE_KINDS and record["classification"] in PROVENANCE_KINDS[entry["kind"]],
                    "entry has no supported typed proof; held entries remain held")
            require(same_path(policy.authorize(Path(entry["source_root"]), "source_roots"), self.source_root)
                    and entry["sha256"] == record["whole_file_sha256"], "provenance root or whole-byte binding differs")
            entry["source_root"] = str(self.source_root)
            if "path" in entry:
                require(record["kind"] == "working" and str(relative_name(entry["path"])) == record["path"], "provenance path identity differs")
                location = ("file", entry["path"])
            else:
                require(record["kind"] == "historical" and entry["git_oid"] == record["git_oid"] and OID.fullmatch(entry["git_oid"]), "provenance object identity differs")
                require(isinstance(entry["aliases"], list) and entry["aliases"] == self.aliases.get(entry["git_oid"]) and bool(entry["aliases"]), "complete canonical alias binding differs")
                for name in entry["aliases"]:
                    relative_name(name)
                location = ("blob", entry["git_oid"])
            require(entry["entry_id"] not in self.entries and location not in self.locations, "duplicate provenance identity")
            position_binding(record["source_positions"])
            self.entries[entry["entry_id"]] = entry
            self.locations[location] = entry
            if entry["kind"] == "public_wheel_member":
                self.public_member(entry)
            elif entry["kind"] == "generated_cache":
                self.generator(entry)

    def recheck(self) -> None:
        for name, digest in self.inputs.items():
            require(sha(bounded_proof_read(safe_components(Path(name)))) == digest, "frozen provenance proof became stale or changed")

    def public_member(self, entry: dict) -> dict:
        matches = [(group, item) for group in self.evidence["upstream-artifact-comparison-r1.json"]["groups"]
                   for item in group["entries"] if item["id"] == entry["entry_id"]]
        require(len(matches) == 1, "no independent published wheel-member equality proof")
        group, item = matches[0]
        require(group["artifact_hash_matches_pypi"] is True and group["all_target_members_match"] is True
                and group["downloaded_bytes"] == group["artifact"]["size"] and group["artifact"]["filename"].endswith(".whl")
                and re.fullmatch(r"[0-9a-f]{64}", group["artifact"]["sha256"])
                and group["pypi_json_url"].startswith("https://pypi.org/pypi/")
                and group["artifact"]["url"].startswith("https://files.pythonhosted.org/packages/")
                and item["whole_file_match"] is True and item["local_source_path"] == entry["path"]
                and item["wheel_member_sha256"] == item["local_whole_file_sha256"] == entry["sha256"]
                and item["wheel_member_bytes"] == item["local_bytes"] == self.records[entry["entry_id"]]["bytes"], "published member proof is inconsistent")
        relative_name(item["wheel_member"])
        return item

    def generator(self, entry: dict) -> tuple[dict, dict]:
        records = [v for v in self.evidence["format-context-followup-r2.json"]["pyc"] if v["id"] == entry["entry_id"]]
        require(len(records) == 1, "missing exact cache decoder proof")
        cache = records[0]
        require(cache["sha256"] == entry["sha256"] and cache["marshal_all_body_consumed"] is True, "invalid cache proof")
        descriptor = {"source_root": str(self.source_root)}
        if self.records[entry["entry_id"]]["classification"] == "CURRENT_SOURCE_EQUIVALENT_GENERATED_CACHE":
            require(cache["all_structural_code_fields_and_constants_equal"] is True, "cache generator was not qualified")
            name = str(relative_name(cache["associated_source"]))
            support = self.evidence["format-context-followup-r2.json"]["source_support_before_after"][str(child(self.source_root, name))]
            require(support["sha256"] == cache["associated_source_sha256"], "whole-byte current generator proof differs")
            descriptor.update(kind="current_source", path=name, sha256=support["sha256"], bytes=support["bytes"])
        else:
            links = [v for v in self.evidence["historical-cache-generator-links-r1.json"]["entries"] if v["entry_id"] == entry["entry_id"]]
            require(len(links) == 1 and links[0]["pyc_sha256"] == entry["sha256"] and len(links[0]["exact_historical_structural_matches"]) == 1,
                    "historical cache has no unique exact generator")
            match = links[0]["exact_historical_structural_matches"][0]
            require(match["header_source_size_match"] is True and OID.fullmatch(match["git_oid"]), "invalid historical generator proof")
            descriptor.update(kind="historical_blob", git_oid=match["git_oid"], aliases=self.aliases.get(match["git_oid"]),
                              sha256=match["source_sha256"], bytes=match["source_bytes"])
            require(bool(descriptor["aliases"]), "historical generator lacks canonical aliases")
        require(type(descriptor["bytes"]) is int and 0 < descriptor["bytes"] <= PROVENANCE_MAX_BYTES, "invalid generator byte bound")
        descriptor["member"] = sha(canonical_proof(descriptor)) + ".py"
        return cache, descriptor

    def generator_bytes(self, descriptor: dict) -> bytes:
        require(self.generator_permitted(descriptor, require_observed=True), "generator is blocked or lacks current complete alias admission")
        if descriptor["kind"] == "current_source":
            data = bounded_proof_read(safe_components(child(self.source_root, descriptor["path"])), PROVENANCE_MAX_BYTES)
        else:
            require(int(text_git(self.source_root, "cat-file", "-s", descriptor["git_oid"])) == descriptor["bytes"], "historical generator size differs")
            data = git(self.source_root, "cat-file", "blob", descriptor["git_oid"])
        require(len(data) == descriptor["bytes"] and sha(data) == descriptor["sha256"], "exact generator changed")
        return data

    def locations_permitted(self, names: list[str]) -> bool:
        return bool(names) and all((self.policy.classify(self.source_root, name) or {}).get("kind")
                                  not in {"live_profile", "private_key", "unknown"} for name in names)

    def observe_generator_aliases(self, root: Path, view: dict | None) -> None:
        """Observe complete tree/index names before reading a historical producer."""
        self.observed_generator_aliases = None
        if not same_path(root, self.source_root):
            return
        historical = [self.generator(entry)[1] for entry in self.entries.values()
                      if entry["kind"] == "generated_cache"
                      and self.generator(entry)[1]["kind"] == "historical_blob"]
        if not historical:
            return
        require(view is not None, "historical generators require a private current index observation")
        objects = []
        for line in text_git(root, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)").splitlines():
            oid, kind, size = line.split()
            require(OID.fullmatch(oid) is not None and kind in {"blob", "tree", "commit", "tag"}
                    and size.isdigit(), "invalid generator observation object")
            objects.append({"oid": oid, "type": kind, "bytes": int(size)})
        self.observed_generator_aliases = git_object_paths(root, objects, view)["blobs"]

    def generator_permitted(self, descriptor: dict, *, require_observed: bool) -> bool:
        if descriptor["kind"] == "current_source":
            return self.locations_permitted([descriptor["path"]])
        names = descriptor["aliases"]
        if not self.locations_permitted(names):
            return False
        if require_observed:
            actual = (self.observed_generator_aliases or {}).get(descriptor["git_oid"])
            return actual == names and self.locations_permitted(actual or [])
        return True

    def cache_constraints(self, entry: dict, data: bytes, provider=None) -> None:
        cache, descriptor = self.generator(entry)
        require(self.generator_permitted(descriptor, require_observed=provider is None), "generator is blocked or lacks current complete alias admission")
        require(cache["interpreter"] == sys.version and cache["magic_hex"] == importlib.util.MAGIC_NUMBER.hex(), "exact generator interpreter is unavailable")
        require(len(data) >= 16 and data[:4] == importlib.util.MAGIC_NUMBER, "cache magic differs")
        flags = struct.unpack_from("<I", data, 4)[0]
        require(flags in {0, 1, 3}, "invalid cache header flags")
        source = provider(descriptor) if provider is not None else self.generator_bytes(descriptor)
        require(len(source) == descriptor["bytes"] and sha(source) == descriptor["sha256"], "bound generator bytes differ")
        if flags == 0:
            require(struct.unpack_from("<I", data, 12)[0] == len(source), "cache header generator size differs")
        else:
            require(data[8:16] == importlib.util.source_hash(source), "cache source hash differs")
        positions = protected_positions(source)
        if positions["userinfo"]:
            location = ("file", descriptor["path"]) if descriptor["kind"] == "current_source" else ("blob", descriptor["git_oid"])
            source_entry = self.locations.get(location)
            require(source_entry is not None and source_entry["kind"] in {"public_wheel_member", "owned_test_literal"}, "protected generator has no independent literal proof")
            require(self.validate(self.source_root, source, path=descriptor.get("path"), oid=descriptor.get("git_oid"), aliases=descriptor.get("aliases")) is not None,
                    "protected generator literal proof failed")
        if positions["private_markers"]:
            python_literal_constraints(source, positions, owned_test=False)
        try:
            stream = io.BytesIO(data[16:])
            code = marshal.load(stream)
            require(stream.tell() == len(data) - 16 and isinstance(code, types.CodeType), "cache marshal body is incomplete or has trailing content")
            cache_literal_constraints(code)
            expected = compile(source, "<bound-generator>", "exec", dont_inherit=True, optimize=0)
            require(code_shape(code) == code_shape(expected), "cache does not match its exact generator")
        except (ValueError, TypeError, EOFError, SyntaxError, RecursionError):
            raise PreservationError("generated cache format could not be validated") from None

    def receipt(self, entry: dict) -> dict:
        value = {"identity": copy.deepcopy(entry), "report_sha256": TRUSTED_PROVENANCE_REPORT_SHA256,
                 "positions_sha256": sha(canonical_proof(position_binding(self.records[entry["entry_id"]]["source_positions"]))) }
        if entry["kind"] == "generated_cache":
            value["generator"] = self.generator(entry)[1]
        return value

    def validate(self, root: Path, data: bytes, *, path=None, oid=None, aliases=None, provider=None) -> dict | None:
        if not same_path(root, self.source_root):
            return None
        entry = self.locations.get(("file", path) if oid is None else ("blob", oid))
        if entry is not None and not self.locations_permitted([entry["path"]] if "path" in entry else entry["aliases"]):
            return None
        if entry is None or len(data) != self.records[entry["entry_id"]]["bytes"] or sha(data) != entry["sha256"]:
            return None
        if oid is not None and aliases != entry["aliases"]:
            return None
        try:
            positions = protected_positions(data)
            require(positions == position_binding(self.records[entry["entry_id"]]["source_positions"]), "new or changed protected positions")
            if entry["kind"] == "public_wheel_member":
                self.public_member(entry)
                if self.records[entry["entry_id"]]["classification"] == "PUBLISHED_PE_BINARY_PATTERN" or data.startswith(b"MZ"):
                    pe_pattern_constraints(data, positions)
                else:
                    python_literal_constraints(data, positions, owned_test=False)
            elif entry["kind"] == "owned_test_literal":
                python_literal_constraints(data, positions, owned_test=True)
            else:
                self.cache_constraints(entry, data, provider)
            return self.receipt(entry)
        except (PreservationError, OSError, KeyError, struct.error):
            return None

    def checkpoint_binding(self, used: list[dict]) -> dict:
        identities = sorted({v["identity"]["entry_id"] for v in used})
        for value in used:
            entry = self.entries.get(value["identity"]["entry_id"])
            require(entry is not None and value == self.receipt(entry), "stored provenance receipt differs")
        receipts = [self.receipt(self.entries[identity]) for identity in identities]
        generators = {r["generator"]["member"]: r["generator"] for r in receipts if "generator" in r}
        return {"report_sha256": TRUSTED_PROVENANCE_REPORT_SHA256, "receipts": receipts,
                "generators": [generators[k] for k in sorted(generators)]}


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
            require(not any(existing[0] == key[0] and existing[2] == identity
                            and equivalent_blocked_path(existing[1], name) for existing in self.classifications),
                    f"duplicate Windows-equivalent classification: {name}")
            self.classifications[key] = entry
        for declared in data.get("declared_inputs", []):
            path = safe_components(Path(declared["path"]))
            require(any(inside(path, r) for r in self.paths["source_roots"]), f"declared input outside authorized source: {path}")
            require(stat.S_ISREG(lstat(path).st_mode), f"declared input is not ordinary: {path}")
            _, value, _ = hash_file(path)
            require(value == declared["sha256"], f"declared input hash differs: {path}")
        try:
            self.provenance = ContentProvenance(data["content_provenance"], self) if "content_provenance" in data else None
        except (KeyError, TypeError, ValueError, RecursionError):
            raise PreservationError("malformed content provenance binding") from None

    def authorize(self, path: Path, key: str, *, missing: bool = False) -> Path:
        actual = safe_components(path, allow_missing=missing)
        require(any(same_path(actual, p) for p in self.paths[key]), f"not explicitly authorized in {key}: {actual}")
        return actual

    def classify(self, root: Path, name: str, digest: str | None = None) -> dict | None:
        relative_name(name)
        prefix = (os.path.normcase(str(root)), name)
        # A current block fences every equivalent Windows spelling, including
        # digest-specific and historical reads. Positive admission remains exact.
        for key, value in self.classifications.items():
            if key[0] == prefix[0] and key[2] == "BLOCKED_CURRENT" and equivalent_blocked_path(key[1], name):
                return value
        if digest is not None:
            return self.classifications.get((*prefix, digest))
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
    bound = policy.provenance and same_path(root, policy.provenance.source_root) and ("file", name) in policy.provenance.locations
    if potential_sensitive(name) and not classification and not bound:
        return {**result, "kind": "pending_sensitive", "contents": "NOT_READ_OR_COPIED", "classification": "PROVENANCE_REQUIRED"}
    count, digest, private, credential = hash_and_protection(path)
    require(file_identity(first) == file_identity(lstat(path)), f"file changed while hashing: {path}")
    require(count == first.st_size, f"file size changed while hashing: {path}")
    if classification:
        classification = policy.classify(root, name, digest)
        if classification is None:
            return {**result, "kind": "pending_sensitive", "contents": "HASHED_UNCLASSIFIED_CURRENT_BYTES_NOT_COPIED",
                    "sha256": digest, "classification": "EXACT_CURRENT_BYTES_PROVENANCE_REQUIRED"}
    if bound:
        payload = bounded_proof_read(path, PROVENANCE_MAX_BYTES)
        require(sha(payload) == digest, "bound source changed after protection scanning")
        admitted = policy.provenance.validate(root, payload, path=name)
        if admitted is None:
            return {**result, "kind": "pending_sensitive", "contents": "BOUND_PROVENANCE_REFUSED_NOT_COPIED",
                    "sha256": digest, "classification": "CURRENT_BYTES_FORMAT_OR_GENERATOR_PROOF_REQUIRED"}
        return {**result, "sha256": digest, "provenance": admitted}
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
    if credential:
        return {**result, "kind": "pending_sensitive", "contents": "SCANNED_CREDENTIAL_LOCATION_NOT_COPIED",
                "sha256": digest, "classification": "CREDENTIAL_URL_OBSERVED"}
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


def git_metadata_preflight(root: Path, policy: Policy) -> dict | None:
    """Reject pending metadata before any observation, scratch or archive copy."""
    if not exists(root / ".git"):
        return None
    local, common = discover_git_dirs(root, policy)
    areas = {"common": (common, tree_inventory(common, policy, skip_objects=True))}
    if not same_path(local, common):
        areas["worktree"] = (local, tree_inventory(local, policy))
    require(not any(e["kind"] == "pending_sensitive" for _, entries in areas.values() for e in entries),
            "Git metadata is pending sensitive; capture refused before observation copies")
    return {"local": local, "common": common, "areas": areas}


def observation_bytes(path: Path, entry: dict) -> bytes:
    """Pin admitted metadata bytes before writing them to any observation path."""
    first = lstat(path)
    require(entry["kind"] == "file" and file_identity(first) == {k: entry[k] for k in file_identity(first)},
            "Git metadata identity changed before observation copy")
    payload = read_bytes(path)
    require(len(payload) == entry["bytes"] and sha(payload) == entry["sha256"],
            "Git metadata bytes changed before observation copy")
    require(file_identity(first) == file_identity(lstat(path)), "Git metadata changed during observation read")
    return payload


def create_read_view(root: Path, policy: Policy, target: Path) -> dict | None:
    """Private index observation prevents Git's split-index mtime writes to source."""
    preflight = git_metadata_preflight(root, policy)
    if preflight is None:
        return None
    local, common = preflight["local"], preflight["common"]
    common_entries = {e["path"]: e for e in preflight["areas"]["common"][1]}
    index_scope = "common" if same_path(local, common) else "worktree"
    local_entries = {e["path"]: e for e in preflight["areas"][index_scope][1]}
    require(not exists(target), "index observation target already exists")
    os.mkdir(io_path(target))
    os.mkdir(io_path(target / "objects"))
    os.mkdir(io_path(target / "refs"))
    os.mkdir(io_path(target / "info"))
    write_new(target / "HEAD", observation_bytes(local / "HEAD", local_entries["HEAD"]))
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
                write_new(target / entry.name, observation_bytes(local / entry.name, local_entries[entry.name]))
    for name in ("exclude", "attributes"):
        path = common / "info" / name
        if exists(path):
            write_new(target / "info" / name, observation_bytes(path, common_entries["info/" + name]))
    after = git_metadata_preflight(root, policy)
    require(preflight == after, "Git metadata changed during observation creation")
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
    # Ref ancestry is not the full object database. Orphan trees also retain
    # historical paths that an output exclusion may not conceal.
    for line in text_git(root, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)").splitlines():
        oid, kind = line.split()
        if kind == "tree":
            require(not git(root, "ls-tree", "-r", "-z", oid, "--", name),
                    "active output exclusion intersects historical work in retained trees")


def git_object_paths(root: Path, objects: list[dict], view: dict) -> dict:
    """Map every retained tree context and every staged index entry to blobs."""
    types = {o["oid"]: o["type"] for o in objects}
    trees, children, roots = {}, set(), set()
    for oid, kind in sorted(types.items()):
        if kind == "commit":
            roots.add(text_git(root, "rev-parse", oid + "^{tree}"))
        elif kind == "tag":
            target = text_git(root, "rev-parse", oid + "^{}")
            if types.get(target) == "tree":
                roots.add(target)
        if kind != "tree":
            continue
        entries = []
        for item in git(root, "ls-tree", "-z", oid).split(b"\0"):
            if not item:
                continue
            metadata, raw_name = item.split(b"\t", 1)
            mode, entry_type, target = metadata.decode("ascii").split()
            path_scan = ProtectionScanner()
            path_scan.feed(raw_name)
            require(not path_scan.private and not path_scan.credential,
                    "retained tree path requires protected provenance; capture refused")
            name = str(relative_name(raw_name.decode("utf-8")))
            require("/" not in name, "tree entry is not a single path component")
            require(entry_type in {"blob", "tree", "commit"}, "unknown tree entry type")
            if entry_type != "commit":
                require(types.get(target) == entry_type, "retained tree refers to a missing object")
            entries.append((entry_type, target, name))
            if entry_type == "tree":
                children.add(target)
        trees[oid] = entries
    roots.update(set(trees) - children)
    by_blob, visited = {}, set()
    for origin in sorted(roots):
        require(origin in trees, "retained commit or tag has no complete root tree")
        stack = [(origin, "", frozenset())]
        while stack:
            oid, prefix, ancestors = stack.pop()
            require(oid not in ancestors, "retained tree graph contains a cycle")
            visited.add(oid)
            for kind, target, name in trees[oid]:
                path = prefix + name
                relative_name(path)
                if kind == "tree":
                    stack.append((target, path + "/", ancestors | {oid}))
                elif kind == "blob":
                    by_blob.setdefault(target, set()).add(path)
    require(visited == set(trees), "retained trees have incomplete path provenance")
    index = []
    for item in view_git(root, view, "ls-files", "--stage", "-z").split(b"\0"):
        if not item:
            continue
        metadata, raw_name = item.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        name = str(relative_name(raw_name.decode("utf-8")))
        require(stage in {"0", "1", "2", "3"} and OID.fullmatch(oid), "invalid index object identity")
        index.append({"path": name, "oid": oid, "mode": mode, "stage": int(stage)})
        if mode != "160000" and set(oid) != {"0"}:
            require(types.get(oid) == "blob", "index refers to a missing retained blob")
            by_blob.setdefault(oid, set()).add(name)
    return {"blobs": {oid: sorted(paths) for oid, paths in sorted(by_blob.items())},
            "root_trees": sorted(roots), "all_trees_observed": sorted(visited),
            "index_entries": sorted(index, key=lambda e: (e["path"], e["stage"]))}


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
    object_paths = git_object_paths(root, objects, view)
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
            "object_path_provenance": object_paths,
            "status_b64": base64.b64encode(view_git(root, view, "status", "--porcelain=v2", "-z", "--untracked-files=all", *pathspec)).decode(),
            "worktrees_b64": base64.b64encode(git(root, "worktree", "list", "--porcelain", "-z")).decode(),
            "working_patch_b64": None if protected_paths else base64.b64encode(view_git(root, view, "diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv", *pathspec)).decode(),
            "staged_patch_b64": None if protected_paths else base64.b64encode(view_git(root, view, "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "--no-textconv", *pathspec)).decode(),
            "protected_working_paths": protected_paths,
            "git_pointer_b64": base64.b64encode(pointer).decode() if pointer is not None else None, "metadata": metadata,
            "original_object_storage": tree_inventory(common / "objects", policy)}


def snapshot(root: Path, policy: Policy, exclusion: Path | None, view: dict | None = None) -> dict:
    if policy.provenance:
        policy.provenance.observe_generator_aliases(root, view)
    entries = tree_inventory(root, policy, exclude=exclusion, skip_git=True)
    protected = [e["path"] for e in entries if e["kind"] == "pending_sensitive"]
    state = git_state(root, policy, exclusion, view, protected)
    if policy.provenance:
        for entry in entries:
            descriptor = entry.get("provenance", {}).get("generator")
            if descriptor and descriptor["kind"] == "historical_blob":
                actual = state["object_path_provenance"]["blobs"].get(descriptor["git_oid"]) if state else None
                if actual != descriptor["aliases"]:
                    entry.pop("provenance")
                    entry.update(kind="pending_sensitive", contents="GENERATOR_ALIAS_PROVENANCE_REFUSED_NOT_COPIED",
                                 classification="CURRENT_COMPLETE_GENERATOR_ALIASES_REQUIRED")
                    protected.append(entry["path"])
        if state and protected:
            state["protected_working_paths"] = sorted(set(protected))
            state["working_patch_b64"] = state["staged_patch_b64"] = None
    return {"source_root": str(root), "entries": entries, "git": state}


def stream_objects(root: Path, objects: list[dict]):
    """Scan every object payload in bounded chunks, without exporting its bytes."""
    proc = subprocess.Popen(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-C", str(root), "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=git_environment())
    try:
        assert proc.stdin is not None and proc.stdout is not None
        for obj in objects:
            proc.stdin.write((obj["oid"] + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode("ascii").strip().split()
            require(header == [obj["oid"], obj["type"], str(obj["bytes"])], "Git object stream differs from inventory")
            remaining, scanner, sample, digest = obj["bytes"], ProtectionScanner(), bytearray(), hashlib.sha256()
            while remaining:
                data = proc.stdout.read(min(BLOCK, remaining))
                require(bool(data), "Git object stream ended early")
                remaining -= len(data)
                digest.update(data)
                scanner.feed(data)
                if len(sample) < 4096:
                    sample.extend(data[:4096 - len(sample)])
            require(proc.stdout.read(1) == b"\n", "Git object boundary differs")
            yield {"oid": obj["oid"], "type": obj["type"], "private": scanner.private,
                   "credential": scanner.credential, "sha256": digest.hexdigest(), "sample": bytes(sample)}
        proc.stdin.close()
        require(proc.wait(timeout=30) == 0, "Git object inspection failed")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None and not stream.closed:
                stream.close()


def stream_object_blobs(root: Path, objects: list[dict]):
    """Retain the former blob iterator interface for callers; gate uses all types."""
    for observed in stream_objects(root, objects):
        if observed["type"] == "blob":
            yield observed["oid"], observed["private"], observed["sample"]


def git_sensitive(root: Path, state: dict, policy: Policy, *, observation_root: Path | None = None,
                  generator_provider=None, admitted_objects: list | None = None) -> list[dict]:
    pending = []
    by_blob = state["object_path_provenance"]["blobs"]
    reader = observation_root or root
    for observed in stream_objects(reader, state["objects"]):
        oid, kind, digest = observed["oid"], observed["type"], observed["sha256"]
        paths = by_blob.get(oid, []) if kind == "blob" else []
        bound = (policy.provenance and kind == "blob" and paths and same_path(root, policy.provenance.source_root)
                 and ("blob", oid) in policy.provenance.locations)
        if bound and (observed["credential"] or observed["private"]):
            entry = policy.provenance.locations[("blob", oid)]
            blocked = any((policy.classify(root, name) or {}).get("kind") in {"live_profile", "private_key", "unknown"} for name in paths)
            admitted = None
            if not blocked and digest == entry["sha256"] and policy.provenance.records[entry["entry_id"]]["bytes"] <= PROVENANCE_MAX_BYTES:
                admitted = policy.provenance.validate(root, git(reader, "cat-file", "blob", oid), oid=oid, aliases=paths, provider=generator_provider)
            if admitted is not None:
                if admitted_objects is not None:
                    admitted_objects.append(admitted)
                continue
        if observed["credential"]:
            pending.append({"git_object": oid, "object_type": kind, "kind": "credential_url_candidate", "contents": "SCANNED_NOT_COPIED"})
            continue
        if kind != "blob":
            if observed["private"]:
                pending.append({"git_object": oid, "object_type": kind, "kind": "private_key_candidate", "contents": "SCANNED_NOT_COPIED"})
            continue
        if not paths:
            pending.append({"git_object": oid, "kind": "unknown_path_provenance", "sha256": digest, "contents": "SCANNED_NOT_COPIED"})
            continue
        approved = [policy.classify(root, name, digest) for name in paths]
        if observed["private"]:
            # A known alias must not launder an unknown alias of the same bytes.
            if not all(c and c["kind"] == "fixture_secret_marker" for c in approved):
                pending.append({"git_object": oid, "kind": "private_key_candidate", "contents": "SCANNED_NOT_COPIED"})
                continue
            validate_fixture_marker(git(reader, "cat-file", "blob", oid))
        for name, classification in zip(paths, approved):
            current = policy.classify(root, name)
            if current and current["kind"] in {"live_profile", "private_key", "unknown"}:
                pending.append({"git_object": oid, "path": name, "kind": "blocked_location", "contents": "NOT_COPIED"})
                continue
            sensitive = potential_sensitive(name) or observed["sample"].startswith(b"SQLite format 3\x00")
            if not sensitive and classification is None:
                continue
            if not classification or classification["kind"] not in {"fixture_database", "public_certificate", "fixture_secret_marker"}:
                pending.append({"git_object": oid, "path": name, "sha256": digest, "kind": "provenance_required", "contents": "NOT_COPIED"})
                continue
            payload = git(reader, "cat-file", "blob", oid)
            require(sha(payload) == digest == classification["sha256"], "classified Git object bytes changed")
            if classification["kind"] == "public_certificate":
                validate_public_certificate(payload)
            elif classification["kind"] == "fixture_secret_marker":
                validate_fixture_marker(payload)
            else:
                require(payload.startswith(b"SQLite format 3\x00"), "classified Git object is not fixture SQLite")
    return pending


def add_file(archive: zipfile.ZipFile, source: Path, entry: dict, name: str) -> None:
    before = lstat(source)
    require(not reparse(before) and stat.S_ISREG(before.st_mode), f"file became nonordinary: {source}")
    require(file_identity(before) == {k: entry[k] for k in file_identity(before)}, f"file identity changed before copy: {source}")
    with open_source(source, exclusive=True) as stream:
        require(file_identity(before) == file_identity(lstat(source)), f"source identity changed before copy admission: {source}")
        count, digest = 0, hashlib.sha256()
        while data := stream.read(BLOCK):
            count += len(data)
            digest.update(data)
        require(count == entry["bytes"] and digest.hexdigest() == entry["sha256"], f"source changed before immutable copy admission: {source}")
        require(file_identity(before) == file_identity(lstat(source)), f"source identity changed during copy admission: {source}")
        safe_components(source)
        stream.seek(0)
        count, digest = 0, hashlib.sha256()
        with archive.open(name, "w", force_zip64=True) as target:
            while data := stream.read(BLOCK):
                count += len(data)
                digest.update(data)
                target.write(data)
        require(count == entry["bytes"] and digest.hexdigest() == entry["sha256"], f"source changed during immutable copy: {source}")
        require(file_identity(before) == file_identity(lstat(source)), f"source identity changed during immutable copy: {source}")


def archive_tree(path: Path, root: Path, entries: list[dict], *, admitted_metadata: bool = False, policy: Policy | None = None) -> None:
    with zipfile.ZipFile(io_path(path), "x", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for entry in entries:
            if entry["kind"] == "file":
                if entry.get("provenance"):
                    require(policy is not None and policy.provenance is not None, "copy lacks its current provenance policy")
                    policy.provenance.recheck()
                source = child(root, entry["path"])
                if admitted_metadata:
                    payload = observation_bytes(source, entry)
                    with archive.open(entry["path"], "w", force_zip64=True) as target:
                        target.write(payload)
                else:
                    add_file(archive, source, entry, entry["path"])


def export_objects(root: Path, state: dict, path: Path) -> None:
    data = "".join(o["oid"] + "\n" for o in state["objects"]).encode()
    with open(io_path(path), "xb") as stream:
        completed = subprocess.run(["git", "--no-optional-locks", "-c", "core.longpaths=true", "-C", str(root), "pack-objects", "--stdout"],
                                   input=data, stdout=stream, stderr=subprocess.PIPE, env=git_environment())
    require(completed.returncode == 0, "independent Git object export failed")


def capture(root: Path, destination: Path, policy: Policy, *, active_output_exclusion: Path | None = None) -> dict:
    root = policy.authorize(root, "source_roots")
    if policy.provenance:
        policy.provenance.recheck()
    destination = policy.authorize(destination, "capture_targets", missing=True)
    require(not exists(destination), "capture destination already exists; overwrite refused")
    safe_components(destination.parent)
    require(not any(inside(source, destination) for source in policy.paths["source_roots"]), "capture target contains an authorized source")
    require(not any(inside(destination, area) or inside(area, destination) for area in policy.paths["git_roots"]),
            "capture target intersects original Git metadata")
    if exists(root / ".git"):
        discover_git_dirs(root, policy)
        git_metadata_preflight(root, policy)
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
        admitted_objects = []
        if state:
            for scope, entries in state["metadata"].items():
                pending.extend({**e, "git_metadata_scope": scope} for e in entries if e["kind"] == "pending_sensitive")
            pending.extend(git_sensitive(root, state, policy, admitted_objects=admitted_objects)
                           if policy.provenance else git_sensitive(root, state, policy))
        if policy.provenance:
            archive_tree(destination / "working-tree.zip", root, before["entries"], policy=policy)
        else:
            archive_tree(destination / "working-tree.zip", root, before["entries"])
        artifacts.append("working-tree.zip")
        if state:
            for scope, entries in state["metadata"].items():
                name = f"git-{scope}-metadata.zip"
                archive_tree(destination / name, Path(state["metadata_roots"][scope]), entries, admitted_metadata=True)
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
        if policy.provenance:
            policy.provenance.recheck()
        recorded = copy.deepcopy(before)
        if policy.provenance:
            used = [e["provenance"] for e in before["entries"] if e.get("provenance")] + admitted_objects
            recorded["provenance_objects"] = admitted_objects
            recorded["content_provenance"] = policy.provenance.checkpoint_binding(used)
            if not pending and recorded["content_provenance"]["generators"]:
                with zipfile.ZipFile(io_path(destination / "provenance-generators.zip"), "x", compression=zipfile.ZIP_STORED) as archive:
                    for descriptor in recorded["content_provenance"]["generators"]:
                        archive.writestr(descriptor["member"], policy.provenance.generator_bytes(descriptor))
                artifacts.append("provenance-generators.zip")
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


def checkpoint_generator_provider(path: Path, descriptors: list[dict]):
    allowed = {d["member"]: d for d in descriptors}
    require(len(allowed) == len(descriptors), "duplicate generator archive member")
    if descriptors:
        with zipfile.ZipFile(io_path(path / "provenance-generators.zip")) as archive:
            require(len(archive.infolist()) == len(allowed) and set(archive.namelist()) == set(allowed), "generator archive membership differs")
            for item in archive.infolist():
                require(re.fullmatch(r"[0-9a-f]{64}\.py", item.filename) and not stat.S_ISLNK(item.external_attr >> 16)
                        and item.file_size == allowed[item.filename]["bytes"] <= PROVENANCE_MAX_BYTES, "unsafe generator archive entry")
    def provider(descriptor):
        require(descriptor == allowed.get(descriptor["member"]), "generator archive identity differs")
        with zipfile.ZipFile(io_path(path / "provenance-generators.zip")) as archive:
            data = archive.read(descriptor["member"])
        require(len(data) == descriptor["bytes"] and sha(data) == descriptor["sha256"], "preserved generator bytes differ")
        return data
    return provider


def verify_protected_archive(path: Path, entries: list[dict], source: Path, policy: Policy, provider) -> None:
    with zipfile.ZipFile(io_path(path)) as archive:
        for entry in entries:
            if entry["kind"] != "file":
                continue
            classification = policy.classify(source, entry["path"])
            require(not classification or classification["kind"] not in {"live_profile", "private_key", "unknown"},
                    "current policy blocks restoring this location")
            scanner = ProtectionScanner()
            with archive.open(entry["path"]) as stream:
                while chunk := stream.read(BLOCK):
                    scanner.feed(chunk)
            stored = entry.get("provenance")
            if stored:
                require(policy.provenance is not None and entry["bytes"] <= PROVENANCE_MAX_BYTES, "restore lacks bounded current provenance")
                actual = policy.provenance.validate(source, archive.read(entry["path"]), path=entry["path"], provider=provider)
                require(actual is not None and actual == stored, "restored literal or cache proof failed")
            elif scanner.private or scanner.credential:
                classification = policy.classify(source, entry["path"], entry["sha256"])
                require(not scanner.credential and classification is not None and classification["kind"] == "fixture_secret_marker"
                        and entry["bytes"] <= PROVENANCE_MAX_BYTES, "unclassified protected archive bytes cannot restore")
                validate_fixture_marker(archive.read(entry["path"]))


def verify_content_provenance(path: Path, inventory: dict, source: Path, policy: Policy):
    used = [e["provenance"] for e in inventory["entries"] if e.get("provenance")] + inventory.get("provenance_objects", [])
    binding = inventory.get("content_provenance")
    descriptors = []
    if binding is not None or used:
        require(policy.provenance is not None and isinstance(binding, dict), "checkpoint has no current bound provenance policy")
        policy.provenance.recheck()
        require(binding == policy.provenance.checkpoint_binding(used), "checkpoint proof or generator binding differs")
        descriptors = binding["generators"]
    provider = checkpoint_generator_provider(path, descriptors)
    verify_protected_archive(path / "working-tree.zip", inventory["entries"], source, policy, provider)
    state = inventory["git"]
    if state:
        for scope, entries in state["metadata"].items():
            verify_protected_archive(path / f"git-{scope}-metadata.zip", entries, Path(state["metadata_roots"][scope]), policy, provider)
        for record in inventory.get("provenance_objects", []):
            require(record["identity"]["git_oid"] in {o["oid"] for o in state["objects"] if o["type"] == "blob"}
                    and state["object_path_provenance"]["blobs"].get(record["identity"]["git_oid"]) == record["identity"]["aliases"],
                    "checkpoint object identity or alias binding differs")
    require(not descriptors or exists(path / "provenance-generators.zip"), "checkpoint is missing exact preserved generators")
    return provider


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
    if inventory.get("content_provenance", {}).get("generators"):
        expected.add("provenance-generators.zip")
    require(set(names) == expected, "checkpoint has missing or unexpected artifacts")
    verify_content_provenance(path, inventory, source, policy)
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
            all_objects = text_git(working, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)").splitlines()
            require(sorted(all_objects) == sorted(expected_objects), "restored pack contains unclassified additional objects")
            read_policy = Policy({"schema_version": SCHEMA, "source_roots": [str(working)], "git_roots": [str(working / ".git")],
                                  "capture_targets": [], "restore_targets": []})
            validation_view = create_read_view(working, read_policy, metadata / "index-view")
            assert validation_view is not None
            observed_aliases = git_object_paths(working, state["objects"], validation_view)
            require(observed_aliases == state["object_path_provenance"], "restored canonical aliases differ from the checkpoint")
            provider = verify_content_provenance(checkpoint, inventory, Path(inventory["source_root"]), policy)
            restored_admissions = []
            pending = git_sensitive(Path(inventory["source_root"]), state, policy, observation_root=working,
                                    generator_provider=provider, admitted_objects=restored_admissions)
            require(not pending, "restored Git pack contains unclassified protected content")
            require(sorted(restored_admissions, key=canonical_proof) == sorted(inventory.get("provenance_objects", []), key=canonical_proof),
                    "restored object admissions differ")
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
