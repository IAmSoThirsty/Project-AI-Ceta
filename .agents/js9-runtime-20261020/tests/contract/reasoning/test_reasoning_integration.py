"""Tests for reasoning integration: source loader, assessment, shadow controller.

These tests exercise the CETA adapter layer without requiring Ollama
or any external service. They verify:
1. Source archive integrity checking
2. Assessment dataclass immutability and commitment determinism
3. Shadow mode transitions and authorization boundaries
4. Adapter initialization and synthetic assessment pipeline
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from ceta.reasoning.assessment import AssessmentOutcome, ReasoningAssessment
from ceta.reasoning.shadow import ShadowLevel, ShadowModeController


class TestAssessmentDataclass(unittest.TestCase):
    """Assessment immutability, commitment determinism, field bounds."""

    def _make_assessment(self, **overrides) -> ReasoningAssessment:
        defaults = dict(
            source_text_sha256="a" * 64,
            speaker_id="test-speaker",
            context_outcome=AssessmentOutcome.NO_CONTEXT,
            context_refs=(),
            context_status="TEST_STATUS",
            gate_outcome=AssessmentOutcome.NOT_EVALUATED,
            gate_decision="TEST_DECISION",
            gate_response="",
            runtime_review_status="NOT_ATTACHED",
            raw_proposal_sha256=None,
            claim_id=None,
            established_fact=False,
            shadow_mode=True,
            assessment_id="ra-test0001",
        )
        defaults.update(overrides)
        return ReasoningAssessment(**defaults)

    def test_frozen(self):
        a = self._make_assessment()
        with self.assertRaises(AttributeError):
            a.speaker_id = "modified"

    def test_commitment_deterministic(self):
        a = self._make_assessment()
        b = self._make_assessment()
        self.assertEqual(a.commitment(), b.commitment())
        self.assertTrue(a.commitment().startswith("sha256:"))

    def test_commitment_changes_with_content(self):
        a = self._make_assessment()
        b = self._make_assessment(speaker_id="other-speaker")
        self.assertNotEqual(a.commitment(), b.commitment())

    def test_commitment_changes_with_outcome(self):
        a = self._make_assessment(gate_outcome=AssessmentOutcome.ADVISORY_PASS)
        b = self._make_assessment(gate_outcome=AssessmentOutcome.ADVISORY_HOLD)
        self.assertNotEqual(a.commitment(), b.commitment())

    def test_all_outcomes_bounded(self):
        """Every AssessmentOutcome value is a known string."""
        expected = {
            "ADVISORY_PASS", "ADVISORY_HOLD", "CONTEXT_FOUND",
            "NO_CONTEXT", "SOURCE_UNAVAILABLE", "REVIEW_FAILURE",
            "NOT_EVALUATED",
        }
        actual = {v.value for v in AssessmentOutcome}
        self.assertEqual(actual, expected)


class TestShadowModeController(unittest.TestCase):
    """Shadow level transitions and authorization."""

    def test_default_level(self):
        c = ShadowModeController()
        self.assertEqual(c.level, ShadowLevel.SHADOW_SILENT)
        self.assertTrue(c.is_active)
        self.assertFalse(c.should_log)
        self.assertFalse(c.should_attach)

    def test_safe_transition_to_off(self):
        c = ShadowModeController()
        t = c.transition(ShadowLevel.OFF)
        self.assertEqual(c.level, ShadowLevel.OFF)
        self.assertFalse(c.is_active)
        self.assertEqual(t.from_level, ShadowLevel.SHADOW_SILENT)
        self.assertEqual(t.to_level, ShadowLevel.OFF)

    def test_safe_transition_to_logged(self):
        c = ShadowModeController()
        c.transition(ShadowLevel.SHADOW_LOGGED)
        self.assertTrue(c.should_log)
        self.assertFalse(c.should_attach)

    def test_attached_requires_authorization(self):
        c = ShadowModeController()
        with self.assertRaises(PermissionError):
            c.transition(ShadowLevel.ADVISORY_ATTACHED)

    def test_attached_succeeds_with_authorization(self):
        c = ShadowModeController()
        t = c.transition(ShadowLevel.ADVISORY_ATTACHED,
                         authorized=True, reason="owner_approved")
        self.assertEqual(c.level, ShadowLevel.ADVISORY_ATTACHED)
        self.assertTrue(c.should_attach)
        self.assertEqual(t.reason, "owner_approved")

    def test_noop_transition_rejected(self):
        c = ShadowModeController()
        with self.assertRaises(ValueError):
            c.transition(ShadowLevel.SHADOW_SILENT)

    def test_transition_history_preserved(self):
        c = ShadowModeController()
        c.transition(ShadowLevel.SHADOW_LOGGED)
        c.transition(ShadowLevel.OFF)
        history = c.transition_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].to_level, ShadowLevel.SHADOW_LOGGED)
        self.assertEqual(history[1].to_level, ShadowLevel.OFF)

    def test_all_levels_bounded(self):
        expected = {"OFF", "SHADOW_SILENT", "SHADOW_LOGGED", "ADVISORY_ATTACHED"}
        actual = {v.value for v in ShadowLevel}
        self.assertEqual(actual, expected)

    def test_invalid_type_rejected(self):
        with self.assertRaises(TypeError):
            ShadowModeController(initial="SHADOW_SILENT")

    def test_deactivation_from_attached_requires_auth(self):
        c = ShadowModeController()
        c.transition(ShadowLevel.ADVISORY_ATTACHED, authorized=True)
        with self.assertRaises(PermissionError):
            c.transition(ShadowLevel.OFF)
        c.transition(ShadowLevel.OFF, authorized=True)
        self.assertEqual(c.level, ShadowLevel.OFF)


class TestSourceLoader(unittest.TestCase):
    """Source loader archive verification (does not require loaded state)."""

    def test_archive_paths_exist(self):
        from ceta.reasoning.source_loader import _ARCHIVES
        v1 = _ARCHIVES / "Societal-Reasoning-Core-v1.zip"
        f = _ARCHIVES / "truth-accountability-reference-increments-A-F.zip"
        self.assertTrue(v1.exists(), f"V1 archive missing: {v1}")
        self.assertTrue(f.exists(), f"F archive missing: {f}")

    def test_archive_checksums_match(self):
        from ceta.reasoning.source_loader import verify_archives
        v1_match, f_match = verify_archives()
        self.assertTrue(v1_match, "V1 archive checksum mismatch")
        self.assertTrue(f_match, "F archive checksum mismatch")


class TestAdapterInitialization(unittest.TestCase):
    """Adapter lifecycle without Ollama dependency."""

    def test_uninitialized_assess_rejected(self):
        from ceta.reasoning.adapter import SocietalReasoningAdapter
        adapter = SocietalReasoningAdapter()
        with self.assertRaises(RuntimeError):
            adapter.assess(speaker_id="test", text="hello")

    def test_uninitialized_context_rejected(self):
        from ceta.reasoning.adapter import SocietalReasoningAdapter
        adapter = SocietalReasoningAdapter()
        with self.assertRaises(RuntimeError):
            adapter.context_only("hello")

    def test_default_shadow_mode(self):
        from ceta.reasoning.adapter import SocietalReasoningAdapter
        adapter = SocietalReasoningAdapter()
        self.assertTrue(adapter.shadow_mode)
        self.assertFalse(adapter.initialized)

    def test_synthetic_proposer_returns_json(self):
        import json
        from ceta.reasoning.adapter import SyntheticProposer
        p = SyntheticProposer()
        result = p.generate_proposal("src-1", "test text")
        parsed = json.loads(result)
        self.assertEqual(parsed["kind"], "observation")
        self.assertTrue(parsed["synthetic"])


if __name__ == "__main__":
    unittest.main()
