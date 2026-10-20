"""Read-only, untrusted-input inspection and contextual retrieval for a Version 1 archive.

This code does NOT import/execute packaged source, mutate Version 1, or
claim conformance to a source archive we have not opened. A mapping from
its actual schema must be separately reviewed before contextual retrieval.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

MAX_ENTRIES = 5000
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_JSONL_LINE = 1 * 1024 * 1024
# Small lexical relevance filter; this is not semantic retrieval or a proof
# that a mechanism applies to the current speaker.
_STOPWORDS = frozenset({
    "the","and","not","was","are","you","your","they","for","with","from",
    "all","some","that","this","have","has","had","can","could","would",
    "should","might","will","must","but","what","who","why","how","its",
    "were","being","been","into","than","about","because","rather",
    "only","then","their","there","also","people","person","these","those"
})
_REQUIRED_HINTS = ("src/societal_reasoning/engine.py", "src/societal_reasoning/models.py")


class SourceRejected(ValueError):
    """Unsafe or malformed source cannot be treated as a Version 1 input."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise SourceRejected("Duplicated JSON object key")
        out[key] = value
    return out


def _reject_constant(v: str) -> None:
    raise SourceRejected("Non-finite JSON forbidden")


def _json_object(raw: bytes) -> dict:
    try:
        out = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as e:
        raise SourceRejected("Invalid UTF-8 JSON source") from e
    if not isinstance(out, dict):
        raise SourceRejected("Each corpus record must be a JSON object")
    return out


def _validate_member_name(name: str) -> None:
    p = PurePosixPath(name)
    if (not name or name.startswith("/") or "\\" in name or "\x00" in name
        or any(part in {"", ".", ".."} for part in name.split("/"))
        or any(":" in part for part in p.parts) or name.startswith("~")):
        raise SourceRejected("Unsafe archive member path")


class _SourceView:
    """Open an archive without extraction, or an existing source directory."""
    def __init__(self, source: str | Path):
        self.path = Path(source)
        self._names: dict[str, str] = {}
        self._zip: zipfile.ZipFile | None = None
        if self.path.is_symlink():
            raise SourceRejected("Symlink source root forbidden")
        self._is_directory = self.path.is_dir()
        if not self._is_directory and not self.path.is_file():
            raise FileNotFoundError("Version 1 source is not accessible")

    def __enter__(self) -> "_SourceView":
        if not self._is_directory:
            if not zipfile.is_zipfile(self.path):
                raise SourceRejected("Source must be a ZIP archive or a directory")
            self._zip = zipfile.ZipFile(self.path)
            try:
                records = self._zip.infolist()
                if len(records) > MAX_ENTRIES:
                    raise SourceRejected("Too many archive entries")
                total = 0
                for info in records:
                    name = info.filename.rstrip("/")
                    _validate_member_name(name)
                    mode = (info.external_attr >> 16) & 0xffff
                    if stat.S_ISLNK(mode):
                        raise SourceRejected("Archive symlinks forbidden")
                    if info.flag_bits & 0x1:
                        raise SourceRejected("Encrypted entries forbidden")
                    if info.is_dir():
                        continue
                    if info.file_size > MAX_MEMBER_BYTES:
                        raise SourceRejected("Oversized archive member")
                    total += info.file_size
                    if total > MAX_TOTAL_BYTES:
                        raise SourceRejected("Oversized archive")
                    self._add(name, name)
            except BaseException:
                self._zip.close()
                self._zip = None
                raise
        else:
            n = 0
            total = 0
            for root, dirs, files in os.walk(self.path, followlinks=False):
                for d in dirs:
                    if (Path(root) / d).is_symlink():
                        raise SourceRejected("Symlink directories forbidden")
                for f in files:
                    child = Path(root) / f
                    if child.is_symlink() or not child.is_file():
                        raise SourceRejected("Symlinks or non-files forbidden")
                    rel = child.relative_to(self.path).as_posix()
                    _validate_member_name(rel)
                    size = child.stat().st_size
                    if size > MAX_MEMBER_BYTES:
                        raise SourceRejected("Oversized source member")
                    total += size
                    n += 1
                    if n > MAX_ENTRIES or total > MAX_TOTAL_BYTES:
                        raise SourceRejected("Source tree exceeds inspection budget")
                    self._add(rel, rel)
        return self

    def _add(self, name: str, raw_name: str) -> None:
        # Reject duplicates independent of case; on Windows they'd collide.
        key = name.casefold()
        if key in self._names:
            raise SourceRejected("Duplicate or case-colliding source path")
        self._names[key] = raw_name

    def __exit__(self, *args: object) -> None:
        if self._zip is not None:
            self._zip.close()

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._names.values()))

    def resolve_suffix(self, suffix: str) -> str:
        _validate_member_name(suffix)
        matched = [n for n in self.names if n == suffix or n.endswith("/" + suffix)]
        if len(matched) != 1:
            raise SourceRejected(f"Required path is missing or ambiguous: {suffix}")
        return matched[0]

    def read(self, name: str) -> bytes:
        if name.casefold() not in self._names:
            raise SourceRejected("Source member not in inspected index")
        if self._zip is not None:
            info = self._zip.getinfo(name)
            if info.file_size > MAX_MEMBER_BYTES:
                raise SourceRejected("Member exceeds read budget")
            with self._zip.open(info) as fp:
                raw = fp.read(MAX_MEMBER_BYTES + 1)
        else:
            raw = (self.path / name).read_bytes()
        if len(raw) > MAX_MEMBER_BYTES:
            raise SourceRejected("Member exceeds read budget")
        return raw


