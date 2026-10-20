"""Publish the four reviewed process-observation timing and validation paths with native originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os

R = Path(__file__).resolve().parent
F = R.parents[2]
RUN = "gd2-20261014"
Q = F / ".agents" / RUN
OUT = R / "active-application"
ALLOWED = frozenset({"src/ceta/resource/diagnostics.py", "tests/contract/test_process_observation_timing.py", "tests/contract/test_process_observation_validation.py", "contracts/PROCESS_DIAGNOSTICS_V1.md"})
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PUBLICATION = F / ".agents/runtime/rs2-20261014/apply_joined_source.py"
assert sha(PUBLICATION) == "4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77"
spec = importlib.util.spec_from_file_location("ceta_process_timing_native_publication", PUBLICATION)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def save(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def main():
    claim = read(R / RUN / "claims.json")["integrate"]
    assert claim["executor_id"] == "/root" and claim["workspace"] == str(F)
    state = read(R / RUN / "state.json")
    assert state["nodes"]["review"]["state"] == state["nodes"]["validate"]["state"] == "SUCCEEDED"
    review_path = R / "independent-review/review.json"
    review = read(review_path)
    assert review["decision"] == "approved" and review["exit_status"] == 0
    helper_review = read(R / "independent-review/publication-helper-review.json")
    assert helper_review["decision"] == "approved" and helper_review["exit_status"] == 0
    assert helper_review["publication_script_sha256"] == sha(Path(__file__))
    manifest_path = Q / "TRANSFER-MANIFEST.json"
    assert sha(manifest_path) == "cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a"
    manifest = read(manifest_path)
    selected = []
    for item in manifest["payloads"]:
        relative = item["relative_path"]
        native.fs.relative_name(relative)
        assert native.exact_hash(Q / relative) == item["candidate_sha256"]
        target = native.fs.safe_components(F / relative, allow_missing=item["active_before_sha256"] is None)
        actual = native.exact_hash(target) if native.fs.exists(target) else None
        assert actual == item["active_before_sha256"], ("source drift", relative)
        if relative in ALLOWED:
            assert item["action"] in {"EXTEND", "CREATE"}
            selected.append(item)
        else:
            assert item["action"] == "REUSE" and item["candidate_sha256"] == item["active_before_sha256"]
    assert len(manifest["payloads"]) == 281 and {item["relative_path"] for item in selected} == ALLOWED
    assert sum(item["action"] == "CREATE" for item in selected) == 2
    assert sum(item["action"] == "EXTEND" for item in selected) == 2
    native.fs.safe_components(OUT, allow_missing=True)
    OUT.mkdir(exist_ok=False)
    originals = []
    for item in selected:
        relative = item["relative_path"]
        stage = OUT / "staged" / relative
        before = OUT / "before" / (relative + ".source")
        backup = OUT / "native-backups" / (relative + ".original")
        for parent in (stage.parent, before.parent, backup.parent):
            native.fs.safe_components(parent, allow_missing=True)
            parent.mkdir(parents=True, exist_ok=True)
            native.fs.safe_components(parent)
        with native.fs.open_source(native.fs.safe_components(Q / relative), exclusive=True) as source:
            candidate = source.read()
            assert hashlib.sha256(candidate).hexdigest() == item["candidate_sha256"]
            with stage.open("xb") as output:
                output.write(candidate)
                output.flush()
                os.fsync(output.fileno())
        if item["active_before_sha256"] is not None:
            with native.fs.open_source(native.fs.safe_components(F / relative), exclusive=True) as source:
                data = source.read()
                assert hashlib.sha256(data).hexdigest() == item["active_before_sha256"]
                facts = os.fstat(source.fileno())
                with before.open("xb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                originals.append({"relative_path": relative, "sha256": item["active_before_sha256"],
                    "device": facts.st_dev, "inode": facts.st_ino, "mode": facts.st_mode,
                    "bytes": facts.st_size, "mtime_ns": facts.st_mtime_ns})
    started = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(), "executor": "/root",
        "source_root": str(F), "claim_input_hash": claim["input_hash"], "manifest_sha256": sha(manifest_path),
        "review_sha256": sha(review_path), "helper_review_sha256": sha(R / "independent-review/publication-helper-review.json"),
        "before_images": originals}
    save(OUT / "STARTED.json", started)
    completed = []
    try:
        for item in selected:
            relative = item["relative_path"]
            native.publish_prepared(OUT / "staged" / relative, F / relative,
                OUT / "native-backups" / (relative + ".original"), item["active_before_sha256"], item["candidate_sha256"])
            completed.append({"relative_path": relative, "sha256": item["candidate_sha256"]})
        save(OUT / "APPLIED.json", {**started, "completed": completed,
            "finished_at": datetime.now(timezone.utc).isoformat(), "status": "FOUR_PROCESS_OBSERVATION_PATHS_APPLIED_AWAITING_DESTINATION_VERIFICATION"})
    except BaseException as error:
        try:
            save(OUT / "FAILED.json", {**started, "completed": completed,
                "failed_at": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__, "error": str(error),
                "recovery": "Preserve targets, stages, logical/native originals and reconcile exact four paths under fresh review"})
        except BaseException as journal_error:
            error.add_note("Publication failure journal could not be written: " + type(journal_error).__name__)
        raise
    print(json.dumps({"actual_process_timing_paths_applied": len(completed), "originals_preserved": len(originals),
                      "application_journal_sha256": sha(OUT / "APPLIED.json")}))


if __name__ == "__main__":
    main()
