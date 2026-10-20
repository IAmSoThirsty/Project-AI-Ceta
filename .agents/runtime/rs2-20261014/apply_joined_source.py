"""Apply seven explicitly reviewed paths with preserved originals and fresh byte checks."""
from datetime import datetime, timezone
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
import sys

S = Path(__file__).resolve().parents[3]
TOOL = S / ".agents/pr4-20261014/preserve_ceta_complete.py"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
assert sha(TOOL) == "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618"
spec = importlib.util.spec_from_file_location("ceta_joined_publication_io", TOOL)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)
KERNEL = ctypes.WinDLL("kernel32", use_last_error=True, winmode=0x800)
KERNEL.ReplaceFileW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                               wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
KERNEL.ReplaceFileW.restype = wintypes.BOOL
ALLOWED = frozenset({"tests/contract/test_source_coverage.py", "tests/contract/test_task_meaning_view.py",
                     "src/ceta/contracts/resource_management.py", "src/ceta/supervisor/windows_jobs.py",
                     "src/ceta/resource/diagnostics.py", "tests/contract/test_process_diagnostics.py",
                     "contracts/PROCESS_DIAGNOSTICS_V1.md"})

def exact_hash(path):
    with fs.open_source(fs.safe_components(path), exclusive=True) as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest.hexdigest()

def publish_prepared(staged, target, backup, before, candidate):
    """Controlled owner scope; caller retains backups after every outcome."""
    fs.safe_components(staged)
    fs.safe_components(target, allow_missing=before is None)
    fs.safe_components(backup, allow_missing=True)
    assert staged != target and backup not in (staged, target)
    assert not fs.exists(backup), "native backup already exists"
    assert exact_hash(staged) == candidate, "staged payload drift"
    if before is None:
        assert not fs.exists(target), "create target already exists"
        fs.publish_new(staged, target)
    else:
        assert exact_hash(target) == before, "existing target drift"
        # flags=0 preserves merge errors instead of weakening their validation.
        # A distinct fresh backup keeps the original file if Windows reports a
        # partial replacement outcome. No original backup is reused/overwritten.
        if not KERNEL.ReplaceFileW(fs.io_path(target), fs.io_path(staged), fs.io_path(backup), 0, None, None):
            raise OSError(ctypes.get_last_error(), "WINDOWS_EXACT_FILE_REPLACEMENT_FAILED")
        assert exact_hash(backup) == before, "native backup bytes differ"
    assert exact_hash(target) == candidate, "published bytes differ"

