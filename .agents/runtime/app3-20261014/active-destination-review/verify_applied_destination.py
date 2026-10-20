"""Independent read-only verification of actual APP3 publication and imports."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib
import importlib.util
import json
import os
import sys

R = Path(__file__).resolve().parent
S = R.parents[3]
Q = S / ".agents/app3-20261014"
OUT = R.parent / "active-application"
E3 = S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
assert Path(sys.executable).resolve() == E3.resolve()
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [str(S / "src"), str(S / "tools"), str(S / "tests/contract")]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
now = lambda: datetime.now(timezone.utc).isoformat()
EXPECTED_MANIFEST = "491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b"
EXPECTED_JOURNAL = "308dcd7bc20bf807e32ea114aa1e61088c9d39ee34be3532ea58feb279b23e2d"
EXPECTED_REVIEW = "be523c8e5b765756948b4dacba5a73cea4e8738a5c838183abca7c79123b9491"
spec = importlib.util.spec_from_file_location("app3_destination_native_read_io", S / ".agents/pr4-20261014/preserve_ceta_complete.py")
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)
assert sha(Path(spec.origin)) == "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618"

def bytes_exact(path):
    with fs.open_source(fs.safe_components(path), exclusive=True) as stream:
        return stream.read()

def hash_exact(path):
    return hashlib.sha256(bytes_exact(path)).hexdigest()

started = now()
manifest_path = Q / "TRANSFER-MANIFEST.json"
journal_path = OUT / "APPLICATION.json"
review_path = R.parent / "independent-review/review.json"
assert sha(manifest_path) == EXPECTED_MANIFEST
assert sha(journal_path) == EXPECTED_JOURNAL
assert sha(review_path) == EXPECTED_REVIEW
manifest = read(manifest_path)
journal = read(journal_path)
assert manifest["source_root"] == journal["source_root"] == str(S)
assert manifest["candidate_root"] == str(Q)
assert journal["status"] == "SEVEN_REVIEWED_PATHS_APPLIED_AWAITING_FULL_DESTINATION_VERIFICATION"
assert journal["executor"] == "/root"
assert journal["claim_input_hash"] == "417c072343d4b96526cd65b7bf19e35a28f4f6fa3c9410145c69c275bfe79e9b"
assert journal["manifest_sha256"] == EXPECTED_MANIFEST and journal["review_sha256"] == EXPECTED_REVIEW
payloads = {item["relative_path"]: item for item in manifest["payloads"]}
assert len(payloads) == len(manifest["payloads"]) == 235
selected = set(manifest["application_paths"])
assert len(selected) == 7
completed = {item["relative_path"]: item for item in journal["completed"]}
assert len(completed) == len(journal["completed"]) == 7 and set(completed) == selected
before_images = {item["relative_path"]: item for item in journal["before_images"]}
assert len(before_images) == len(journal["before_images"]) == 5
current = {}
observations = []
for relative, item in sorted(payloads.items()):
    fs.relative_name(relative)
    assert relative == item["active_target_relative_to_repository"]
    candidate, target = Q / relative, S / relative
    candidate_data, target_data = bytes_exact(candidate), bytes_exact(target)
    assert candidate_data == target_data
    assert hashlib.sha256(target_data).hexdigest() == item["candidate_sha256"]
    info = fs.lstat(target)
    assert not fs.reparse(info)
    current[relative] = item["candidate_sha256"]
    record = {"relative_path": relative, "action": item["application_action"], "actual_sha256": current[relative],
              "actual_bytes": len(target_data), "device": info.st_dev, "inode": info.st_ino}
    if relative in selected:
        assert completed[relative]["sha256"] == current[relative]
        stage = OUT / "staged" / relative
        assert not fs.exists(stage), ("published staged member still present", relative)
        logical = OUT / "before" / (relative + ".source")
        backup = OUT / "native-backups" / (relative + ".original")
        if item["application_action"] == "CREATE":
            assert item["active_before_sha256"] is None
            assert relative not in before_images
            assert not fs.exists(logical) and not fs.exists(backup)
        else:
            assert item["application_action"] == "EXTEND_PRESERVE_BEFORE_IMAGE"
            old = before_images[relative]
            assert old["sha256"] == item["active_before_sha256"]
            logical_data, backup_data = bytes_exact(logical), bytes_exact(backup)
            assert logical_data == backup_data
            assert hashlib.sha256(logical_data).hexdigest() == old["sha256"]
            native_info = fs.lstat(backup)
            assert not fs.reparse(native_info)
            assert len(logical_data) == native_info.st_size == old["bytes"]
            assert (native_info.st_dev, native_info.st_ino) == (old["device"], old["inode"])
            assert native_info.st_mtime_ns == old["mtime_ns"]
            assert native_info.st_mode == old["mode"]
            record["original_preservation"] = {"logical_path": str(logical), "native_backup_path": str(backup),
                "sha256": old["sha256"], "device": native_info.st_dev, "inode": native_info.st_ino,
                "mtime_ns": native_info.st_mtime_ns, "mode": native_info.st_mode, "bytes": native_info.st_size}
    else:
        assert item["application_action"] == "IDENTICAL_RETAINED"
        assert current[relative] == item["active_before_sha256"]
    observations.append(record)

assert sum(item["application_action"] == "CREATE" for item in payloads.values()) == 2
assert sum(item["application_action"] == "EXTEND_PRESERVE_BEFORE_IMAGE" for item in payloads.values()) == 5
assert sum(item["application_action"] == "IDENTICAL_RETAINED" for item in payloads.values()) == 228
assert not any(path.is_file() for path in (OUT / "staged").rglob("*"))
assert not (OUT / "APPLICATION.next.json").exists()
imports = []
for path in sorted((S / "src/ceta").rglob("*.py")):
    parts = list(path.relative_to(S / "src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    name = ".".join(parts)
    module = importlib.import_module(name)
    actual = Path(module.__file__).resolve()
    assert actual == path.resolve(), (name, actual, path)
    imports.append({"module": name, "actual_path": str(actual), "sha256": hash_exact(actual)})
assert len(imports) == 72
for name, module in tuple(sys.modules.items()):
    if name == "ceta" or name.startswith("ceta."):
        assert Path(module.__file__).resolve().is_relative_to(S / "src"), (name, module.__file__)
after = {relative: hash_exact(S / relative) for relative in payloads}
assert after == current
assert sha(manifest_path) == EXPECTED_MANIFEST and sha(journal_path) == EXPECTED_JOURNAL
result = {"schema_version": 1, "started_at": started, "finished_at": now(), "source_root": str(S),
          "candidate_root": str(Q), "manifest_sha256": EXPECTED_MANIFEST,
          "application_journal_sha256": EXPECTED_JOURNAL, "accepted_join_review_sha256": EXPECTED_REVIEW,
          "root_claim_input_hash": journal["claim_input_hash"], "root_executor": journal["executor"],
          "payload_count": 235, "applied_count": 7, "retained_count": 228, "create_count": 2,
          "logical_original_count": 5, "native_original_count": 5, "all_native_original_identities_and_metadata_preserved": True,
          "before_current_hashes": current, "after_current_hashes": after, "observations": observations,
          "imports": imports, "module_count": 72, "imports_all_actual_S": True,
          "source_unchanged": True, "remaining_staged_files": 0,
          "claim_note": "Root claim identity compared with initial observed claim and immutable journal; runtime claims/state not read or modified during completion",
          "suite_status": "Full active destination suite running; final acceptance awaits its actual results",
          "shared_administration": "Same Windows host/principal and declared same-project e3 environment; independent reviewer reads actual S payloads with verified native handles",
          "exit_status": 0}
with (R / "applied-source-audit.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: result[key] for key in ("payload_count", "applied_count", "retained_count", "create_count", "logical_original_count", "native_original_count", "module_count", "source_unchanged", "remaining_staged_files", "exit_status")}))
