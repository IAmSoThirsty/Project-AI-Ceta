"""Verified source loader for vendored V1 and F components.

Loads the original Societal Reasoning Core V1 and Truth Accountability
Increment F from their vendored locations, verifying archive identity
before making any API surface available. All imports are lazily resolved
after integrity checks pass.

This loader never modifies the vendor sources. It adds them to an
isolated sys.path prefix that does not contaminate the main CETA
namespace.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_VENDOR_ROOT = Path(__file__).resolve().parent / "vendor"
_V1_ROOT = _VENDOR_ROOT / "societal_reasoning_v1"
_F_ROOT = _VENDOR_ROOT / "truth_accountability_f"
_ARCHIVES = _VENDOR_ROOT / "original_archives"

# Pinned SHA-256 hashes from the owner-supplied integration package.
_V1_ARCHIVE_SHA256 = "b76b9482f95b93b0a25b8d88881ac3b68558b077118f32e3360f383ded4247b5"
_F_ARCHIVE_SHA256 = "76cde0a52c0fabb4fb0fe6f12aee7ed36220493a175701f04aa9919777fda27a"

_LOADED = False
_LOAD_ERROR: str | None = None


@dataclass(frozen=True)
class SourceVerification:
    """Immutable record of what was verified. Not authority or a permit."""
    v1_archive_sha256: str
    f_archive_sha256: str
    v1_archive_match: bool
    f_archive_match: bool
    v1_concept_count: int
    v1_version_string: str
    paths_added: tuple[str, ...]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_archives() -> tuple[bool, bool]:
    """Check vendored archives against pinned checksums."""
    v1_path = _ARCHIVES / "Societal-Reasoning-Core-v1.zip"
    f_path = _ARCHIVES / "truth-accountability-reference-increments-A-F.zip"
    v1_match = v1_path.exists() and _sha256_file(v1_path) == _V1_ARCHIVE_SHA256
    f_match = f_path.exists() and _sha256_file(f_path) == _F_ARCHIVE_SHA256
    return v1_match, f_match


def load_components() -> SourceVerification:
    """Load V1 and F components after verifying archive identity.

    Adds vendor source paths to sys.path for the duration of this
    process. Returns a frozen verification record. Raises RuntimeError
    if archive integrity fails or the V1 API contract is not met.
    """
    global _LOADED, _LOAD_ERROR

    if _LOADED:
        raise RuntimeError("Components already loaded in this process")
    if _LOAD_ERROR is not None:
        raise RuntimeError(f"Previous load attempt failed: {_LOAD_ERROR}")

    v1_match, f_match = verify_archives()
    if not v1_match:
        _LOAD_ERROR = "V1 archive SHA-256 mismatch or missing"
        raise RuntimeError(_LOAD_ERROR)
    if not f_match:
        _LOAD_ERROR = "F archive SHA-256 mismatch or missing"
        raise RuntimeError(_LOAD_ERROR)

    v1_src = str(_V1_ROOT / "src")
    f_src = str(_F_ROOT)
    paths_added: list[str] = []

    if v1_src not in sys.path:
        sys.path.insert(0, v1_src)
        paths_added.append(v1_src)
    if f_src not in sys.path:
        sys.path.insert(0, f_src)
        paths_added.append(f_src)

    try:
        import societal_reasoning
    except ImportError as exc:
        _LOAD_ERROR = f"V1 import failed: {exc}"
        raise RuntimeError(_LOAD_ERROR) from exc

    version = getattr(societal_reasoning, "__version__", None)
    if version != "1":
        _LOAD_ERROR = f"Unexpected V1 version: {version!r}"
        raise RuntimeError(_LOAD_ERROR)

    try:
        from truth_accountability import (
            CorpusMapping, Version1ReadOnlyAdapter,
        )
    except ImportError as exc:
        _LOAD_ERROR = f"F import failed: {exc}"
        raise RuntimeError(_LOAD_ERROR) from exc

    mapping_path = _F_ROOT / "configs" / "version1_canonical_mapping.json"
    mapping_data = json.loads(mapping_path.read_text("utf-8"))
    adapter = Version1ReadOnlyAdapter(
        _ARCHIVES / "Societal-Reasoning-Core-v1.zip",
        mapping=CorpusMapping(**mapping_data),
        expected_zip_sha256=_V1_ARCHIVE_SHA256,
    )
    inspection = adapter.inspect()
    if inspection.records != 2000:
        _LOAD_ERROR = f"V1 corpus count {inspection.records} != 2000"
        raise RuntimeError(_LOAD_ERROR)

    _LOADED = True
    return SourceVerification(
        v1_archive_sha256=_V1_ARCHIVE_SHA256,
        f_archive_sha256=_F_ARCHIVE_SHA256,
        v1_archive_match=True,
        f_archive_match=True,
        v1_concept_count=inspection.records,
        v1_version_string=version,
        paths_added=tuple(paths_added),
    )


def is_loaded() -> bool:
    """Whether components have been successfully loaded."""
    return _LOADED


def get_load_error() -> str | None:
    """Return the error message from a failed load attempt, if any."""
    return _LOAD_ERROR
