"""Run the actual contract suite with exact source cuts and retained output."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from development_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
REPORT_ROOT = ROOT / ".agents/test-evidence"


def snapshot() -> dict[str, str]:
    return {name: row["sha256"] for name, row in inventory(ROOT)["files"].items()
            if row["source_test_watched"]}


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) == 2 else "desktop-contract-source-bound-01"
    if not re.fullmatch(r"[a-z0-9-]{1,80}", run_id):
        raise ValueError("invalid run identity")
    if not REPORT_ROOT.is_dir() or REPORT_ROOT.is_symlink() or REPORT_ROOT.is_junction():
        raise ValueError("authorized evidence directory is unavailable")
    report_path, log_path = REPORT_ROOT / (run_id + ".json"), REPORT_ROOT / (run_id + ".txt")
    if report_path.exists() or log_path.exists():
        raise ValueError("run evidence already exists; use a new run identity")
    before = snapshot()
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, check=True, text=True).stdout.strip()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/contract"), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = snapshot()
    unchanged = before == after
    report = {
        "schema_version": "1", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "CONTRACTS_TOOLS_AND_REAL_FIXTURE_SQLITE_HISTORY_NO_AUTHENTICATED_EFFECT_OR_INSTALLED_QUALIFICATION",
        "root": str(ROOT), "git_head": head, "python": sys.version,
        "interpreter": sys.executable,
        "interpreter_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "source_before_sha256": before, "source_after_sha256": after,
        "source_unchanged": unchanged, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "skip_details": result.skipped,
        "failed_test_ids": [test.id() for test, _ in result.failures + result.errors],
        "dependencies": {name: importlib.metadata.version(name) for name in
                         ("jsonschema", "rfc3339-validator", "attrs", "jsonschema-specifications",
                          "referencing", "rpds-py", "six", "typing-extensions")},
        "result": "PASS" if result.wasSuccessful() and unchanged and not result.skipped else "FAIL_OR_INCOMPLETE",
        "runtime_qualification": "NOT_RUN", "independent_review": "NOT_PERFORMED",
        "installed_qualification": "NOT_RUN", "endurance": "NOT_RUN",
    }
    with log_path.open("x", encoding="utf-8") as file:
        file.write(output.getvalue())
    report["complete_log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()
    with report_path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    print(json.dumps({key: report[key] for key in ("scope", "result", "tests_run", "failures", "errors",
                                                  "skipped", "source_unchanged")}))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
