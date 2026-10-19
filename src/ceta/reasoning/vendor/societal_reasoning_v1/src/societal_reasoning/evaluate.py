"""Offline deterministic behavior contract evaluator (not empirical accuracy measurement)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import SocietalReasoner
from .models import Scenario


def evaluate_cases(reasoner: SocietalReasoner, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one evaluation case is required")
    seen: set[str] = set()
    results = []
    for row in records:
        if not isinstance(row, dict) or set(row) != {"id", "scenario", "expected_status", "expected_primary"}:
            raise ValueError("Evaluation case requires exactly id, scenario, expected_status, expected_primary")
        case_id = row["id"]
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError("Evaluation case IDs must be distinct nonblank strings")
        seen.add(case_id)
        if not isinstance(row["expected_status"], str) or not row["expected_status"]:
            raise ValueError("Expected status must be a nonempty string")
        if row["expected_primary"] is not None and not isinstance(row["expected_primary"], str):
            raise ValueError("Expected primary rule ID must be a string or null")
        scenario = Scenario.from_dict(row["scenario"])
        observed = reasoner.analyze(scenario)
        primary = observed["primary"]["rule_id"] if observed["primary"] else None
        passed = observed["status"] == row["expected_status"] and primary == row["expected_primary"]
        results.append({"id": case_id, "pass": passed,
                        "expected": {"status": row["expected_status"], "primary": row["expected_primary"]},
                        "observed": {"status": observed["status"], "primary": primary}})
    return {"suite_type": "developer_authored_regression_not_empirical_accuracy",
            "cases": len(results), "passed": sum(r["pass"] for r in results),
            "failed": sum(not r["pass"] for r in results), "results": results}


def evaluate_file(reasoner: SocietalReasoner, path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation file must contain a JSON array")
    return evaluate_cases(reasoner, data)