@dataclass(frozen=True)
class CorpusMapping:
    """Host-reviewed field mapping. There are NO assumed Version 1 field names."""
    corpus_suffix: str
    id_field: str
    text_field: str
    expected_count: int = 2000
    id_prefix: str = ""
    id_width: int = 0

    def __post_init__(self) -> None:
        _validate_member_name(self.corpus_suffix)
        for s in (self.id_field, self.text_field):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", s):
                raise ValueError("Simple, explicitly reviewed JSON field names only")
        if self.id_field == self.text_field:
            raise ValueError("ID and text fields must differ")
        if not isinstance(self.expected_count, int) or isinstance(self.expected_count, bool) or not 1 <= self.expected_count <= 2000:
            raise ValueError("Expected count must be bounded")
        if not isinstance(self.id_prefix, str) or len(self.id_prefix) > 32:
            raise ValueError("Bounded ID prefix required")
        if not isinstance(self.id_width, int) or isinstance(self.id_width, bool) or not 0 <= self.id_width <= 8:
            raise ValueError("Invalid ID width")

    def id_at(self, position: int) -> str:
        return self.id_prefix + (str(position).zfill(self.id_width) if self.id_width else str(position))


@dataclass(frozen=True)
class ContextCandidate:
    """An observed inventory record, never proof about a particular person."""
    entry_id: str
    exact_text: str
    text_sha256: str
    source_member: str
    line: int
    source_kind: str = "CONTEXTUAL_REFERENCE_NOT_PERSON_EVIDENCE"


@dataclass(frozen=True)
class SourceInspection:
    status: str
    members: int
    source_sha256: str | None
    source_accessible: bool
    observed_contract_hints: tuple[str, ...]
    records: int | None
    corpus_member: str | None
    corpus_sha256: str | None
    notes: tuple[str, ...]


