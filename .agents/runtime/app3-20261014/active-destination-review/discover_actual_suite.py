"""Independent actual-S test discovery and current full-run preflight comparison."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib
import json
import os
import sys
import unittest

R = Path(__file__).resolve().parent
S = R.parents[3]
E3 = S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
assert Path(sys.executable).resolve() == E3.resolve()
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path[:0] = [str(S / "src"), str(S / "tools"), str(S / "tests/contract")]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
started = datetime.now(timezone.utc).isoformat()
preflight_path = S / ".agents/runtime/rs2-20261014/active-application/destination-full-r2-preflight.json"
preflight = read(preflight_path)
assert preflight["root"] == str(S) and preflight["python_executable"] == str(E3)
assert preflight["cut_bindings"][-1]["sha256"] == "491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b"
current = {relative: sha(S / relative) for relative in preflight["expected_payload_hashes"]}
assert len(current) == 235 and current == preflight["expected_payload_hashes"] == preflight["before_hashes"]
suite = unittest.TestLoader().discover(str(S / "tests/contract"), pattern="test_*.py")

def ids(value):
    if isinstance(value, unittest.TestSuite):
        for child in value:
            yield from ids(child)
    else:
        yield value.id()

discovered = list(ids(suite))
assert len(discovered) == len(set(discovered)) and not any("_FailedTest" in name for name in discovered)
assert discovered == preflight["expected_ids"]
assert len(discovered) == 1158
module_paths = []
for name, module in tuple(sys.modules.items()):
    if name == "ceta" or name.startswith("ceta."):
        actual = Path(module.__file__).resolve()
        assert actual.is_relative_to(S / "src"), (name, actual)
        module_paths.append({"module": name, "actual_path": str(actual), "sha256": sha(actual)})
dependencies = []
for item in preflight["dependencies"]:
    module = importlib.import_module(item["module"])
    actual = Path(module.__file__).resolve()
    assert actual == Path(item["actual_path"])
    assert actual.is_relative_to(E3.parent.parent / "Lib/site-packages")
    assert sha(actual) == item["module_file_sha256"]
    dependencies.append(item)
after = {relative: sha(S / relative) for relative in current}
assert after == current
record = {"schema_version": 1, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
          "source_root": str(S), "preflight": str(preflight_path), "preflight_sha256": sha(preflight_path),
          "discovered_ids": discovered, "test_count": len(discovered), "same_as_root_full_run_preflight": True,
          "source_hashes": current, "source_after_hashes": after, "source_unchanged": True,
          "actual_imports": module_paths, "dependencies": dependencies,
          "distribution_metadata_limit": "PySide6 distribution metadata absence remains explicitly recorded; actual module bytes and PySide6_Essentials/runtime versions are separately identified",
          "tests_executed_by_this_discovery": 0, "exit_status": 0}
with (R / "actual-suite-discovery.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({"test_count": len(discovered), "same_as_root_full_run_preflight": True,
                  "source_unchanged": True, "tests_executed": 0, "exit_status": 0}))
