"""Build a truthful, stable 120-requirement implementation tracking register.

Statuses are independent of mere code existence. This is an engineering progress
register, not a Codex conformance or external-evaluation certificate.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"^- \*\*([A-L][0-9]{2}):\*\* (.+)$", re.MULTILINE)

# Verified in a bounded local test suite; no generalization claims.
VERIFIED = {
    "A02": ("src/societal_reasoning/__init__.py", "tests/test_release_policy.py"),
    "B01": ("src/societal_reasoning/input_boundary.py", "tests/test_text_contract.py"),
    "B02": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "E01": ("scripts/compile_inventory.py", "tests/test_full_inventory.py"),
    "K01": ("run.py", "tests/test_launcher.py"),
    "L02": ("scripts/build_release.py", "tests/test_evaluate.py"),
}
# Implemented only narrowly and explicitly not an accepted whole-domain solution.
PARTIAL = {
    "A01": ("docs/OBJECTIVE_AND_BOUNDARIES.md", "tests/test_text_contract.py"),
    "A03": ("src/societal_reasoning/engine.py", "tests/test_text_contract.py"),
    "A04": ("src/societal_reasoning/engine.py", "tests/test_engine.py"),
    "A06": ("src/societal_reasoning/input_boundary.py", "tests/test_text_contract.py"),
    "A08": ("src/societal_reasoning/engine.py", "tests/test_engine.py"),
    "A10": ("docs/REASONING_SPEC.md", "tests/test_text_contract.py"),
    "B03": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "B04": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "B05": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "B06": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "B07": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "B08": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "B09": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "B10": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "C01": ("src/societal_reasoning/semantics.py", "tests/test_semantics.py"),
    "C02": ("src/societal_reasoning/semantics.py", "tests/test_semantics.py"),
    "C03": ("src/societal_reasoning/semantics.py", "tests/test_text_contract.py"),
    "C04": ("src/societal_reasoning/semantics.py", "tests/test_text_contract.py"),
    "C05": ("src/societal_reasoning/semantics.py", "tests/test_text_contract.py"),
    "C06": ("src/societal_reasoning/semantics.py", "tests/test_text_contract.py"),
    "C08": ("src/societal_reasoning/claims.py", "tests/test_text_contract.py"),
    "D01": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "D02": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "D03": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "D05": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "D09": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "D10": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "G01": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "G03": ("src/societal_reasoning/semantic_support.py", "tests/test_semantic_support.py"),
    "G04": ("src/societal_reasoning/semantic_support.py", "tests/test_semantic_support.py"),
    "G05": ("src/societal_reasoning/semantic_support.py", "tests/test_semantic_support.py"),
    "G07": ("src/societal_reasoning/semantic_support.py", "tests/test_semantic_support.py"),
    "G04": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "G07": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "H05": ("src/societal_reasoning/effects.py", "tests/test_context.py"),
    "H06": ("src/societal_reasoning/effects.py", "tests/test_context.py"),
    "H07": ("src/societal_reasoning/effects.py", "tests/test_context.py"),
    "H09": ("src/societal_reasoning/effects.py", "tests/test_context.py"),
    "H10": ("src/societal_reasoning/effects.py", "tests/test_context.py"),
    "I03": ("src/societal_reasoning/engine.py", "tests/test_text_contract.py"),
    "I04": ("src/societal_reasoning/semantics.py", "tests/test_text_contract.py"),
    "I07": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "I08": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "K02": ("src/societal_reasoning/cli.py", "tests/test_cli_text.py"),
    "K03": ("src/societal_reasoning/engine.py", "tests/test_cli_text.py"),
    "K07": ("src/societal_reasoning/response_review.py", "tests/test_text_contract.py"),
    "K08": ("src/societal_reasoning/input_boundary.py", "tests/test_text_contract.py"),
    "K09": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "L01": ("scripts/requirement_register.py", "tests/test_release_policy.py"),
    "L03": ("tests/test_text_contract.py", "tests/test_text_contract.py"),
    "L05": ("src/societal_reasoning/context.py", "tests/test_context.py"),
    "E05": ("src/societal_reasoning/relevance.py", "tests/test_relevance.py"),
    "E06": ("src/societal_reasoning/relevance.py", "tests/test_relevance.py"),
    "E09": ("src/societal_reasoning/relevance.py", "tests/test_relevance.py"),
    "J01": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J02": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J03": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J04": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J05": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J06": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J07": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "J08": ("tests/test_corrections.py", "tests/test_corrections.py"),
    "J09": ("src/societal_reasoning/corrections.py", "tests/test_corrections.py"),
    "D04": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "D05": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "F03": ("src/societal_reasoning/semantic_support.py", "tests/test_semantic_support.py"),
    "F06": ("src/societal_reasoning/reading_support.py", "tests/test_reading_support.py"),
    "F05": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "F07": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "F08": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "F09": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "F10": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
    "G08": ("src/societal_reasoning/deliberation.py", "tests/test_deliberation.py"),
}
BLOCKED = {
    "E02": "Requires an authoritative original-source export; not provided.",
    "L04": "Independent hidden scenario benchmark not constructed.",
    "L06": "Independent blind human review not conducted.",
    "L07": "Matched AI model comparison not conducted.",
    "L10": "Redistribution license and publication require owner decisions.",
}


def create_register() -> dict:
    source = (ROOT / "docs" / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    items = PATTERN.findall(source)
    if len(items) != 120 or len({key for key, _ in items}) != 120:
        raise ValueError("Plan requirement registry is not exactly 120 unique A01-L10 entries")
    if {key for key, _ in items} != {f"{chr(letter)}{i:02d}" for letter in range(65, 77) for i in range(1, 11)}:
        raise ValueError("Missing or unexpected requirement identifiers")
    if (set(VERIFIED) & set(PARTIAL)) or ((set(VERIFIED) | set(PARTIAL) | set(BLOCKED)) - {r for r, _ in items}):
        raise ValueError("Invalid requirement status assignment")
    rows = []
    for key, phrase in items:
        if key in VERIFIED:
            status, paths, reason = "verified_bounded", VERIFIED[key], "Specific local behavior tested; broader intent may require additional evidence."
        elif key in PARTIAL:
            status, paths, reason = "partial", PARTIAL[key], "Only named bounded behavior is implemented; full requirement remains open."
        elif key in BLOCKED:
            status, paths, reason = "blocked_external_or_independent_evidence", (), BLOCKED[key]
        else:
            status, paths, reason = "not_implemented_or_not_verified", (), "No acceptance evidence exists for full requirement."
        for p in paths:
            if not (ROOT / p).is_file():
                raise ValueError(f"Referenced traceability artifact missing: {p}")
        rows.append({"id": key, "requirement": phrase, "status": status,
                     "implementation": list(paths[:1]), "test_reference": list(paths[1:]),
                     "acceptance_proof": "local_test_only" if status == "verified_bounded" else "not_established",
                     "limitations": reason})
    return {"version": "1", "type": "development_traceability_not_conformance_certificate",
            "planned_requirements": len(rows),
            "counts": {k: sum(1 for x in rows if x["status"] == k)
                       for k in ("verified_bounded", "partial", "blocked_external_or_independent_evidence", "not_implemented_or_not_verified")},
            "requirements": rows}


def main() -> None:
    r = create_register()
    (ROOT / "docs" / "TRACEABILITY.json").write_text(json.dumps(r, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(r["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
