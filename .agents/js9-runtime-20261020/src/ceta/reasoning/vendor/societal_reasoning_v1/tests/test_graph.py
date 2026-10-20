import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.graph import KnowledgeGraph, read_jsonl
from societal_reasoning.models import Concept, Edge


def c(n):
    return Concept.from_dict({"id":n,"label":f"Concept {n}", "summary":f"Summary {n}", "source":{"kind":"test"}})


class GraphTests(unittest.TestCase):
    def test_starter_loads(self):
        g = KnowledgeGraph.starter()
        self.assertGreaterEqual(len(g.concepts), 100)
        self.assertGreaterEqual(len(g.edges), 35)

    def test_seed_status_is_not_verified(self):
        g = KnowledgeGraph.starter()
        self.assertEqual(g.audit()["independently_verified_count"], 0)
        self.assertEqual(g.concepts[171].status, "source_transcribed")

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate concept"):
            KnowledgeGraph([c(1), c(1)])

    def test_dangling_edges_rejected(self):
        with self.assertRaisesRegex(ValueError, "Dangling"):
            KnowledgeGraph([c(1)], [Edge(1,2,"enables","test")])

    def test_duplicate_edges_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate edge"):
            KnowledgeGraph([c(1),c(2)], [Edge(1,2,"enables","x"), Edge(1,2,"enables","y")])

    def test_search_meme(self):
        result = KnowledgeGraph.starter().search("memes")
        self.assertEqual(result[0].id, 576)

    def test_search_empty(self):
        self.assertEqual(KnowledgeGraph.starter().search("!?"), [])

    def test_search_limits(self):
        with self.assertRaises(ValueError):
            KnowledgeGraph.starter().search("trust",limit=0)

    def test_neighbors_explicit(self):
        neighbors = KnowledgeGraph.starter().neighbors(576)
        self.assertTrue(any(x["concept"]["id"] == 171 for x in neighbors))
        self.assertTrue(all("provenance" in x["via"] for x in neighbors))

    def test_neighbors_reject_unknown(self):
        with self.assertRaises(KeyError):
            KnowledgeGraph.starter().neighbors(999999)

    def test_neighbors_reject_depth(self):
        with self.assertRaises(ValueError):
            KnowledgeGraph.starter().neighbors(576,depth=30)

    def test_audit_requires_complete_import(self):
        stats = KnowledgeGraph.starter().audit()
        self.assertEqual(stats["concept_count"], 2000)
        self.assertEqual(stats["unpopulated_ids_within_range_count"], 0)
        self.assertEqual(stats["original_inventory_ids_not_present"], 0)
        self.assertEqual(stats["status_counts"], {"source_transcribed": 2000})

    def test_from_file(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"concepts.jsonl"
            p.write_text(json.dumps(c(1).to_dict())+"\n",encoding="utf-8")
            self.assertIn(1, KnowledgeGraph.from_files(p).concepts)

    def test_bad_jsonl_gives_source_location(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"data.jsonl"
            p.write_text('not json\n')
            with self.assertRaisesRegex(ValueError, r":1:"):
                read_jsonl(p)


if __name__ == "__main__":
    unittest.main()
