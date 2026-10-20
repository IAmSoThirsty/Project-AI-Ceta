"""Actual pinned V1/F pipeline and adapter failure-boundary regressions.

No model service, canonical CETA database or host profile is used. Mutable
vendor fixtures are disposable copies under this repository's T: fixture root.
"""
from __future__ import annotations

import hashlib
import importlib.resources
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from ceta.reasoning import (
    AssessmentOutcome as O, ReasoningAssessment, ShadowLevel,
    ShadowModeController, SocietalReasoningAdapter, SyntheticProposer,
)
from ceta.reasoning import source_loader


ROOT = Path(__file__).resolve().parents[3]


class StructuredProvider:
    def __init__(self, kind: str, text: str | None = None):
        self.kind, self.text = kind, text

    def generate_proposal(self, source_id, source_text, *, contextual_references=None):
        record = {"kind": self.kind, "text": self.text or source_text}
        if self.kind in {"quote", "paraphrase"}:
            record.update(source_id=source_id, span=[0, len(source_text)])
        return json.dumps(record)


class ActualPipelineTests(unittest.TestCase):
    def setUp(self):
        self.adapter = SocietalReasoningAdapter()
        self.adapter.initialize()
        self.addCleanup(self.adapter.close)

    def assess(self, text, proposer):
        return self.adapter.assess(speaker_id="speaker-1", text=text, proposer=proposer)

    def test_real_quote_preserves_exact_original(self):
        result = self.assess("I understand.", StructuredProvider("quote"))
        self.assertEqual((result.gate_decision, result.gate_outcome), ("QUOTED_VERBATIM", O.ADVISORY_PASS))
        self.assertEqual(result.runtime_review_status, "ADVISORY_PASS")
        row = self.adapter._core.db.execute("SELECT exact_utf8 FROM sources_v2").fetchone()
        self.assertEqual(bytes(row[0]).decode("utf-8"), "I understand.")
        self.assertEqual(result.source_text_sha256, hashlib.sha256(b"I understand.").hexdigest())
        self.assertEqual(result.gate_response, "")
        self.assertFalse(result.established_fact)

    def test_registered_actual_arithmetic_supports_only_true_equation(self):
        good = self.assess("7 * 8 = 56", StructuredProvider("fact"))
        bad = self.assess("7 * 8 = 57", StructuredProvider("fact"))
        self.assertEqual((good.gate_decision, good.gate_outcome, good.established_fact),
                         ("SUPPORTED_BY_CHECK", O.ADVISORY_PASS, True))
        self.assertEqual((bad.gate_decision, bad.gate_outcome, bad.established_fact),
                         ("REFUTED_BY_CHECK", O.REVIEW_FAILURE, False))
        self.assertTrue(self.adapter._core.integrity_report()["ok"])

    def test_unsupported_fact_and_hypothesis_are_held(self):
        fact = self.assess("This neighborhood is safe", StructuredProvider("fact"))
        hypothesis = self.assess("Hello.", StructuredProvider("hypothesis", "An unverified idea"))
        self.assertEqual((fact.gate_decision, fact.gate_outcome), ("UNVERIFIED", O.ADVISORY_HOLD))
        self.assertEqual((hypothesis.gate_decision, hypothesis.gate_outcome),
                         ("HYPOTHESIS_HELD_FOR_REVIEW", O.ADVISORY_HOLD))
        self.assertFalse(fact.established_fact or hypothesis.established_fact)

    def test_real_meaning_review_is_required_for_paraphrase(self):
        result = self.assess("I asked you to understand.", StructuredProvider("paraphrase", "You demanded obedience"))
        self.assertIn(result.gate_decision, {"NEEDS_MEANING_REVIEW", "VERSION1_REVIEW_HOLD"})
        self.assertEqual(result.gate_outcome, O.ADVISORY_HOLD)
        self.assertFalse(result.established_fact)

    def test_actual_runtime_review_can_withhold_a_quote(self):
        result = self.assess("I might attend, but I have not promised.", StructuredProvider("quote"))
        self.assertEqual((result.gate_decision, result.runtime_review_status),
                         ("VERSION1_REVIEW_HOLD", "REVIEW_HOLD"))
        self.assertEqual(result.gate_outcome, O.ADVISORY_HOLD)

    def test_no_implicit_provider_or_synthetic_fallback(self):
        with self.assertRaises(ValueError):
            self.adapter.assess(speaker_id="speaker-1", text="I understand.")
        self.assertEqual(self.adapter._core.db.execute("SELECT COUNT(*) FROM sources_v2").fetchone()[0], 0)
        rejected = self.assess("I understand.", SyntheticProposer())
        self.assertEqual((rejected.gate_decision, rejected.gate_outcome),
                         ("MODEL_PROPOSAL_REJECTED", O.REVIEW_FAILURE))

    def test_provider_failure_is_not_mislabeled_as_source_unavailable(self):
        failure = RuntimeError("provider unavailable")
        class Broken:
            def generate_proposal(self, *args, **kwargs):
                raise failure
        result = self.assess("I understand.", Broken())
        self.assertEqual(result.context_outcome, O.NOT_EVALUATED)
        self.assertEqual((result.context_status, result.gate_decision), ("PIPELINE_ERROR", "PIPELINE_ERROR"))
        self.assertIs(self.adapter.last_error, failure)
        self.assertEqual(result.gate_response, "")
        self.assertFalse(result.established_fact)
        self.assess("I understand.", StructuredProvider("quote"))
        self.assertIsNone(self.adapter.last_error)

    def test_malformed_and_oversized_provider_results_fail_closed(self):
        class Raw:
            def __init__(self, raw): self.raw = raw
            def generate_proposal(self, *args, **kwargs): return self.raw
        for raw, expected in [("{bad", "MODEL_PROPOSAL_REJECTED"), ("x" * 32769, "PIPELINE_ERROR"),
                              (None, "PIPELINE_ERROR"), ('{"kind":"fact","kind":"quote","text":"x"}', "MODEL_PROPOSAL_REJECTED")]:
            with self.subTest(expected=expected, raw_type=type(raw).__name__):
                result = self.assess("I understand.", Raw(raw))
                self.assertEqual(result.gate_decision, expected)
                self.assertEqual(result.gate_outcome, O.REVIEW_FAILURE)
                self.assertFalse(result.established_fact)

    def test_context_candidates_are_bounded_and_explicitly_unverified(self):
        candidates = self.adapter.context_only("context collapse conversation", limit=2)
        self.assertGreater(len(candidates), 0)
        self.assertLessEqual(len(candidates), 2)
        self.assertTrue(all(x["authority"] == "UNVERIFIED_CONTEXT_ONLY" for x in candidates))
        for limit in (True, 0, 11, "4"):
            with self.assertRaises(ValueError): self.adapter.context_only("context", limit=limit)

    def test_input_bounds_reject_before_source_preservation(self):
        for speaker, text in [(1, "hello"), ("s", ""), ("s", "x\0y"), ("s", "x" * 65537), ("s" * 129, "hello")]:
            with self.assertRaises((TypeError, ValueError)):
                self.adapter.assess(speaker_id=speaker, text=text, proposer=StructuredProvider("quote"))
        self.assertEqual(self.adapter._core.db.execute("SELECT COUNT(*) FROM sources_v2").fetchone()[0], 0)

    def test_foreign_thread_cannot_assess_or_close_live_session(self):
        outcomes = []
        def attempt():
            for action in (lambda: self.adapter.context_only("hello"), self.adapter.close):
                try: action()
                except Exception as exc: outcomes.append(type(exc))
        worker = threading.Thread(target=attempt)
        worker.start(); worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(outcomes, [RuntimeError, RuntimeError])
        self.assertTrue(self.adapter.initialized)
        self.assertFalse(self.adapter.closed)

    def test_provider_cannot_reenter_or_retire_current_session(self):
        observed = []
        adapter = self.adapter
        class Reentrant(StructuredProvider):
            def generate_proposal(self, *args, **kwargs):
                for action in (lambda: adapter.context_only("hello"), adapter.close):
                    try: action()
                    except RuntimeError: observed.append("rejected")
                return super().generate_proposal(*args, **kwargs)
        result = self.assess("I understand.", Reentrant("quote"))
        self.assertEqual(observed, ["rejected", "rejected"])
        self.assertEqual(result.gate_decision, "QUOTED_VERBATIM")


    def test_provider_descriptor_is_guarded_and_captured_once(self):
        adapter, observed = self.adapter, []
        class Descriptor:
            lookups = 0
            @property
            def generate_proposal(self):
                self.lookups += 1
                try: adapter.close()
                except RuntimeError: observed.append("retirement rejected")
                return StructuredProvider("quote").generate_proposal
        provider = Descriptor()
        result = self.assess("I understand.", provider)
        self.assertEqual(provider.lookups, 1)
        self.assertEqual(observed, ["retirement rejected"])
        self.assertTrue(adapter.initialized)
        self.assertFalse(adapter.closed)
        self.assertEqual(result.gate_decision, "QUOTED_VERBATIM")

    def test_provider_descriptor_admission_failure_preserves_open_session(self):
        adapter = self.adapter
        class Descriptor:
            @property
            def generate_proposal(self):
                adapter.close()
        with self.assertRaises(RuntimeError): self.assess("I understand.", Descriptor())
        self.assertFalse(adapter._busy)
        self.assertTrue(adapter.initialized)
        self.assertFalse(adapter.closed)
        self.assertEqual(adapter._core.db.execute("SELECT COUNT(*) FROM sources_v2").fetchone()[0], 0)
        self.assertEqual(self.assess("I understand.", StructuredProvider("quote")).gate_decision,
                         "QUOTED_VERBATIM")


