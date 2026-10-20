"""Separate build evidence axes; applicability is never a completion percentage."""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

INPUTS = {
    "coverage": "standards/lifecycle_coverage.json",
    "authority": "handoff/source_authority_register.json",
    "progress": "build/progress.json",
    "gates": "build/gates.json",
    "cases": "acceptance/scenarios.json",
    "components": "architecture/components.json",
    "requirements": "requirements/requirements.json",
    "packages": "build/work_packages.json",
}
COVERAGE_SHA256 = "816d692ebf0d5b7b148ff2a021a8c994f59778a38a308542d08342289823e0b8"


def measurements(documents: dict) -> dict:
    rows = documents["coverage"]["sections"]
    classes = Counter(row["applicability"] for row in rows)
    if set(classes) - {"DIRECT", "SUPPORTING", "NOT_APPLICABLE", "UNRESOLVED"}:
        raise ValueError("UNKNOWN_APPLICABILITY")
    return {
        "profile": "ceta-build-evidence-measurements-v1",
        "applicability_classification": {"total_sections": len(rows),
            "classified_sections": len(rows) - classes["UNRESOLVED"],
            "unresolved_applicability_classifications": classes["UNRESOLVED"],
            "class_counts": dict(classes)},
        "source_reconciliation": {
            "state": documents["authority"]["current_source_coverage_state"],
            "latest_working_record": documents["authority"].get("latest_supplemental_working_record"),
            "registered_volume_count": len(documents["authority"]["volume_sources"]),
            "limit": "CLASSIFIED_APPLICABILITY_DOES_NOT_ESTABLISH_COMPLETE_RECONCILIATION"},
        "requirement_adoption": {"state": documents["authority"]["adoption"],
            "registered_requirement_groups": len(documents["requirements"]["requirements"])},
        "implementation": {"runtime_state": documents["progress"]["runtime_implementation"],
            "lifecycle_status_counts": dict(Counter(row["implementation_status"] for row in rows)),
            "registered_components": len(documents["components"]["components"]),
            "registered_work_packages": len(documents["packages"]["packages"])},
        "conformance_verification": {
            "lifecycle_status_counts": dict(Counter(row["conformance_status"] for row in rows)),
            "original_case_result_counts": dict(Counter(row["result"] for row in documents["cases"]["scenarios"])),
            "test_execution_state": documents["progress"]["test_execution"],
            "installed_state": documents["progress"]["installed_qualification"]},
        "independent_acceptance": {"state": documents["authority"]["independent_review"]},
        "gate_qualification": {row["id"]: row["state"] for row in documents["gates"]["gates"]},
        "full_product": documents["progress"]["goal_state"],
        "completion_inferred_from_applicability": False,
    }


def collect(root: Path) -> dict:
    root = root.resolve(strict=True)
    wires = {name: (root / rel).read_bytes() for name, rel in INPUTS.items()}
    if hashlib.sha256(wires["coverage"]).hexdigest() != COVERAGE_SHA256:
        raise ValueError("PRESERVED_COVERAGE_COMMITMENT_MISMATCH")
    result = measurements({name: json.loads(wire) for name, wire in wires.items()})
    if any((root / INPUTS[name]).read_bytes() != wire for name, wire in wires.items()):
        raise ValueError("MEASUREMENT_INPUT_CHANGED")
    result["verified_input_sha256"] = {INPUTS[name]: hashlib.sha256(wire).hexdigest() for name, wire in wires.items()}
    result["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specification-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = collect(args.specification_root)
    with args.report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"report": str(args.report), "applicability": result["applicability_classification"],
                      "full_product": result["full_product"]}))


if __name__ == "__main__":
    main()