def main():
    run = "app3-20261014"
    Q, R = S / ".agents" / run, S / ".agents/runtime" / run
    OUT = R / "active-application"
    claim = read(R / run / "claims.json")["integrate"]
    assert claim["executor_id"] == "/root" and claim["workspace"] == str(S)
    state = read(R / run / "state.json")
    assert state["nodes"]["review"]["state"] == state["nodes"]["validate"]["state"] == "SUCCEEDED"
    review_path = R / "independent-review/review.json"
    review = read(review_path)
    assert review["decision"] == "approved" and review["exit_status"] == 0
    assert sha(Path(__file__)) == review["result"]["publication_script_sha256"], "publication script differs from independent review"
    manifest_path = Q / "TRANSFER-MANIFEST.json"
    manifest = read(manifest_path)
    assert sha(manifest_path) == review["result"]["manifest_sha256"]
    assert frozenset(manifest["application_paths"]) == ALLOWED
    entries = {item["relative_path"]: item for item in manifest["payloads"]}
    assert len(entries) == len(manifest["payloads"])
    selected = [entries[relative] for relative in sorted(ALLOWED)]
    assert sum(item["application_action"] == "CREATE" for item in selected) == 2
    assert sum(item["application_action"] == "EXTEND_PRESERVE_BEFORE_IMAGE" for item in selected) == 5
    for item in entries.values():
        relative = item["relative_path"]
        fs.relative_name(relative)
        assert relative == item["active_target_relative_to_repository"]
        assert exact_hash(Q / relative) == item["candidate_sha256"]
        target = fs.safe_components(S / relative, allow_missing=item["active_before_sha256"] is None)
        actual = exact_hash(target) if fs.exists(target) else None
        assert actual == item["active_before_sha256"], ("destination drift", relative)
    fs.safe_components(OUT, allow_missing=True)
    OUT.mkdir(exist_ok=False)
    before_images = []
    for item in selected:
        relative = item["relative_path"]
        stage = OUT / "staged" / relative
        before_image = OUT / "before" / (relative + ".source")
        native_backup = OUT / "native-backups" / (relative + ".original")
        for parent in (stage.parent, before_image.parent, native_backup.parent):
            fs.safe_components(parent, allow_missing=True)
            parent.mkdir(parents=True, exist_ok=True)
            fs.safe_components(parent)
        with fs.open_source(fs.safe_components(Q / relative), exclusive=True) as source:
            data = source.read()
            assert len(data) <= 8 * 1024 * 1024 and hashlib.sha256(data).hexdigest() == item["candidate_sha256"]
            with stage.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        if item["active_before_sha256"] is not None:
            with fs.open_source(fs.safe_components(S / relative), exclusive=True) as source:
                original = source.read()
                assert hashlib.sha256(original).hexdigest() == item["active_before_sha256"]
                facts = os.fstat(source.fileno())
                with before_image.open("xb") as output:
                    output.write(original)
                    output.flush()
                    os.fsync(output.fileno())
            before_images.append({"relative_path": relative, "sha256": sha(before_image),
                                  "bytes": facts.st_size, "device": facts.st_dev, "inode": facts.st_ino,
                                  "mode": facts.st_mode, "mtime_ns": facts.st_mtime_ns})
    journal = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(), "executor": "/root",
               "claim_input_hash": claim["input_hash"], "manifest_sha256": sha(manifest_path),
               "review_sha256": sha(review_path), "source_root": str(S), "completed": [],
               "before_images": before_images, "status": "PREPARED_AWAITING_SEVEN_PATH_APPLICATION",
               "publication_api": "ReplaceFileW(flags0,fresh_backup) for existing paths; approved no-overwrite MoveFileExW(flags8) for creates",
               "api_reference": "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew",
               "scope_limit": "Exclusive coordinator-owned ordinary paths; same-principal/privileged hostile ancestor replacement remains unqualified",
               "recovery_rule": "On any failure preserve targets, staged bytes, logical before-images and native backups; reconcile all seven hashes and file identities under fresh review before resuming"}
    journal_path = OUT / "APPLICATION.json"
    def save_journal():
        temporary = OUT / "APPLICATION.next.json"
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(journal, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, journal_path)
    save_journal()
    try:
        for item in selected:
            relative = item["relative_path"]
            publish_prepared(OUT / "staged" / relative, S / relative,
                             OUT / "native-backups" / (relative + ".original"),
                             item["active_before_sha256"], item["candidate_sha256"])
            journal["completed"].append({"relative_path": relative, "sha256": exact_hash(S / relative)})
            save_journal()
        for item in entries.values():
            assert exact_hash(S / item["relative_path"]) == item["candidate_sha256"]
        journal["status"] = "SEVEN_REVIEWED_PATHS_APPLIED_AWAITING_FULL_DESTINATION_VERIFICATION"
        journal["applied_at"] = datetime.now(timezone.utc).isoformat()
        save_journal()
    except BaseException as failure:
        journal["status"] = "PARTIAL_APPLICATION_PRESERVED_REQUIRES_FRESH_RECONCILIATION"
        journal["error_type"] = type(failure).__name__
        journal["error"] = str(failure)
        save_journal()
        raise
    print(json.dumps({"status": journal["status"], "published": len(journal["completed"]),
                      "journal_sha256": sha(journal_path)}))

if __name__ == "__main__":
    main()
