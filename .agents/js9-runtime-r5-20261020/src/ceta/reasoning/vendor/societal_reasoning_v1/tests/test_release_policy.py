import json
import unittest
from pathlib import Path

from societal_reasoning import __version__
from societal_reasoning.graph import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]

class TestReleasePolicy(unittest.TestCase):
    def test_owner_fixed_release_version(self):
        self.assertEqual(__version__, "1")
        self.assertEqual(json.loads((ROOT / "manifest.json").read_text())["version"], "1")
        self.assertIn('version = "1"', (ROOT / "pyproject.toml").read_text())

    def test_requirement_register_has_120_items_without_fake_completion(self):
        from scripts.requirement_register import create_register
        rows = create_register()
        self.assertEqual(rows["planned_requirements"], 120)
        self.assertEqual(len(rows["requirements"]), 120)
        self.assertGreater(rows["counts"]["not_implemented_or_not_verified"], 1)
        self.assertGreater(rows["counts"]["partial"], 1)
        self.assertEqual(sum(rows["counts"].values()), 120)

    def test_verified_bounded_cannot_be_used_as_general_conformance(self):
        from scripts.requirement_register import create_register
        rows = create_register()
        self.assertEqual(rows["type"], "development_traceability_not_conformance_certificate")
        for x in rows["requirements"]:
            self.assertNotIn(x["status"], ("done", "compliant", "complete"))

    def test_full_inventory_remains_authoritative(self):
        graph = KnowledgeGraph.canonical()
        self.assertEqual(len(graph.concepts), 2000)
        self.assertEqual(graph.audit()["independently_verified_count"], 0)


if __name__ == '__main__':
    unittest.main()
