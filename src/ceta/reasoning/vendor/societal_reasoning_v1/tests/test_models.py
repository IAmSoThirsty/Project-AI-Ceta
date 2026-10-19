import unittest

from societal_reasoning.models import Concept, Edge, Evidence, Scenario


class ModelTests(unittest.TestCase):
    def test_valid_concept(self):
        obj = Concept.from_dict({"id": 1, "label": "A", "summary": "B", "source": {"kind": "test"}})
        self.assertEqual(1, obj.id)

    def test_duplicate_unknown_concept_key(self):
        with self.assertRaisesRegex(ValueError, "Unexpected concept"):
            Concept.from_dict({"id":1,"label":"A","summary":"B","source":{"kind":"test"},"magic": 9})

    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            Concept.from_dict({"id":1,"label":"A","summary":"B","source":{"kind":"test"},"status":"perfect"})

    def test_source_transcription_needs_source_text(self):
        with self.assertRaises(ValueError):
            Concept.from_dict({"id":1,"label":"A","summary":"B","source":{"kind":"test"},"status":"source_transcribed"})

    def test_missing_source(self):
        with self.assertRaises(ValueError):
            Concept.from_dict({"id":1,"label":"A","summary":"B"})

    def test_invalid_edge_type(self):
        with self.assertRaises(ValueError):
            Edge.from_dict({"source":1,"target":2,"type":"is_always_true","rationale":"wrong"})

    def test_evidence_origin_restricted(self):
        with self.assertRaises(ValueError):
            Evidence.from_dict({"id":"x","statement":"something","origin":"trust_me"})

    def test_duplicate_evidence_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate evidence IDs"):
            Scenario.from_dict({"id":"s", "question":"q", "evidence":[
                {"id":"e", "statement":"A", "origin":"user_report"},
                {"id":"e", "statement":"B", "origin":"user_report"}]})

    def test_scenario_unknown_field(self):
        with self.assertRaisesRegex(ValueError, "Unexpected scenario"):
            Scenario.from_dict({"id":"s","question":"q","evidence":[],"run_shell":True})

    def test_scenario_roundtrip(self):
        data = {"id":"demo","question":"Is it a joke?", "evidence":[{"id":"e1", "statement":"quote", "origin":"quoted_material", "cues":["teasing"]}], "context":{"relationship":"friends"}}
        item = Scenario.from_dict(data)
        self.assertEqual(item, Scenario.from_dict(item.to_dict()))


if __name__ == "__main__":
    unittest.main()
