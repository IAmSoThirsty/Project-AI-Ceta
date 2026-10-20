"""Load the exact project SQLite DLL before CPython opens any connection.

This preserves the installed interpreter and refuses a previously loaded engine
with a different identity. Loading a library establishes no operational authority.
"""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import struct
import threading

from ceta.contracts.wire import ContractError

VERSION = "3.53.4"
DLL_SHA256 = "ab57d0437795ecc757cb693f32ea224173fa9856594d95cfa6b5033e645cd1ec"
ROOT = Path(__file__).resolve().parents[3]
DLL_PATH = ROOT / "native/sqlite_runtime/win-x64/sqlite3.dll"
_LOCK = threading.RLock()
_HANDLE = None


def _kernel():
    if os.name != "nt" or struct.calcsize("P") != 8:
        raise ContractError("SQLITE_WINDOWS_X64_REQUIRED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetModuleFileNameW.restype = wintypes.DWORD
    return kernel


def _module_path(kernel):
    handle = kernel.GetModuleHandleW("sqlite3.dll")
    if not handle:
        return None
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
    if not length or length == len(buffer):
        raise ContractError("SQLITE_LOADED_PATH_UNAVAILABLE")
    return Path(buffer.value).resolve(strict=True)


def load_sqlite():
    global _HANDLE
    with _LOCK:
        kernel = _kernel()
        for path in (DLL_PATH, *DLL_PATH.parents):
            if path.is_symlink() or path.is_junction():
                raise ContractError("SQLITE_RUNTIME_LINK_REJECTED")
        if hashlib.sha256(DLL_PATH.read_bytes()).hexdigest() != DLL_SHA256:
            raise ContractError("SQLITE_RUNTIME_BYTES_MISMATCH")
        loaded = _module_path(kernel)
        if loaded is not None and loaded != DLL_PATH.resolve(strict=True):
            raise ContractError("SQLITE_PRELOADED_ENGINE_CONFLICT")
        if loaded is None:
            # Absolute path, DLL-load directory and standard default directories.
            # No environment PATH edit or installed-library replacement occurs.
            _HANDLE = ctypes.WinDLL(str(DLL_PATH), winmode=0x100 | 0x1000)
        import sqlite3
        loaded = _module_path(kernel)
        if (loaded != DLL_PATH.resolve(strict=True) or sqlite3.sqlite_version != VERSION
                or hashlib.sha256(loaded.read_bytes()).hexdigest() != DLL_SHA256):
            raise ContractError("SQLITE_LOADED_IDENTITY_MISMATCH")
        return sqlite3


def runtime_identity():
    sqlite3 = load_sqlite()
    import _sqlite3
    return {"version": sqlite3.sqlite_version, "dll_path": str(_module_path(_kernel())),
            "dll_sha256": DLL_SHA256, "wrapper_path": _sqlite3.__file__,
            "wrapper_sha256": hashlib.sha256(Path(_sqlite3.__file__).read_bytes()).hexdigest(),
            "qualification": "LOADED_LIBRARY_IDENTITY_ONLY"}
