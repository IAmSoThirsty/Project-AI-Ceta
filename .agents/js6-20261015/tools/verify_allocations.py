"""Check declared CETA baseline allocation links; never promote runtime readiness.

Current registries are compared with the preserved manifest-bound identifier sets.
This is document/relationship tooling, not an interface implementation, kernel,
security boundary, independent review or acceptance test of the running product.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from verify_source_coverage import (ContractError, ORIGINAL_MANIFEST_SHA256,
                                    preserved_registry, require_unchanged,
                                    safe_path, snapshot, strict_loads)

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {
    "requirements": ("requirements/requirements.json", "requirements"),
    "components": ("architecture/components.json", "components"),
    "packages": ("build/work_packages.json", "packages"),
    "cases": ("acceptance/scenarios.json", "scenarios"),
    "gates": ("build/gates.json", "gates"),
}


def check_models(models: dict, expected_ids: dict[str, set[str]]) -> list[str]:
    """Inspect supplied in-memory registries without I/O or state promotion."""
    errors: set[str] = set()
    indexed: dict[str, dict[str, dict]] = {}
    for name in REGISTRIES:
        rows = models.get(name)
        index = {}
        if type(rows) is not list:
            errors.add("MALFORMED_REGISTRY:" + name)
            rows = []
        for row in rows:
            if type(row) is not dict or type(row.get("id")) is not str or not row["id"]:
                errors.add("MALFORMED_ROW:" + name)
                continue
            if row["id"] in index:
                errors.add("DUPLICATE_ID:" + name + ":" + row["id"])
            index[row["id"]] = row
        if set(index) != expected_ids.get(name):
            errors.add("ORIGINAL_ID_SET_CHANGED:" + name)
        indexed[name] = index

    def refs(row: dict, field: str, known: set[str], *, required: bool = True) -> set[str]:
        values = row.get(field)
        context = row["id"] + ":" + field
        if (type(values) is not list or any(type(v) is not str or not v for v in values)
                or len(values) != len(set(values))):
            errors.add("MALFORMED_REFERENCES:" + context)
            return set()
        if required and not values:
            errors.add("EMPTY_REFERENCES:" + context)
        for value in set(values) - known:
            errors.add("UNKNOWN_REFERENCE:" + context + ":" + value)
        return set(values) & known

    requirements, components, packages, cases, gates = (indexed[n] for n in REGISTRIES)
    component_ids = set(components)
    section_ids = {r["section"] for r in requirements.values()
                   if type(r.get("section")) is str and r["section"]}
    slugs = {r["slug"] for r in components.values() if type(r.get("slug")) is str and r["slug"]}
    if len(slugs) != len(components):
        errors.add("COMPONENT_SLUG_MISSING_OR_DUPLICATE")
    component_sections = {}
    component_graph = {}
    for row in components.values():
        component_sections[row["id"]] = refs(row, "section_ids", section_ids)
        dependencies = refs(row, "allowed_static_dependencies", slugs, required=False)
        if type(row.get("slug")) is str:
            component_graph[row["slug"]] = dependencies

    for row in requirements.values():
        section = row.get("section")
        if type(section) is not str or not section:
            errors.add("MALFORMED_REQUIREMENT_SECTION:" + row["id"])
        owner = row.get("component_owner")
        if type(owner) is not str or owner not in component_ids | {"LEAD_INTEGRATOR"}:
            errors.add("UNKNOWN_REQUIREMENT_OWNER:" + row["id"])
        elif owner in component_ids and (type(section) is not str or section not in component_sections[owner]):
            errors.add("OWNER_SECTION_MISMATCH:" + row["id"])
        targets = refs(row, "acceptance_ids", set(cases))
        for case_id in targets:
            case_requirements = cases[case_id].get("requirement_ids")
            if type(case_requirements) is list and row["id"] not in case_requirements:
                errors.add("CASE_MISSING_REQUIREMENT_LINK:" + row["id"] + ":" + case_id)
    for row in cases.values():
        refs(row, "requirement_ids", set(requirements))

    allocated_requirements, allocated_cases, allocated_components = set(), set(), set()
    package_graph = {}
    for row in packages.values():
        allocated_requirements.update(refs(row, "requirement_ids", set(requirements)))
        allocated_cases.update(refs(row, "acceptance_ids", set(cases)))
        allocated_components.update(refs(row, "component_owners", component_ids | {"LEAD_INTEGRATOR"}))
        package_graph[row["id"]] = refs(row, "depends_on", set(packages), required=False)
        if type(row.get("target_gate")) is not str or row["target_gate"] not in gates:
            errors.add("UNKNOWN_TARGET_GATE:" + row["id"])
    for req in set(requirements) - allocated_requirements:
        errors.add("UNALLOCATED_REQUIREMENT:" + req)
    for case in set(cases) - allocated_cases:
        errors.add("UNALLOCATED_CASE:" + case)
    for component in component_ids - allocated_components:
        errors.add("UNALLOCATED_COMPONENT:" + component)
    for row in gates.values():
        refs(row, "required_work_packages", set(packages))

    # Iterative topological elimination avoids recursion on hostile deep graphs.
    def acyclic(graph: dict[str, set[str]], label: str):
        pending = {node: set(deps) for node, deps in graph.items()}
        while pending:
            leaves = {node for node, deps in pending.items() if not deps}
            if not leaves:
                errors.add(label)
                return
            pending = {node: deps - leaves for node, deps in pending.items() if node not in leaves}

    acyclic(component_graph, "COMPONENT_DEPENDENCY_CYCLE")
    acyclic(package_graph, "WORK_PACKAGE_DEPENDENCY_CYCLE")
    return sorted(errors)


def verify(root: Path) -> dict:
    errors = []
    inputs = {}
    models = {}
    try:
        root = root.resolve(strict=True)
        paths = ["PACKAGE_MANIFEST.json"] + [p for p, _ in REGISTRIES.values()]
        paths += [".local-build-cache/restoration-proof/" + p for p, _ in REGISTRIES.values()]
        before = snapshot(root, paths)
        if before["PACKAGE_MANIFEST.json"] != ORIGINAL_MANIFEST_SHA256:
            raise ContractError("ORIGINAL_MANIFEST_CHANGED")
        manifest = strict_loads(safe_path(root, "PACKAGE_MANIFEST.json").read_bytes())
        rows = manifest["files"]
        original = {r["path"]: r for r in rows}
        if len(original) != len(rows):
            raise ContractError("DUPLICATE_MANIFEST_PATH")
        expected_ids = {}
        for name, (path, key) in REGISTRIES.items():
            baseline = preserved_registry(root, original, path)[key]
            values = [row["id"] for row in baseline]
            if len(values) != len(set(values)):
                raise ContractError("DUPLICATE_PRESERVED_REGISTRY_ID")
            expected_ids[name] = set(values)
            models[name] = strict_loads(safe_path(root, path).read_bytes())[key]
        errors.extend(check_models(models, expected_ids))
        after = snapshot(root, paths)
        require_unchanged(before, after)
        inputs = after
    except ContractError as exc:
        errors.append(exc.code)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {"schema_version": "1", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "DECLARED_BASELINE_ALLOCATION_REFERENCES_AND_DEPENDENCY_GRAPHS_ONLY",
            "result": "FAIL" if errors else "PASS", "errors": errors,
            "registry_counts": {name: len(rows) for name, rows in models.items() if type(rows) is list},
            "input_sha256": inputs,
            "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "runtime_qualification": "NOT_RUN", "interface_implementation": "NOT_VERIFIED",
            "semantic_source_conformance": "NOT_EVALUATED", "independent_review": "NOT_PERFORMED",
            "gate_a": "NOT_CLOSED", "status_promotion": "NONE"}


if __name__ == "__main__":
    result = verify(ROOT)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["result"] == "PASS" else 1)
