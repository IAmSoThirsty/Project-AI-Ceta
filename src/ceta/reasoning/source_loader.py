"""Load the two pinned vendor packages from verified source snapshots.

The extracted Python, resource and configuration files must match the original
archives. Code and package resources are then read from those captured archive
bytes, never from Python bytecode caches. The narrowly scoped import finder
owns only the two vendor package names and does not alter sys.path. This is
source provenance in one interpreter, not an OS isolation boundary.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.abc
import importlib.util
import io
import json
import stat
import sys
import threading
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType

_VENDOR_ROOT = Path(__file__).resolve().parent / "vendor"
_V1_ROOT = _VENDOR_ROOT / "societal_reasoning_v1"
_F_ROOT = _VENDOR_ROOT / "truth_accountability_f"
_ARCHIVES = _VENDOR_ROOT / "original_archives"
_V1_ARCHIVE_SHA256 = "b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5"
_F_ARCHIVE_SHA256 = "76cde0a52c0fabb4fb0fe6f12aee7ed36220493a175701f04aa9919777fda27a"
_PACKAGES = ("societal_reasoning", "truth_accountability")
_LOCK = threading.RLock()
_LOADED = False
_LOAD_ERROR: str | None = None
_FINDER: _VerifiedFinder | None = None
_VERIFICATION: SourceVerification | None = None


@dataclass(frozen=True)
class SourceVerification:
    """Observed source identity; no authority or execution qualification."""
    v1_archive_sha256: str
    f_archive_sha256: str
    v1_archive_match: bool
    f_archive_match: bool
    v1_concept_count: int
    v1_version_string: str
    paths_added: tuple[str, ...]
    verified_files: tuple[tuple[str, str], ...] = ()
    tree_sha256: str = ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_archives() -> tuple[bool, bool]:
    """Observe archive checksums only; this function performs no imports."""
    paths = (_ARCHIVES / "Societal-Reasoning-Core-v1.zip",
             _ARCHIVES / "truth-accountability-reference-increments-A-F.zip")
    return tuple(p.is_file() and _sha256_file(p) == pin for p, pin in
                 zip(paths, (_V1_ARCHIVE_SHA256, _F_ARCHIVE_SHA256)))


def _ordinary_file(path: Path, root: Path) -> bytes:
    # Reject linked/reparse directories as well as linked leaf files. Do not
    # follow an attacker-selected executable/resource out of the vendor tree.
    for node in (path, *path.parents):
        attributes = node.lstat()
        if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, "st_file_attributes", 0) & 0x400:
            raise RuntimeError(f"Linked vendor path rejected: {node}")
        if node == root:
            break
    if not path.is_file():
        raise RuntimeError(f"Missing vendor file: {path}")
    return path.read_bytes()


def _capture_sources() -> tuple[dict[str, tuple[zipfile.ZipFile, str, Path]],
                                 tuple[tuple[str, str], ...], bytes]:
    # Transfer only a completely verified set of in-memory archive handles.
    with ExitStack() as resources:
        result = _capture_with_resources(resources)
        resources.pop_all()
        return result


def _capture_with_resources(resources: ExitStack):
    specs = (
        ("Societal-Reasoning-Core-v1.zip", _V1_ARCHIVE_SHA256, _V1_ROOT,
         "Societal-Reasoning-Core/", ("src/societal_reasoning/",)),
        ("truth-accountability-reference-increments-A-F.zip", _F_ARCHIVE_SHA256, _F_ROOT,
         "truth-accountability-reference/", ("truth_accountability/", "configs/", "schemas/")),
    )
    packages = {}
    verified = []
    mapping = None
    for archive_name, pin, extracted, prefix, included in specs:
        raw = _ordinary_file(_ARCHIVES / archive_name, _VENDOR_ROOT)
        if hashlib.sha256(raw).hexdigest() != pin:
            raise RuntimeError(f"Archive SHA-256 mismatch: {archive_name}")
        archive = resources.enter_context(zipfile.ZipFile(io.BytesIO(raw), "r"))
        expected = set()
        for member in archive.infolist():
            if member.is_dir() or not member.filename.startswith(prefix):
                continue
            relative = member.filename[len(prefix):]
            if not relative.startswith(included):
                continue
            parts = PurePosixPath(relative).parts
            if (relative in expected or ".." in parts or "\\" in relative or
                    relative.startswith("/") or member.file_size > 25 * 1024 * 1024):
                raise RuntimeError("Unsafe or duplicate pinned member")
            expected.add(relative)
            content = archive.read(member)
            if _ordinary_file(extracted.joinpath(*parts), _VENDOR_ROOT) != content:
                raise RuntimeError(f"Extracted vendor bytes differ: {relative}")
            verified.append((extracted.name + "/" + relative, hashlib.sha256(content).hexdigest()))
            if relative == "configs/version1_canonical_mapping.json":
                mapping = content
        # Extra files cannot silently become imports/resources. Bytecode caches
        # are excluded because this loader never consults or writes them.
        observed = set()
        for directory in included:
            folder = extracted / directory.rstrip("/")
            for file in folder.rglob("*"):
                if "__pycache__" in file.relative_to(folder).parts:
                    continue
                attributes = file.lstat()
                if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, "st_file_attributes", 0) & 0x400:
                    raise RuntimeError(f"Linked vendor member rejected: {file}")
                if file.is_file():
                    observed.add(file.relative_to(extracted).as_posix())
        if observed != expected:
            raise RuntimeError("Extracted vendor membership differs from pinned archive")
        if archive_name.startswith("Societal"):
            packages["societal_reasoning"] = (archive, prefix + "src/societal_reasoning/",
                                               extracted / "src/societal_reasoning")
        else:
            packages["truth_accountability"] = (archive, prefix + "truth_accountability/",
                                                 extracted / "truth_accountability")
    if mapping is None:
        raise RuntimeError("Pinned corpus mapping is missing")
    return packages, tuple(sorted(verified)), mapping


class _ResourceReader(importlib.abc.TraversableResources):
    def __init__(self, archive: zipfile.ZipFile, prefix: str):
        self.archive, self.prefix = archive, prefix

    def files(self):
        return zipfile.Path(self.archive, at=self.prefix)


class _VerifiedLoader(importlib.abc.Loader):
    def __init__(self, finder: _VerifiedFinder, fullname: str, member: str,
                 archive: zipfile.ZipFile, origin: Path, package: bool):
        self.finder, self.fullname, self.member = finder, fullname, member
        self.archive, self.origin, self.package = archive, origin, package

    def create_module(self, spec):
        return None

    def exec_module(self, module: ModuleType) -> None:
        previous = self.finder.modules.get(self.fullname)
        if previous is not None:
            raise RuntimeError("Verified vendor module reload is not supported")
        self.finder.modules[self.fullname] = module
        module.__file__ = str(self.origin)
        code = compile(self.archive.read(self.member), str(self.origin), "exec", dont_inherit=True)
        exec(code, module.__dict__)

    def get_resource_reader(self, fullname: str):
        if self.package and fullname == self.fullname:
            return _ResourceReader(self.archive, self.member.removesuffix("__init__.py"))
        return None


class _VerifiedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, packages):
        self.packages = packages
        self.modules: dict[str, ModuleType] = {}

    def find_spec(self, fullname, path=None, target=None):
        package_name = fullname.partition(".")[0]
        if package_name not in self.packages:
            return None
        archive, prefix, root = self.packages[package_name]
        suffix = fullname[len(package_name):].lstrip(".").replace(".", "/")
        base = prefix + (suffix + "/" if suffix else "")
        if base + "__init__.py" in archive.namelist():
            member, is_package = base + "__init__.py", True
        else:
            member, is_package = prefix + suffix + ".py", False
        if member not in archive.namelist():
            raise ModuleNotFoundError(f"Module outside verified vendor membership: {fullname}")
        relative = member[len(prefix):]
        loader = _VerifiedLoader(self, fullname, member, archive, root / relative, is_package)
        return importlib.util.spec_from_loader(fullname, loader, origin=str(root / relative),
                                               is_package=is_package)

    def verify_cache(self) -> None:
        for name, module in tuple(sys.modules.items()):
            if name.partition(".")[0] not in _PACKAGES:
                continue
            if self.modules.get(name) is not module:
                raise RuntimeError(f"Foreign preloaded vendor module rejected: {name}")
            loader = getattr(module, "__loader__", None)
            spec = getattr(module, "__spec__", None)
            if (not isinstance(loader, _VerifiedLoader) or loader.finder is not self or
                    spec is None or spec.loader is not loader or
                    module.__file__ != str(loader.origin) or spec.origin != str(loader.origin)):
                raise RuntimeError(f"Verified vendor module origin changed: {name}")
        if any(sys.modules.get(name) is not module for name, module in self.modules.items()):
            raise RuntimeError("Verified vendor module removed from import cache")


def corpus_mapping_bytes() -> bytes:
    """Return the already verified mapping used by new independent sessions."""
    with _LOCK:
        load_components()
        archive, _, _ = _FINDER.packages["truth_accountability"]
        return archive.read("truth-accountability-reference/configs/version1_canonical_mapping.json")


def load_components() -> SourceVerification:
    """Verify sources and load reusable modules; construct no live CETA state.

    Repeated calls recheck the extracted sources and module identities. Failed
    first loads retire only modules/finder objects created by that attempt;
    a later explicit call can retry after the external problem is repaired.
    """
    global _LOADED, _LOAD_ERROR, _FINDER, _VERIFICATION
    with _LOCK:
        finder = None
        packages = {}
        try:
            packages, verified, mapping_raw = _capture_sources()
            if _LOADED:
                if _FINDER not in sys.meta_path:
                    raise RuntimeError("Verified vendor import finder was removed")
                _FINDER.verify_cache()
                if verified != _VERIFICATION.verified_files:
                    raise RuntimeError("Verified source identity changed")
                _LOAD_ERROR = None
                return _VERIFICATION
            for name in tuple(sys.modules):
                if name.partition(".")[0] in _PACKAGES:
                    raise RuntimeError(f"Foreign preloaded vendor module rejected: {name}")
            finder = _VerifiedFinder(packages)
            sys.meta_path.insert(0, finder)
            societal = importlib.import_module("societal_reasoning")
            truth = importlib.import_module("truth_accountability")
            if societal.__version__ != "1" or not callable(getattr(societal, "SocietalReasoner", None)):
                raise RuntimeError("Unexpected V1 runtime API")
            adapter = truth.Version1ReadOnlyAdapter(
                _ARCHIVES / "Societal-Reasoning-Core-v1.zip",
                mapping=truth.CorpusMapping(**json.loads(mapping_raw)),
                expected_zip_sha256=_V1_ARCHIVE_SHA256)
            inspection = adapter.inspect()
            if inspection.records != 2000:
                raise RuntimeError("Pinned V1 corpus must contain exactly 2000 records")
            finder.verify_cache()
            tree = hashlib.sha256(json.dumps(verified, separators=(",", ":")).encode("utf-8")).hexdigest()
            _VERIFICATION = SourceVerification(_V1_ARCHIVE_SHA256, _F_ARCHIVE_SHA256,
                True, True, inspection.records, societal.__version__, (), verified, tree)
            _FINDER, _LOADED, _LOAD_ERROR = finder, True, None
            return _VERIFICATION
        except BaseException as exc:
            # Do not execute an exception's potentially failing __str__ while
            # recording diagnostics for the actual source-loading failure.
            _LOAD_ERROR = type(exc).__name__ + ": source loading failed"
            if finder is not None:
                if finder in sys.meta_path:
                    sys.meta_path.remove(finder)
                for name, module in tuple(finder.modules.items()):
                    if sys.modules.get(name) is module:
                        del sys.modules[name]
            raise
        finally:
            # Rechecks capture fresh snapshots. Only the installed finder's
            # snapshots remain live for subsequent imports and resources.
            if _FINDER is None or packages is not _FINDER.packages:
                for archive, _, _ in packages.values():
                    archive.close()


def is_loaded() -> bool:
    """Whether the last successful load installed reusable verified modules."""
    return _LOADED


def get_load_error() -> str | None:
    return _LOAD_ERROR
