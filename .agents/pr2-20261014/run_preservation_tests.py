"""Run the native suite once and retain exact console output and a JSON receipt."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-directory", required=True, type=Path)
    parser.add_argument("--run-label", required=True)
    args = parser.parse_args()
    cut = Path(__file__).parent.absolute()
    expected = cut.parent / "runtime" / cut.name
    if args.report_directory.absolute() != expected or not args.run_label.replace("-", "").isalnum():
        raise ValueError("receipt destination must be this cut's exact assigned runtime directory")
    expected.mkdir(parents=True, exist_ok=True)
    log = expected / (args.run_label + ".txt")
    receipt = expected / (args.run_label + ".json")
    if log.exists() or receipt.exists():
        raise ValueError("receipt overwrite refused")
    command = [sys.executable, "-B", "-m", "unittest", "-v", "test_preserve_ceta_complete"]
    names = ("preserve_ceta_complete.py", "test_preserve_ceta_complete.py", "run_preservation_tests.py", "README.md")
    before = [{"path": str(cut / name), "sha256": hashlib.sha256((cut / name).read_bytes()).hexdigest()} for name in names]
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(command, cwd=cut, capture_output=True)
    after = [{"path": str(cut / name), "sha256": hashlib.sha256((cut / name).read_bytes()).hexdigest()} for name in names]
    source_unchanged = before == after
    exit_status = completed.returncode if source_unchanged else 1
    output = completed.stdout + completed.stderr
    with log.open("xb") as stream:
        stream.write(output)
    value = {"schema_version": 1, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
             "command_argv": command, "workdir": str(cut), "exit_status": exit_status, "test_exit_status": completed.returncode,
             "source_unchanged_before_after": source_unchanged,
             "output_path": str(log), "output_sha256": hashlib.sha256(output).hexdigest(),
             "source_files_before": before, "source_files_after": after,
             "scope": "ACTUAL_DISPOSABLE_WINDOWS_RESOURCES_ONLY_REAL_CETA_CAPTURE_NOT_RUN"}
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    print(output.decode("utf-8", errors="replace"))
    print(json.dumps(value, indent=2))
    return exit_status


if __name__ == "__main__":
    sys.exit(main())