class SessionLifecycleTests(unittest.TestCase):
    def test_multiple_sessions_have_distinct_ledgers_and_close_truthfully(self):
        first, second = SocietalReasoningAdapter(), SocietalReasoningAdapter(shadow_mode=False)
        try:
            first.initialize(); second.initialize()
            self.assertIsNot(first._core, second._core)
            first.assess(speaker_id="s", text="I understand.", proposer=StructuredProvider("quote"))
            self.assertEqual(second._core.db.execute("SELECT COUNT(*) FROM sources_v2").fetchone()[0], 0)
            result = second.assess(speaker_id="s", text="7 * 8 = 56", proposer=StructuredProvider("fact"))
            self.assertIn("local:arithmetic:v1", result.gate_response)
            self.assertTrue(result.established_fact)
            connection = first._core.db
            first.close()
            self.assertFalse(first.initialized)
            self.assertTrue(first.closed)
            with self.assertRaises(sqlite3.ProgrammingError): connection.execute("SELECT 1")
            with self.assertRaises(RuntimeError): first.initialize()
            with self.assertRaises(RuntimeError): first.context_only("hello")
            first.close()
            self.assertTrue(second.initialized)
        finally:
            first.close(); second.close()

    def test_failed_close_retains_core_and_blocks_further_assessment(self):
        adapter = SocietalReasoningAdapter()
        adapter.initialize()
        core = adapter._core
        try:
            with patch.object(core, "close", side_effect=RuntimeError("retirement failed")):
                with self.assertRaises(RuntimeError): adapter.close()
            self.assertIs(adapter._core, core)
            self.assertTrue(adapter.closed)
            self.assertFalse(adapter.initialized)
            with self.assertRaises(RuntimeError): adapter.context_only("hello")
        finally:
            adapter.close()
        self.assertIsNone(adapter._core)

    def test_failed_partial_initialization_preserves_primary_and_cleanup_custody(self):
        source_loader.load_components()
        import truth_accountability as truth
        primary, secondary = RuntimeError("construction failed"), RuntimeError("close failed")
        adapter = SocietalReasoningAdapter()
        try:
            with patch.object(truth, "SocietalGatedPipeline", side_effect=primary), \
                 patch.object(truth.GovernedTruthCore, "close", side_effect=secondary):
                with self.assertRaises(RuntimeError) as caught: adapter.initialize()
            self.assertIs(caught.exception, primary)
            self.assertIs(primary.reasoning_cleanup_error, secondary)
            self.assertIsNotNone(adapter._core)
            with self.assertRaises(RuntimeError): adapter.initialize()
        finally:
            adapter.close()

    def test_hostile_primary_dict_and_string_do_not_replace_initialization_failure(self):
        source_loader.load_components()
        import truth_accountability as truth
        class Hostile(RuntimeError):
            @property
            def __dict__(self): raise RuntimeError("hostile exception dictionary")
            def __str__(self): raise RuntimeError("hostile exception text")
        primary, secondary = Hostile(), RuntimeError("close failure")
        adapter = SocietalReasoningAdapter()
        try:
            with patch.object(truth, "SocietalGatedPipeline", side_effect=primary), \
                 patch.object(truth.GovernedTruthCore, "close", side_effect=secondary):
                with self.assertRaises(Hostile) as caught: adapter.initialize()
            self.assertIs(caught.exception, primary)
            raw = BaseException.__dict__["__dict__"].__get__(primary)
            self.assertIs(raw["reasoning_cleanup_error"], secondary)
            self.assertIsNotNone(adapter._core)
        finally:
            adapter.close()

    def test_failure_inside_core_constructor_retires_its_allocated_database(self):
        source_loader.load_components()
        import truth_accountability as truth
        original = truth.GovernedTruthCore.__init__
        created = []
        primary = RuntimeError("failure inside constructor")
        def failing(core, *args, **kwargs):
            original(core, *args, **kwargs)
            created.append(core.db)
            raise primary
        adapter = SocietalReasoningAdapter()
        with patch.object(truth.GovernedTruthCore, "__init__", failing):
            with self.assertRaises(RuntimeError) as caught: adapter.initialize()
        self.assertIs(caught.exception, primary)
        self.assertIsNone(adapter._core)
        self.assertFalse(adapter.initialized)
        self.assertEqual(len(created), 1)
        with self.assertRaises(sqlite3.ProgrammingError): created[0].execute("SELECT 1")
        adapter.close()

    def test_shadow_flag_requires_actual_boolean(self):
        for flag in (0, 1, "no", None):
            with self.assertRaises(TypeError): SocietalReasoningAdapter(shadow_mode=flag)


