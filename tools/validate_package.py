#!/usr/bin/env python3
"""Read-only validation of the CETA build-specification package, not its future runtime.

Python standard library suffices. --with-jsonschema explicitly requires the
optional, already-installed jsonschema package. No downloads or subprocesses.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any
from urllib.parse import unquote, urlsplit

EXCLUDED_PAYLOAD = {"PACKAGE_MANIFEST.json"}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"Duplicate JSON key: {key}")
        out[key] = value
    return out


def reject_constant(value: str) -> Any:
    raise ValueError(f"Non-finite JSON constant: {value}")


def strict_json(path: Path) -> Any:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"JSON exceeds package parser bound: {path.name}")
    return json.loads(path.read_text(encoding="utf-8-sig"),
                      object_pairs_hook=reject_duplicate_keys,
                      parse_constant=reject_constant)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Invalid package-relative path: {value!r}")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts or ":" in value:
        raise ValueError(f"Unsafe package-relative path: {value!r}")
    path = root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"Path escaped package: {value!r}")
    return path


def acyclic(nodes: dict[str, list[str]]) -> bool:
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            raise ValueError(f"Dependency cycle at {node}")
        if node in visited:
            return
        if node not in nodes:
            raise ValueError(f"Missing dependency {node}")
        active.add(node)
        for dep in nodes[node]:
            visit(dep)
        active.remove(node)
        visited.add(node)

    for node in nodes:
        visit(node)
    return True


def validate(root: Path, *, skip_manifest: bool = False,
             with_jsonschema: bool = False) -> dict[str, Any]:
    root = root.resolve(strict=True)
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    def test(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"name": name, "result": "PASS" if condition else "FAIL",
                       "detail": detail})
        if not condition:
            errors.append(f"{name}: {detail}")

    def unique(rows: list[dict[str, Any]], key: str, name: str) -> set[str]:
        values = [r[key] for r in rows]
        duplicates = [v for v, n in Counter(values).items() if n > 1]
        test(name, not duplicates, ", ".join(duplicates))
        return set(values)

    def registered_paths(rows: list[dict[str, Any]], key: str, name: str,
                         directory: bool = False) -> None:
        missing: list[str] = []
        for row in rows:
            path = safe_path(root, row[key])
            ok = path.is_dir() if directory else path.is_file()
            if not ok:
                missing.append(row[key])
        test(name, not missing, "; ".join(missing))

    try:
        files = [p for p in root.rglob("*") if p.is_file()]
        test("no_symlinks", not any(p.is_symlink() for p in root.rglob("*")))
        test("no_standalone_font_or_private_key_files",
             not any(p.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2", ".key", ".pfx", ".p12", ".pem"} for p in files))
        for required in ["README.md", "START_HERE.md", "AGENTS.md", "CODEX_BOOTSTRAP_PROMPT.md",
                         "PACKAGE_SUMMARY.json", "PACKAGE_INDEX.md", "PACKAGE_TREE.txt",
                         "sources/ground_up_master_prompt.original.md"]:
            test("entry:" + required, safe_path(root, required).is_file())

        malformed = []
        for p in files:
            if p.suffix == ".json" and not p.relative_to(root).parts[0] == "sources":
                try:
                    strict_json(p)
                except (ValueError, OSError) as exc:
                    malformed.append(f"{p.relative_to(root)}: {exc}")
        test("authored_json_strict_parsing", not malformed, "; ".join(malformed))

        summary = strict_json(root / "PACKAGE_SUMMARY.json")
        reqs = strict_json(root / "requirements/requirements.json")["requirements"]
        cases = strict_json(root / "acceptance/scenarios.json")["scenarios"]
        comps = strict_json(root / "architecture/components.json")["components"]
        policies = strict_json(root / "policies/policy_registry.json")["policies"]
        work = strict_json(root / "build/work_packages.json")["packages"]
        gates = strict_json(root / "build/gates.json")["gates"]
        lifecycle = strict_json(root / "standards/lifecycle_coverage.json")["sections"]
        volumes = strict_json(root / "standards/volume_register.json")["volumes"]
        schema = strict_json(root / "contracts/schemas/records.schema.json")
        progress = strict_json(root / "build/progress.json")
        source_manifest = strict_json(root / "sources/source_manifest.json")

        rids = unique(reqs, "id", "unique_requirement_group_ids")
        bids = unique(cases, "id", "unique_acceptance_ids")
        cids = unique(comps, "id", "unique_component_ids")
        pids = unique(policies, "id", "unique_policy_ids")
        wids = unique(work, "id", "unique_work_package_ids")
        gids = unique(gates, "id", "unique_gate_ids")
        test("all_128_original_acceptance_ids", bids == {f"B{i:03d}" for i in range(1,129)})
        test("all_406_original_lifecycle_ids",
             len(lifecycle) == 406 and {r["section"] for r in lifecycle} == {f"{i:03d}" for i in range(1,407)})
        test("all_20_original_volumes", len(volumes) == 20 and {v["volume"] for v in volumes} == set(range(1,21)))
        test("original_page_total", sum(v["pages"] for v in volumes) == 4805)
        test("required_shape_contracts", len(schema["$defs"]) == 20 and len(schema["oneOf"]) == 20)

        registered_paths(reqs, "specification_path", "requirements_have_full_specifications")
        registered_paths(cases, "specification_path", "cases_have_written_fixtures")
        registered_paths(comps, "path", "component_directories_exist", directory=True)
        registered_paths(policies, "path", "policy_documents_exist")
        registered_paths(work, "path", "work_orders_exist")
        registered_paths(lifecycle, "path", "original_lifecycle_text_present")
        registered_paths(volumes, "path", "original_volume_pdfs_present")

        dangling = []
        for r in reqs:
            if r["component_owner"] not in cids | {"LEAD_INTEGRATOR"}:
                dangling.append(r["id"] + ":owner")
            if not r["acceptance_ids"] or not set(r["acceptance_ids"]) <= bids:
                dangling.append(r["id"] + ":acceptance")
        for c in cases:
            if not c["requirement_ids"] or not set(c["requirement_ids"]) <= rids:
                dangling.append(c["id"] + ":requirement")
        for p in policies:
            if not set(p["requirement_ids"]) <= rids:
                dangling.append(p["id"] + ":requirement")
        for w in work:
            if not set(w["requirement_ids"]) <= rids or not set(w["acceptance_ids"]) <= bids:
                dangling.append(w["id"] + ":trace")
            if not set(w["depends_on"]) <= wids or w["target_gate"] not in gids:
                dangling.append(w["id"] + ":dependency")
        for g in gates:
            if not set(g["required_work_packages"]) <= wids:
                dangling.append(g["id"] + ":work")
        test("all_traceability_references_resolve", not dangling, "; ".join(dangling))
        covered_req = {i for w in work for i in w["requirement_ids"]}
        covered_cases = {i for w in work for i in w["acceptance_ids"]}
        test("every_requirement_has_build_work", covered_req == rids, ", ".join(sorted(rids-covered_req)))
        test("every_case_has_build_work", covered_cases == bids, ", ".join(sorted(bids-covered_cases)))
        reciprocal = [c["id"] for c in cases if set(c["requirement_ids"]) != {r["id"] for r in reqs if c["id"] in r["acceptance_ids"]}]
        test("requirement_case_links_reciprocal", not reciprocal, ", ".join(reciprocal))
        try:
            acyclic({w["id"]: w["depends_on"] for w in work})
            test("work_package_graph_acyclic", True)
        except ValueError as exc:
            test("work_package_graph_acyclic", False, str(exc))
        try:
            acyclic({c["slug"]: c["allowed_static_dependencies"] for c in comps})
            test("core_static_dependencies_acyclic", True)
        except ValueError as exc:
            test("core_static_dependencies_acyclic", False, str(exc))

        initial_status_ok = (
            summary["runtime_implementation"] == "NOT_STARTED" and summary["runtime_validation"] == "NOT_RUN"
            and progress["runtime_implementation"] == "NOT_STARTED" and progress["test_execution"] == "NOT_RUN"
            and all(r["implementation_status"] == "NOT_STARTED" and r["verification_status"] == "NOT_RUN" and not r["evidence_refs"] for r in reqs)
            and all(c["result"] == "NOT_RUN" and c["test_code_status"] == "TO_IMPLEMENT" and not c["evidence_refs"] for c in cases)
            and all(w["implementation_status"] == "NOT_STARTED" and not w["evidence_refs"] for w in work)
            and all(p["state"] == "SPECIFIED_NOT_COMPILED" and not p["runtime_evidence"] for p in policies)
            and all(g["state"] == "NOT_EVALUATED" and not g["evidence_refs"] for g in gates)
            and all(r["applicability"] == "UNRESOLVED" and r["conformance_status"] == "NOT_EVALUATED" for r in lifecycle)
        )
        test("initial_handoff_has_no_fabricated_runtime_success", initial_status_ok,
             "This checker validates the initial delivered specification snapshot, not a later implementation registry.")
        for key, expected in [("components",len(comps)),("requirement_groups",len(reqs)),("acceptance_scenarios",len(cases)),
                              ("prewritten_policies",len(policies)),("work_packages",len(work)),("record_contracts",len(schema["$defs"]))]:
            test("summary_count:" + key, summary[key] == expected)

        master_path = root / "sources/ground_up_master_prompt.original.md"
        test("original_master_digest", digest(master_path) == source_manifest["master_prompt_sha256"])
        master = master_path.read_text(encoding="utf-8")
        missing_text = [r["id"] for r in reqs if r["requirement_text"] not in master]
        test("requirement_text_preserved_verbatim", not missing_text, ", ".join(missing_text))
        missing_cases = [c["id"] for c in cases if c["normative_scenario"] not in master]
        test("original_acceptance_text_preserved_verbatim", not missing_cases, ", ".join(missing_cases))
        source_mismatch = []
        for row in lifecycle + volumes:
            p = safe_path(root, row["path"])
            if p.stat().st_size != row["bytes"] or digest(p) != row["sha256"]:
                source_mismatch.append(row["path"])
        test("original_lifecycle_and_volume_digests", not source_mismatch, "; ".join(source_mismatch))
        witnesses = strict_json(root / "sources/codex/text_witnesses.json")["witnesses"]
        bad_witnesses = [r["path"] for r in witnesses if digest(safe_path(root, r["path"])) != r["sha256"]]
        test("original_text_witness_digests", not bad_witnesses, "; ".join(bad_witnesses))
        test("witness_count", len(witnesses) == summary["original_text_witnesses"])

        broken_links = []
        for p in files:
            if p.suffix.lower() != ".md" or p.relative_to(root).parts[0] == "sources":
                continue
            for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)", p.read_text(encoding="utf-8")):
                target = match[1].strip().strip("<>")
                if not target or target.startswith("#") or urlsplit(target).scheme:
                    continue
                target = unquote(target.split("#",1)[0])
                if not (p.parent / target).resolve().is_relative_to(root) or not (p.parent / target).exists():
                    broken_links.append(str(p.relative_to(root)) + " -> " + target)
        test("authored_markdown_file_links", not broken_links, "; ".join(broken_links))

        test("schema_definitions_strict_objects", all(s.get("additionalProperties") is False and s.get("type") == "object"
             and set(s.get("required",[])) == set(s.get("properties",{})) for s in schema["$defs"].values()))
        raw_dup = root / "contracts/examples/duplicate_keys.wire.txt"
        try:
            strict_json(raw_dup)
            test("duplicate_key_wire_rejected", False)
        except ValueError:
            test("duplicate_key_wire_rejected", True)

        if with_jsonschema:
            try:
                from jsonschema import Draft202012Validator, FormatChecker
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema, format_checker=FormatChecker())
                for p in sorted((root / "contracts/examples").glob("*.json")):
                    example = strict_json(p)
                    valid = not list(validator.iter_errors(example["instance"]))
                    test("full_json_schema_example:" + p.name,
                         valid == (example["expected_shape"] == "ACCEPT") and example["never_authority"] is True)
                test("full_json_schema_meta_validation", True)
            except ImportError:
                test("optional_jsonschema_dependency", False, "Install through your approved environment workflow, or omit this explicitly optional check.")
            except Exception as exc:
                test("full_json_schema_meta_validation", False, f"{type(exc).__name__}: {exc}")

        if not skip_manifest:
            mf = strict_json(root / "PACKAGE_MANIFEST.json")
            entries = mf["files"]
            names = unique(entries, "path", "manifest_paths_unique")
            actual = {p.relative_to(root).as_posix() for p in files} - EXCLUDED_PAYLOAD
            test("manifest_covers_exact_payload", names == actual,
                 "Missing: " + ", ".join(sorted(actual-names)) + "; unexpected: " + ", ".join(sorted(names-actual)))
            bad_hashes = []
            for row in entries:
                p = safe_path(root, row["path"])
                if not p.is_file() or p.stat().st_size != row["bytes"] or digest(p) != row["sha256"]:
                    bad_hashes.append(row["path"])
            test("manifest_payload_hashes", not bad_hashes, "; ".join(bad_hashes))
            test("manifest_self_exclusion_explicit", set(mf["excluded_paths"]) == EXCLUDED_PAYLOAD)
    except (OSError, ValueError, KeyError, TypeError, IndexError, RecursionError) as exc:
        test("package_read_or_structure", False, f"{type(exc).__name__}: {exc}")

    return {"tool":"CETA build package validator","tool_version":"1.0",
            "observed_at_utc":datetime.now(timezone.utc).isoformat(),
            "validation_scope":"PACKAGE_DOCUMENTS_AND_REFERENCES_ONLY",
            "result":"PASS" if not errors else "FAIL",
            "manifest_checked":not skip_manifest,"full_json_schema_requested":with_jsonschema,
            "runtime_implemented":False,"runtime_tests_executed":False,
            "runtime_qualification":"NOT_RUN","checks":checks,"errors":errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-manifest", action="store_true", help="Authoring structure checks only; no final integrity claim.")
    parser.add_argument("--with-jsonschema", action="store_true", help="Require already-installed optional jsonschema for full example checks.")
    parser.add_argument("--report", type=Path, help="New result file outside the immutable handoff root.")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if args.report and args.report.resolve().is_relative_to(root):
            parser.error("Report must be outside the package; validation does not modify its payload.")
        result = validate(root, skip_manifest=args.skip_manifest, with_jsonschema=args.with_jsonschema)
        text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        sys.stdout.write(text)
        return 0 if result["result"] == "PASS" else 1
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"Package validation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
