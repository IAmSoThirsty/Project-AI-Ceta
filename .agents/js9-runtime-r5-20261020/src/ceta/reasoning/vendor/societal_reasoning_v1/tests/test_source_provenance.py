import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.graph import KnowledgeGraph
from societal_reasoning.ingest import import_markdown
from societal_reasoning.merge import merge_concepts
from societal_reasoning.models import Concept

ROOT=Path(__file__).resolve().parents[1]


class SourceProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=KnowledgeGraph.starter()

    def test_graph_includes_complete_2000(self):
        self.assertEqual(self.graph.audit()['concept_count'],2000)
        self.assertEqual(self.graph.audit()['status_counts']['source_transcribed'],2000)
        self.assertEqual(self.graph.audit()['original_inventory_ids_not_present'],0)

    def test_16_transcripts_have_source_hashes(self):
        for c in self.graph.concepts.values():
            if c.status=='source_transcribed':
                self.assertEqual(len(c.source['source_sha256']),64)
                self.assertEqual(hashlib.sha256(c.original_text.encode()).hexdigest(),c.source['entry_sha256'])

    def test_imports_match_bundled_source(self):
        for v,start,end in ((1,1,8),(2,1001,1008)):
            file=ROOT/'knowledge'/f'volume-{v:02}-{start:04}-{end:04}.md'
            records, report=import_markdown(file.read_text(),volume=v,source_title=file.name,expected_start=start,expected_end=end,require_contiguous=True)
            bundled=ROOT/'src'/'societal_reasoning'/'resources'/f'concepts.volume-{v:02}.excerpt.jsonl'
            rows=[Concept.from_dict(json.loads(line)) for line in bundled.read_text().splitlines()]
            self.assertEqual([x.to_dict() for x in records],[x.to_dict() for x in rows])
            self.assertEqual([x.id for x in records],list(range(start,end+1)))

    def test_hash_changes_when_source_changes(self):
        a='1. **Water:** Used for drinking.'
        b='1. **Water:** Used for drinking!'
        first,_=import_markdown(a,volume=1,source_title='v.md')
        second,_=import_markdown(b,volume=1,source_title='v.md')
        self.assertNotEqual(first[0].source['entry_sha256'],second[0].source['entry_sha256'])
        self.assertNotEqual(first[0].source['source_sha256'],second[0].source['source_sha256'])

    def test_identical_text_from_different_source_names_remains_attributable(self):
        txt='1. **Water:** Used for drinking.'
        a,_=import_markdown(txt,volume=1,source_title='one.md')
        b,_=import_markdown(txt,volume=1,source_title='two.md')
        self.assertNotEqual(a[0].source['title'],b[0].source['title'])

    def test_conflicting_same_status_transcripts_fail_closed(self):
        a,_=import_markdown('1. **Water:** One.',volume=1,source_title='one.md')
        b,_=import_markdown('1. **Water:** Two.',volume=1,source_title='two.md')
        with self.assertRaisesRegex(ValueError,'Competing equal-status'):
            merge_concepts([a,b])

    def test_no_claim_of_independent_verification(self):
        self.assertEqual(self.graph.audit()['independently_verified_count'],0)

    def test_all_inventory_present(self):
        self.assertEqual(self.graph.audit()['original_inventory_ids_not_present'],0)
        self.assertEqual(self.graph.get(33).label,'Adulthood')
        self.assertEqual(self.graph.get(2000).label,'The implementation–experience gap')

    def test_invalid_source_range_fails(self):
        with self.assertRaises(ValueError):
            import_markdown('1001. **Clock:** A.',volume=1,source_title='v',expected_start=1,expected_end=1000)

    def test_edge_count_unchanged(self):
        self.assertEqual(self.graph.audit()['relationship_count'],45)


if __name__=='__main__': unittest.main()
