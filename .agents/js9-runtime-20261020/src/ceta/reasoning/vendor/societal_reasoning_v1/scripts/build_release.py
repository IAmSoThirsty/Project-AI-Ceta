"""Build deterministic, integrity-listed source release ZIP.

Usage: python scripts/build_release.py [output-directory]
The script first runs all tests; failures prevent an archive from being released.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1"
ARCHIVE_NAME = "Societal-Reasoning-Core-v1.zip"
ZIP_TIMESTAMP = (2026, 10, 18, 0, 0, 0)
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist", ".venv", ".git"}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not any(p in EXCLUDED_DIRS or p.endswith(".egg-info") for p in path.relative_to(ROOT).parts)
        and path.name not in {"manifest.json", "SHA256SUMS"}
        and path.suffix not in {".pyc", ".pyo"}
    )


def checksums(files: list[Path]) -> str:
    return "".join(f"{digest(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n" for path in files)


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent
    destination.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    from requirement_register import create_register
    register = create_register()
    expected_register = json.dumps(register, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    actual_register = (ROOT / "docs" / "TRACEABILITY.json").read_text(encoding="utf-8")
    if actual_register != expected_register:
        raise RuntimeError("Refusing to package stale or forged 120-requirement progress register")
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        print(result.stdout + "\n" + result.stderr, file=sys.stderr)
        raise SystemExit("Refusing to package failing tests")
    observed = re.search(r"Ran (\d+) tests?", result.stderr)
    if not observed:
        raise RuntimeError("Failed to independently detect test count")
    test_count = int(observed.group(1))

    sys.path.insert(0, str(ROOT / "src"))
    from societal_reasoning.engine import SocietalReasoner
    from societal_reasoning.evaluate import evaluate_file
    from societal_reasoning.semantics import LexicalRegistry
    # Gate the release against authoritative local Markdown, not only precompiled JSON.
    from compile_inventory import compile_corpus
    source_report = compile_corpus(write=False)
    if source_report["included"] != 2000:
        raise RuntimeError("Refusing to package incomplete inventory")
    reasoner = SocietalReasoner.starter()
    report = reasoner.graph.audit()
    if report["concept_count"] != 2000 or report["original_inventory_ids_not_present"] != 0:
        raise RuntimeError("Refusing to package graph without all 2,000 original IDs")
    if report["status_counts"].get("source_transcribed", 0) != 2000:
        raise RuntimeError("Refusing to package untranscribed catalog entries")
    from societal_reasoning import __version__
    if __version__ != VERSION:
        raise RuntimeError("Internal version must equal owner-fixed Version 1")
    from societal_reasoning.models import Scenario
    source_check = reasoner.assess_text("I might attend.")
    guarded = reasoner.review_draft(source_check, 'You said "I will attend."')
    if guarded["status"] != "hold":
        raise RuntimeError("Statement attribution guard did not hold a misquotation")
    if source_check["version"] != VERSION:
        raise RuntimeError("Text assessment changed owner-fixed Version 1")
    # Relevance must use the full corpus without asserting people-labels or
    # treating model proposals as observations. No unsupported inference claims.
    lookup = reasoner.assess_text("Explain humor.", turn_id="r1")
    if 74 not in {row["concept_id"] for row in lookup["knowledge_considerations"]["topics"]}:
        raise RuntimeError("Canonical inventory not consulted for grounded topic retrieval")
    if reasoner.assess_text("I lost my job.")["knowledge_considerations"]["topics"]:
        raise RuntimeError("Unrelated loss report must not be forcibly labeled")
    from societal_reasoning.corrections import CorrectionLedger
    from societal_reasoning.input_boundary import Utterance
    ledger = CorrectionLedger("release-local")
    old = Utterance.capture("I might attend.", turn_id="old")
    new = Utterance.capture("Correction: I will not attend.", turn_id="new")
    ledger.add_turn(old)
    ledger.add_turn(new)
    ledger.correct("old", "new", start=12, end=len(new.text))
    old_check = reasoner.assess_text(old.text, turn_id="old", session_id=ledger.session_id)
    old_review = reasoner.review_draft(old_check, 'Your current position is "I might attend."', correction_ledger=ledger)
    if old_review["status"] != "hold" or not any(
        issue["code"] == "SUPERSEDED_USER_QUOTE_AS_CURRENT" for issue in old_review["issues"]
    ):
        raise RuntimeError("Explicit correction did not hold obsolete current-user attribution")
    ledger.purge()
    from societal_reasoning.deliberation import DeliberationCase
    public_case = DeliberationCase.from_dict(json.loads(
        (ROOT / "examples" / "deliberation_public.json").read_text(encoding="utf-8")))
    private_case = DeliberationCase.from_dict(json.loads(
        (ROOT / "examples" / "deliberation_private.json").read_text(encoding="utf-8")))
    public_reading = reasoner.deliberate(public_case)
    if public_reading["version"] != VERSION or public_reading["schema"] != "deliberation.v1":
        raise RuntimeError("New deliberation facade broke Version 1 contract")
    if public_reading["candidates"][3]["status"] != "no_active_supporting_warrants":
        raise RuntimeError("An unsourced hidden-motive hypothesis was improperly promoted")
    if public_reading["candidates"][3]["excluded_warrants"][0]["evidence_origin"] != "interpretation":
        raise RuntimeError("A previous interpretation became presumed observational evidence")
    variation = reasoner.compare_deliberations(public_case, private_case)
    expected_changes = {"group-directed-reading", "private-joking-reading"}
    if {item["id"] for item in variation["candidate_changes"]} != expected_changes:
        raise RuntimeError("Context-specific warrant changes failed deterministic regression")
    if variation["evidence_changes"]:
        raise RuntimeError("Context-only fixture unexpectedly modified evidence")
    if any(item["semantic_entailment_checked"] for item in public_reading["candidates"]):
        raise RuntimeError("Unverified warrants cannot masquerade as semantic entailment proof")
    # Bounded semantic checks must prevent a genuine quotation or one opposed
    # record from acquiring authority over a person's real motives or factual state.
    fixture = json.loads((ROOT / "examples" / "bounded_semantic_premises.json").read_text(encoding="utf-8"))
    ground = reasoner.deliberate(DeliberationCase.from_dict(fixture))
    if len(ground["literal_source_oppositions"]) != 1:
        raise RuntimeError("Opposed literal source reports were not preserved")
    candidates = {row["id"]: row for row in ground["candidates"]}
    if any(candidates[key]["bounded_premises_verified"] != 1 for key in
           ("reported-nonattendance", "reported-attendance", "caption-wording")):
        raise RuntimeError("Digest-bound literal premise proof not exercised")
    if candidates["unsupported-motive"]["supporting_warrants"]:
        raise RuntimeError("Speculative private motive acquired observation status")
    if any(row["semantic_entailment_checked"] for row in ground["candidates"]):
        raise RuntimeError("Literal source presence cannot certify social entailment")
    stale = json.loads(json.dumps(fixture))
    stale["scenario"]["evidence"][0]["statement"] += " edited"
    stale_report = reasoner.deliberate(DeliberationCase.from_dict(stale))
    stale_status = stale_report["candidates"][0]["excluded_warrants"][0]["premise_check"]["status"]
    if stale_status != "stale_source_binding":
        raise RuntimeError("Stale source record was allowed as a validated premise")
    # Inspect both source wording and the proposed reading. These test only
    # bounded source reporting, never a person's character or true motives.
    mixed_case = DeliberationCase.from_dict(json.loads((ROOT / "examples" /
        "reading_source_alignment.json").read_text(encoding="utf-8")))
    mixed = reasoner.deliberate(mixed_case)
    aligned = {row["id"]: row["reading_source_alignment"] for row in mixed["candidates"]}
    if (aligned["categorical-wording"]["status"] != "bounded_textual_generalization_matched" or
            aligned["work-wording"]["status"] != "bounded_work_product_evaluation_matched" or
            aligned["unfounded-private-intent"]["status"] != "third_party_private_state_not_independently_established"):
        raise RuntimeError("Source-vs-reading alignment failed on mixed human context")
    if (len(mixed["source_language_signals"]) != 2 or
            any(s["personal_attribute_proven"] or s["independently_verified_truth"]
                for s in mixed["source_language_signals"]) or
            any(c["reading_source_alignment"]["social_entailment_verified"]
                for c in mixed["candidates"])):
        raise RuntimeError("Text patterns were promoted to unsupported claims about people")
    opposed_case = DeliberationCase.from_dict(json.loads((ROOT / "examples" /
        "literal_reading_opposed.json").read_text(encoding="utf-8")))
    opposed_report = reasoner.deliberate(opposed_case)
    if (opposed_report["candidates"][0]["reading_source_alignment"]["status"] !=
            "literal_reading_opposed_by_source_reports" or
            opposed_report["response_guidance"]["mode"] != "withhold_unsupported_conclusion"):
        raise RuntimeError("Opposed literal reading was promoted by a proposed rationale")
    if len(mixed["candidates"]) != 3 or mixed["version"] != VERSION:
        raise RuntimeError("Source-reading regression changed owner-fixed Version 1")
    evaluated = evaluate_file(reasoner, ROOT / "evaluations" / "behavior-contract.v1.json")
    if evaluated["failed"]:
        raise RuntimeError(f"Refusing to package {evaluated['failed']} failed behavioral contract(s)")
    registry = LexicalRegistry.starter()
    ambiguous_example = json.loads((ROOT / "examples" / "semantic_ambiguity.json").read_text())
    from societal_reasoning.models import Scenario
    if reasoner.analyze(Scenario.from_dict(ambiguous_example))["status"] != "clarification_required":
        raise RuntimeError("Material dictionary ambiguity failed closed gate")
    verification_report = {
        "version": VERSION,
        "scope": "offline_source_prototype_validation_not_independent_social_accuracy",
        "tests": {"passed": test_count, "failed": 0, "method": "PYTHONPATH=src python -m unittest discover -s tests -q"},
        "behavior_contract": {"passed": evaluated["passed"], "failed": evaluated["failed"],
                              "type": evaluated["suite_type"],
                              "case_ids": [r["id"] for r in evaluated["results"]]},
        "dictionary": {"source": "Merriam-Webster", "reviewed_linked_terms": len(registry.terms),
                       "dictionary_text_redistributed": False},
        "inventory": {"original_expected": 2000, "present": report["concept_count"],
                      "source_transcribed_unverified": report["status_counts"].get("source_transcribed", 0),
                      "seed_summaries": report["status_counts"].get("seed_summary_pending_transcription", 0),
                      "independently_verified": report["independently_verified_count"],
                      "absent": report["original_inventory_ids_not_present"],
                      "source_compilation": source_report},
        "reading_source_alignment_regression": {
            "explicit_universal_text_pattern": aligned["categorical-wording"]["status"],
            "specific_work_text_pattern": aligned["work-wording"]["status"],
            "private_motive_unestablished": aligned["unfounded-private-intent"]["status"],
            "opposed_bounded_literal_reading_held": True,
            "group_or_person_characterization_certified": False,
            "source_language_patterns_detected_in_mixed_case": len(mixed["source_language_signals"]),
            "test_author": "implementer_not_independent",
        },
        "deliberation_regression": {
            "public_private_variant_candidates_changed": sorted(expected_changes),
            "evidence_changes_in_context_only_variant": 0,
            "unsourced_private_motive_proposal_admitted_as_fact": False,
            "source_to_warrant_semantic_validation": "bounded_literal_premises_only_social_inference_unverified",
            "literal_source_oppositions_detected_in_fixture": len(ground["literal_source_oppositions"]),
            "stale_source_binding_rejected": stale_status == "stale_source_binding",
            "test_author": "implementer_not_independent",
        },
        "known_gaps": ["Human line-by-line comparison of local source text against chat export not completed",
                       "Independent assessment of societal reasoning not performed",
                       "Free-text returns lexical corpus topics and does not reliably infer social meanings or causal mechanisms",
                       "Alternative interpretations and pro/con rationales are supplied by the caller; bounded reading checks do not establish broad social semantic entailment",
                       "Draft review is a bounded surface scanner and cannot establish full semantic fidelity",
                       "Only optional explicit in-memory correction supersession; no automatic conversation-wide semantic revision",
                       "Full ratified Codex I-XX not reconciled; XXI remains draft",
                       "Public GitHub release and licensing not authorized",
                       "CETA/Project-AI integration deferred",
                       "Offline pip installation not verified (build backend unavailable in test environment); direct launcher verified"],
        "development": {
            "purpose": "context-sensitive interpretation without unsupported person attributions",
            "requirements": register["planned_requirements"],
            "requirement_status_counts": register["counts"],
            "statement_source_capture": "bounded_local_tests_pass",
            "draft_review": "heuristic_advisory_surface_checker_not_complete_entailment",
            "knowledge_relevance": "source_attributed_lexical_topics_not_validated_social_inference",
            "session_corrections": "opt_in_explicit_supersession_not_automatic_semantics",
            "argument_comparison": "bounded_source_linked_conditional_warrants_with_literal_premise_checks_not_social_entailment",
            "reading_source_alignment": "source_bound_literal_or_narrow_text_pattern_not_personal_or_factual_verdict",
            "generalized_social_reasoning": "not_demonstrated",
            "host_enforcement": "not_tested",
        },
        "status": "VERSION_1_DEVELOPMENT_INCREMENT_NOT_COMPLETE"
    }
    (ROOT / "verification-report.json").write_text(
        json.dumps(verification_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    demo_data = json.loads((ROOT / "src" / "societal_reasoning" / "resources" / "demo_social.json").read_text())
    from societal_reasoning.models import Scenario
    if reasoner.analyze(Scenario.from_dict(demo_data))["primary"]["rule_id"] != "public_group_ridicule":
        raise RuntimeError("Core smoke test failed")

    content = source_files()
    file_entries = [
        {"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p.read_bytes()), "bytes": p.stat().st_size}
        for p in content
    ]
    manifest = {
        "name": "Societal Reasoning Core",
        "version": VERSION,
        "release_type": "offline_full_inventory_source_development_increment",
        "archive_name": ARCHIVE_NAME,
        "source_date": "2026-10-18",
        "python_requires": ">=3.11",
        "runtime_dependencies": [],
        "inventory": {
            "original_volume_I_and_II_target": 2000,
            "total_included": report["concept_count"],
            "seed_concept_summaries": report["status_counts"].get("seed_summary_pending_transcription", 0),
            "source_transcribed_not_independently_verified": report["status_counts"].get("source_transcribed", 0),
            "missing_original_ids": report["original_inventory_ids_not_present"],
            "independently_verified_entries": report["independently_verified_count"],
            "proposed_relationships": report["relationship_count"],
            "declarative_rules": len(reasoner.rules),
        },
        "verification": {
            "unit_tests_passed": test_count,
            "developer_regression_cases_passed": evaluated["passed"],
            "dictionary_terms_source_linked": len(registry.terms),
            "method": "python -m unittest discover -s tests -q",
            "smoke_example": "public_group_ridicule",
            "note": "Tests validate implemented behavior, not real-world social reasoning accuracy.",
        },
        "requirement_progress": {
            "register": "docs/TRACEABILITY.json",
            "total": register["planned_requirements"],
            "counts": register["counts"],
            "status": "work_in_progress_not_completion",
        },
        "statement_review": "bounded_advisory_surface_checks_plus_opt_in_exact_superseded_quote_guard",
        "knowledge_retrieval": "lexical_source_attributed_candidates_not_people_classification",
        "session_corrections": "explicit_in_memory_only_not_automatic_revision",
        "alternative_readings": "source_linked_contextual_argument_review_not_independently_validated_inference",
        "bounded_literal_premises": "exact_span_or_strict_literal_assertion_source_only_not_social_factual_verdict",
        "bounded_reading_alignment": "source_literal_conflict_and_two_explicit_text_patterns_not_social_entailment",
        "standards_evidence_state": "partial_trace_to_codex_XXI_draft_not_ratified_no_full_conformance_claim",
        "publication": "local_delivery_only_not_published",
        "license_status": "undecided_not_open_source_licensed",
        "integration_status": "standalone_only_future_host_integration_deferred",
        "files": file_entries,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = ROOT / "manifest.json"
    with (ROOT / "SHA256SUMS").open("w", encoding="utf-8", newline="\n") as target:
        target.write(checksums(content + [manifest_path]))
    archive = destination / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(source_files() + [manifest_path, ROOT / "SHA256SUMS"]):
            archive_path = f"{ROOT.name}/{file.relative_to(ROOT).as_posix()}"
            info = zipfile.ZipInfo(archive_path, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 << 16)
            z.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    archive_hash = digest(archive.read_bytes())
    (destination / f"{ARCHIVE_NAME}.sha256").write_text(
        f"{archive_hash}  {ARCHIVE_NAME}\n", encoding="utf-8"
    )
    print(json.dumps({
        "archive": str(archive), "sha256": archive_hash,
        "size_bytes": archive.stat().st_size,
        "files_in_archive": len(content) + 2,
        "concepts": report["concept_count"], "relationships": report["relationship_count"],
        "dictionary_terms": len(registry.terms), "behavior_contracts_passed": evaluated["passed"],
        "source_transcriptions": report["status_counts"].get("source_transcribed", 0),
        "rules": len(reasoner.rules), "tests_passed": test_count,
    }, indent=2))


if __name__ == "__main__":
    main()
