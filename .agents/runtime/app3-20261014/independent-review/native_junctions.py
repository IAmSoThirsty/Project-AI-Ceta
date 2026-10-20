"""Real, retained Windows junction refusals within the review's own fixtures."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parent
S = R.parents[3]
publication = S / ".agents/runtime/rs2-20261014/apply_joined_source.py"
spec = importlib.util.spec_from_file_location("app3_real_junction_publication", publication)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)
sha = lambda data: hashlib.sha256(data).hexdigest()
started = datetime.now(timezone.utc).isoformat()
script_hash_before = sha(publication.read_bytes())
parent = R / "junction-fixtures-r1"
parent.mkdir(exist_ok=False)
cases = []
for component in ("staged", "target", "backup"):
    root = Path(tempfile.mkdtemp(prefix=component + "-", dir=parent))
    physical = root / "ordinary-owned-directory"
    physical.mkdir()
    link = root / "owned-junction"
    assert root.resolve().is_relative_to(R.resolve()) and physical.resolve().is_relative_to(R.resolve())
    assert not link.exists()
    argv = ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(physical)]
    created = subprocess.run(argv, capture_output=True)
    record = {"component": component, "argv": argv, "create_exit_status": created.returncode,
              "create_stdout": created.stdout.decode("utf-8", errors="replace"),
              "create_stderr": created.stderr.decode("utf-8", errors="replace"),
              "junction": str(link), "target_directory": str(physical)}
    assert created.returncode == 0 and pub.fs.reparse(pub.fs.lstat(link)), record
    physical_stage, physical_target, physical_backup = root / "stage.py", root / "target.py", root / "backup.py"
    if component == "staged":
        physical_stage = physical / "stage.py"
    elif component == "target":
        physical_target = physical / "target.py"
    else:
        physical_backup = physical / "backup.py"
    old, new = b"owned original\n", b"owned candidate\n"
    physical_target.write_bytes(old)
    physical_stage.write_bytes(new)
    stage = link / "stage.py" if component == "staged" else physical_stage
    target = link / "target.py" if component == "target" else physical_target
    backup = link / "backup.py" if component == "backup" else physical_backup
    try:
        pub.publish_prepared(stage, target, backup, sha(old), sha(new))
    except pub.fs.PreservationError as error:
        assert "reparse path component is forbidden" in str(error), str(error)
        record["refused"] = True
        record["refusal"] = str(error)
    else:
        raise AssertionError("Real junction component was allowed to reach publication")
    assert physical_target.read_bytes() == old and physical_stage.read_bytes() == new
    assert not physical_backup.exists()
    record.update({"original_sha256": sha(physical_target.read_bytes()),
                   "stage_sha256": sha(physical_stage.read_bytes()), "backup_absent": True,
                   "fixtures_preserved": True})
    cases.append(record)
script_hash_after = sha(publication.read_bytes())
assert script_hash_before == script_hash_after
result = {"schema_version": 1, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
          "case_count": len(cases), "cases": cases, "source_before_sha256": script_hash_before,
          "source_after_sha256": script_hash_after, "source_unchanged": True, "exit_status": 0,
          "scope": "Three actual Windows junctions created and retained solely inside independent-review fixture scope; no source writes or external targets"}
with (R / "native-junctions-r1.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({"case_count": len(cases), "source_unchanged": True, "exit_status": 0}))
