"""Verify the exact preservation and write scope of the current rebuild increment."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("preservation", ROOT / "tools/preserve_ceta_baseline.py")
preservation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preservation)


def main() -> int:
    errors, results = [], []
    checkpoints = ("desktop-baseline-20261006-01", "reference-baseline-20261006-01")
    for name in checkpoints:
        base = ROOT / ".local-build-cache" / name
        original = json.loads((base / "inventory.json").read_bytes())
        current = preservation.inventory(Path(original["root"]))
        expected = {row["path"]: row for row in original["files"]}
        actual = {row["path"]: row for row in current["files"]}
        changed = [path for path, row in expected.items() if actual.get(path) != row]
        added = sorted(set(actual) - set(expected))
        if name.startswith("reference"):
            if original != current:
                errors.append("REFERENCE_BASELINE_CHANGED")
        else:
            if any(path != "docs/operations/CONTINUITY_MAP.md" for path in changed):
                errors.append("RETAINED_DESKTOP_SOURCE_CHANGED")
            for path in changed:
                previous = (base / "restoration-proof" / path).read_bytes()
                now = (Path(original["root"]) / path).read_bytes()
                if not now.startswith(previous):
                    errors.append("CONTINUITY_HISTORY_REWRITTEN")
            if any(not path.startswith("rebuild_ios/") for path in added):
                errors.append("NEW_DESKTOP_PATH_OUTSIDE_NAMESPACE")
            if current["head"] != original["head"] or current["branch"] != original["branch"]:
                errors.append("DESKTOP_BASELINE_IDENTITY_CHANGED")
        results.append({"root": current["root"], "head": current["head"], "branch": current["branch"],
                        "baseline_files": len(expected), "changed_baseline_paths": changed,
                        "added_paths": added, "current_status": current["status"],
                        "retained_source_bytes": "PASS" if not errors else "REVIEW_REQUIRED"})
    # Only top-level profile metadata is read; no database/key/conversation bytes.
    profile_record = json.loads((ROOT / "evidence/runtime/live-profile-metadata-20261006-01.json").read_bytes())
    profile = Path(profile_record["profile_path"])
    profile_changes = []
    for row in profile_record["files"]:
        path = profile / row["name"]
        if not path.exists():
            profile_changes.append(row["name"])
            continue
        stat = path.stat()
        observed_time = datetime.fromisoformat(row["last_write_utc"].replace("Z", "+00:00")).timestamp()
        if abs(stat.st_mtime - observed_time) > 0.000001 or (row["bytes"] is not None and stat.st_size != row["bytes"]):
            profile_changes.append(row["name"])
    added_profile_paths = sorted({path.name for path in profile.iterdir()} -
                                 {row["name"] for row in profile_record["files"]}) if profile.is_dir() else []
    if profile_changes or added_profile_paths:
        errors.append("NORMAL_PROFILE_METADATA_CHANGED_REQUIRES_RECONCILIATION")
    report = {"schema_version": "1", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "RETAINED_SOURCE_AND_WRITE_SCOPE_AUDIT",
              "result": "PASS" if not errors else "FAIL", "errors": errors, "worktrees": results,
              "normal_profile": {"path": str(profile), "inspection": "TOP_LEVEL_METADATA_ONLY",
                                 "changed_metadata_paths": profile_changes,
                                 "added_paths": added_profile_paths, "contents_read": False,
                                 "limit": "Metadata does not prove byte integrity or OS confinement."},
              "runtime_qualification": "NOT_RUN", "production_cutover": "NOT_PERFORMED"}
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