class ProvenanceAndEncodingTests(unittest.TestCase):
    def child(self, program):
        prefix = "import sys;sys.path.insert(0," + repr(str(ROOT / "src")) + ");"
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", prefix + program],
                                   cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_actual_resources_and_repeat_verification_do_not_change_sys_path(self):
        before = tuple(sys.path)
        one = source_loader.load_components()
        second = source_loader.load_components()
        self.assertIs(one, second)
        self.assertEqual(before, tuple(sys.path))
        self.assertEqual(one.v1_concept_count, 2000)
        self.assertEqual(one.paths_added, ())
        data = importlib.resources.files("societal_reasoning").joinpath("resources/concepts.full.jsonl").read_bytes()
        self.assertEqual(len(data.splitlines()), 2000)
        self.assertGreater(len(one.verified_files), 20)
        self.assertEqual(len(one.tree_sha256), 64)

    def test_wrong_origin_preloaded_version_one_is_rejected(self):
        self.child("""
import types
from ceta.reasoning import source_loader as loader
fake=types.ModuleType('societal_reasoning');fake.__version__='1';fake.__file__='unverified.py'
sys.modules['societal_reasoning']=fake
try: loader.load_components()
except RuntimeError as exc: assert 'Foreign preloaded' in str(exc)
else: raise AssertionError('foreign module accepted')
assert sys.modules['societal_reasoning'] is fake
assert not loader.is_loaded()
""")

    def test_removed_verified_module_fails_recheck(self):
        self.child("""
from ceta.reasoning import source_loader as loader
loader.load_components()
del sys.modules['societal_reasoning']
try: loader.load_components()
except RuntimeError as exc: assert 'removed' in str(exc)
else: raise AssertionError('removed module accepted')
""")

    def test_modified_extracted_code_resource_config_and_extra_module_rejected(self):
        fixture_root = ROOT / ".agents/runtime/reasoning-core-repair-20261020/test-fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        mutations = (
            ("societal_reasoning_v1/src/societal_reasoning/__init__.py", b"# altered\n"),
            ("societal_reasoning_v1/src/societal_reasoning/resources/concepts.full.jsonl", b"{}\n"),
            ("truth_accountability_f/configs/version1_canonical_mapping.json", b"{}\n"),
            ("truth_accountability_f/truth_accountability/extra.py", b"executed=False\n"),
        )
        for relative, content in mutations:
            with self.subTest(path=relative), tempfile.TemporaryDirectory(dir=fixture_root) as directory:
                vendor = Path(directory) / "vendor"
                shutil.copytree(source_loader._VENDOR_ROOT, vendor)
                (vendor / relative).write_bytes(content)
                with patch.multiple(source_loader, _VENDOR_ROOT=vendor,
                        _V1_ROOT=vendor / "societal_reasoning_v1",
                        _F_ROOT=vendor / "truth_accountability_f", _ARCHIVES=vendor / "original_archives"):
                    with self.assertRaises(RuntimeError): source_loader._capture_sources()

    def assessment(self, **overrides):
        values = dict(source_text_sha256="a" * 64, speaker_id="s", context_outcome=O.NO_CONTEXT,
            context_refs=(), context_status="NONE", gate_outcome=O.NOT_EVALUATED,
            gate_decision="NONE", gate_response="", runtime_review_status="NOT_ATTACHED",
            raw_proposal_sha256=None, claim_id=None, established_fact=False,
            shadow_mode=True, assessment_id="a")
        values.update(overrides)
        return ReasoningAssessment(**values)

    def test_sequence_boundaries_no_longer_share_commitment(self):
        left = self.assessment(context_refs=("a:b", "c"))
        right = self.assessment(context_refs=("a", "b:c"))
        self.assertNotEqual(left.commitment(), right.commitment())
        self.assertEqual(json.loads(left.canonical_bytes())["schema"], "ceta.reasoning-assessment.v2")
        self.assertNotEqual(self.assessment(claim_id=None).commitment(), self.assessment(claim_id="None").commitment())

    def test_mutable_or_untyped_assessment_fields_rejected(self):
        for overrides in ({"context_refs": ["1"]}, {"context_refs": ("a\0b",)},
                          {"established_fact": 1}, {"shadow_mode": "no"},
                          {"source_text_sha256": "bad"}, {"gate_response": "leaked"}):
            with self.subTest(fields=tuple(overrides)), self.assertRaises((TypeError, ValueError)):
                self.assessment(**overrides)

    def test_all_public_exports_are_bound(self):
        import ceta.reasoning as reasoning
        self.assertTrue(all(hasattr(reasoning, name) for name in reasoning.__all__))
        self.assertNotIn("TruthAccountabilityAdapter", reasoning.__all__)

    def test_initial_attachment_and_truthy_authority_strings_rejected(self):
        with self.assertRaises(PermissionError): ShadowModeController(ShadowLevel.ADVISORY_ATTACHED)
        for value in ("no", "false", 1):
            with self.assertRaises(TypeError): ShadowModeController(authorized=value)
            with self.assertRaises(TypeError):
                ShadowModeController().transition(ShadowLevel.ADVISORY_ATTACHED, authorized=value)
        controller = ShadowModeController(ShadowLevel.ADVISORY_ATTACHED, authorized=True)
        self.assertTrue(controller.should_attach)

    def test_known_vendor_decisions_are_classified_and_unknown_is_not_accepted(self):
        from ceta.reasoning.adapter import _gate_outcome
        expected = {"QUOTED_VERBATIM": O.ADVISORY_PASS, "MEANING_REVIEWED": O.ADVISORY_PASS,
                    "SUPPORTED_BY_CHECK": O.ADVISORY_PASS, "REFUTED_BY_CHECK": O.REVIEW_FAILURE,
                    "MODEL_PROPOSAL_REJECTED": O.REVIEW_FAILURE, "NEEDS_MEANING_REVIEW": O.ADVISORY_HOLD,
                    "NEEDS_RECONSIDERATION": O.ADVISORY_HOLD, "DISPUTED": O.ADVISORY_HOLD,
                    "STALE_EVIDENCE": O.ADVISORY_HOLD, "FUTURE_UNKNOWN": O.NOT_EVALUATED}
        for status, outcome in expected.items():
            with self.subTest(status=status): self.assertEqual(_gate_outcome(status), outcome)


if __name__ == "__main__":
    unittest.main()