class Version1ReadOnlyAdapter:
    """No runtime import, no mutation, and no ontology-based person labels.

    The source must be supplied by the host as a real filesystem path; a
    previous assistant's link or file title cannot substitute for bytes.
    """
    def __init__(self, source: str | Path, *, mapping: CorpusMapping | None = None,
                 expected_zip_sha256: str | None = None):
        self.path = Path(source)
        self.mapping = mapping
        if expected_zip_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", expected_zip_sha256):
            raise ValueError("Expected SHA-256 must be complete and lowercase")
        self.expected_zip_sha256 = expected_zip_sha256
        self._cached_candidates: tuple[ContextCandidate, ...] | None = None
        self._inspected_corpus_digest: str | None = None
        self.last_inspection: SourceInspection | None = None

    def inspect(self) -> SourceInspection:
        if self.path.is_dir() and self.expected_zip_sha256:
            raise SourceRejected("An archive checksum cannot authenticate a source directory")
        zip_sha = None
        if self.path.is_file():
            h = hashlib.sha256()
            with self.path.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            zip_sha = h.hexdigest()
            if self.expected_zip_sha256 and zip_sha != self.expected_zip_sha256:
                raise SourceRejected("Archive SHA-256 mismatch")
        with _SourceView(self.path) as view:
            observed = tuple(hint for hint in _REQUIRED_HINTS
                             if any(n.endswith(hint) for n in view.names))
            if not self.mapping:
                self._cached_candidates = None
                self._inspected_corpus_digest = None
                result = SourceInspection("UNMAPPED_INSPECTION_ONLY",len(view.names),zip_sha,True,
                                          observed,None,None,None,
                                          ("No schema field mapping was provided; no claims about the 2,000 entries.",))
            else:
                member = view.resolve_suffix(self.mapping.corpus_suffix)
                raw = view.read(member)
                entries = self._parse_corpus(raw,member)
                self._cached_candidates = entries
                self._inspected_corpus_digest = _digest(raw)
                status = ("MAPPED_2000_RECORDS_SOURCE_ONLY" if len(entries)==2000 and self.mapping.expected_count==2000
                          else "MAPPED_TEST_OR_PARTIAL_CORPUS")
                result = SourceInspection(status,len(view.names),zip_sha,True,observed,len(entries),
                                          member,_digest(raw),
                                          ("Mapping and raw-record checks are structural only; they do not certify owner approval, corpus authenticity or meanings.",))
        self.last_inspection = result
        return result

    def _parse_corpus(self, raw: bytes, member: str) -> tuple[ContextCandidate, ...]:
        assert self.mapping is not None
        lines = raw.splitlines()
        if len(lines) != self.mapping.expected_count:
            raise SourceRejected("Corpus record count does not match mapped expectation")
        entries: list[ContextCandidate] = []
        for n, line in enumerate(lines, 1):
            if not line or len(line)>MAX_JSONL_LINE:
                raise SourceRejected("Empty or oversized corpus JSONL record")
            item = _json_object(line)
            key, content = item.get(self.mapping.id_field), item.get(self.mapping.text_field)
            if isinstance(key, int) and not isinstance(key,bool):
                key = str(key)
            if not isinstance(key,str) or key != self.mapping.id_at(n):
                raise SourceRejected("Missing, repeated, unordered or mismapped record ID")
            if not isinstance(content,str) or not content.strip() or len(content.encode('utf-8')) > MAX_JSONL_LINE:
                raise SourceRejected("Missing or malformed context text")
            entries.append(ContextCandidate(key,content,_digest(line),member,n))
        return tuple(entries)

    def candidates(self, query: str, *, limit: int = 4) -> tuple[ContextCandidate, ...]:
        if self._cached_candidates is None or self.last_inspection is None:
            raise RuntimeError("Explicit mapping and successful inspection required")
        # Detect source mutations after inspection. Directory sources lack an
        # archive-wide checksum, so re-open the mapped corpus and recheck it.
        if self.path.is_file():
            h = hashlib.sha256()
            with self.path.open('rb') as fp:
                for chunk in iter(lambda: fp.read(65536),b''):
                    h.update(chunk)
            if h.hexdigest() != self.last_inspection.source_sha256:
                raise SourceRejected("Source changed after inspection; re-inspect")
        else:
            with _SourceView(self.path) as view:
                member = view.resolve_suffix(self.mapping.corpus_suffix)
                if _digest(view.read(member)) != self._inspected_corpus_digest:
                    raise SourceRejected("Mapped corpus changed after inspection; re-inspect")
        if not isinstance(query,str) or not 1 <= len(query) <= 8192:
            raise ValueError("Bounded query required")
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1 <= limit <= 10:
            raise ValueError("Limit 1..10")
        q = set(re.findall(r"\b[a-z]{3,}\b",query.lower())) - _STOPWORDS
        if not q:
            return ()
        scored = []
        for entry in self._cached_candidates:
            words = set(re.findall(r"\b[a-z]{3,}\b",entry.exact_text.lower())) - _STOPWORDS
            score = len(q & words)
            if score:
                scored.append((score,entry.line,entry))
        scored.sort(key=lambda item:(-item[0],item[1]))
        return tuple(i[2] for i in scored[:limit])
