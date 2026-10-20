import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_measurements", ROOT / "tools/build_measurements.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildMeasurementTests(unittest.TestCase):
    def fixture(self):
        return {"coverage": {"sections": [{"applicability": "DIRECT", "implementation_status": "NOT_STARTED",
                "conformance_status": "NOT_EVALUATED"}]},
                "authority": {"current_source_coverage_state": "RECONCILIATION_OPEN", "volume_sources": [{}],
                              "adoption": "NOT_ADOPTED", "independent_review": "NOT_PERFORMED"},
                "progress": {"runtime_implementation": "NOT_STARTED", "test_execution": "NOT_RUN",
                             "installed_qualification": "NOT_RUN", "goal_state": "ACTIVE_NOT_COMPLETE"},
                "gates": {"gates": [{"id": "G-A", "state": "NOT_EVALUATED"}]},
                "cases": {"scenarios": [{"result": "NOT_RUN"}]}, "components": {"components": [{}]},
                "requirements": {"requirements": [{}]}, "packages": {"packages": [{}]}}

    def test_zero_unresolved_applicability_preserves_every_open_evidence_axis(self):
        result = module.measurements(self.fixture())
        self.assertEqual(result["applicability_classification"]["unresolved_applicability_classifications"], 0)
        self.assertEqual(result["source_reconciliation"]["state"], "RECONCILIATION_OPEN")
        self.assertEqual(result["requirement_adoption"]["state"], "NOT_ADOPTED")
        self.assertEqual(result["implementation"]["runtime_state"], "NOT_STARTED")
        self.assertEqual(result["conformance_verification"]["lifecycle_status_counts"], {"NOT_EVALUATED": 1})
        self.assertEqual(result["independent_acceptance"]["state"], "NOT_PERFORMED")
        self.assertEqual(result["gate_qualification"], {"G-A": "NOT_EVALUATED"})
        self.assertEqual(result["full_product"], "ACTIVE_NOT_COMPLETE")
        self.assertFalse(result["completion_inferred_from_applicability"])

    def test_pending_classification_is_counted_separately(self):
        documents = self.fixture()
        documents["coverage"]["sections"][0]["applicability"] = "UNRESOLVED"
        result = module.measurements(documents)["applicability_classification"]
        self.assertEqual(result["classified_sections"], 0)
        self.assertEqual(result["unresolved_applicability_classifications"], 1)

    def test_unknown_applicability_is_rejected(self):
        documents = self.fixture()
        documents["coverage"]["sections"][0]["applicability"] = "DONE"
        with self.assertRaisesRegex(ValueError, "UNKNOWN_APPLICABILITY"):
            module.measurements(documents)


if __name__ == "__main__":
    unittest.main()
