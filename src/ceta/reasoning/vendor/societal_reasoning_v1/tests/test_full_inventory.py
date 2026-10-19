"""Release-blocking complete source inventory tests (not social truth verification)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.graph import KnowledgeGraph, read_jsonl
from societal_reasoning.ingest import InventoryImportError, import_markdown
from societal_reasoning.merge import merge_concepts
from societal_reasoning.models import Concept

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'src' / 'societal_reasoning' / 'resources'


def source(volume):
    return ROOT / 'knowledge' / f'volume-{volume:02}-full.md'


def parse(volume):
    start, end = ((1, 1000) if volume == 1 else (1001, 2000))
    file = source(volume)
    return import_markdown(
        file.read_text(encoding='utf-8'), volume=volume, source_title=file.name,
        expected_start=start, expected_end=end, require_contiguous=True,
    )


class FullInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = KnowledgeGraph.canonical()
        cls.first, cls.first_report = parse(1)
        cls.second, cls.second_report = parse(2)

    def test_both_volumes_are_exactly_1000(self):
        self.assertEqual((len(self.first), len(self.second)), (1000, 1000))

    def test_all_ids_exactly_once_and_contiguous(self):
        self.assertEqual(sorted(self.graph.concepts), list(range(1, 2001)))

    def test_each_volume_contains_only_its_range(self):
        self.assertEqual([c.id for c in self.first], list(range(1, 1001)))
        self.assertEqual([c.id for c in self.second], list(range(1001, 2001)))

    def test_all_concepts_preserve_nonempty_source_text(self):
        self.assertTrue(all(c.original_text and c.summary.strip() and c.label.strip()
                            and c.status == 'source_transcribed' for c in self.graph.concepts.values()))

    def test_no_seed_records_in_canonical_database(self):
        self.assertEqual(self.graph.audit()['status_counts'], {'source_transcribed': 2000})

    def test_no_independent_factual_verification_claim(self):
        self.assertEqual(self.graph.audit()['independently_verified_count'], 0)

    def test_compiled_canonical_matches_both_markdown_sources(self):
        observed = [x.to_dict() for x in self.first + self.second]
        compiled = [Concept.from_dict(x).to_dict() for x in read_jsonl(RES / 'concepts.full.jsonl')]
        self.assertEqual(observed, compiled)

    def test_individual_volume_compilations_match_sources(self):
        self.assertEqual([x.to_dict() for x in self.first],
                         [Concept.from_dict(x).to_dict() for x in read_jsonl(RES / 'concepts.volume-01.full.jsonl')])
        self.assertEqual([x.to_dict() for x in self.second],
                         [Concept.from_dict(x).to_dict() for x in read_jsonl(RES / 'concepts.volume-02.full.jsonl')])

    def test_source_sha256_per_record_matches_actual_markdown(self):
        for volume, records in ((1, self.first), (2, self.second)):
            expected = hashlib.sha256(source(volume).read_bytes()).hexdigest()
            self.assertTrue(all(record.source['source_sha256'] == expected for record in records))

    def test_entry_sha256_per_record_matches_text(self):
        for concept in self.graph.concepts.values():
            self.assertEqual(concept.source['entry_sha256'],
                             hashlib.sha256(concept.original_text.encode('utf-8')).hexdigest())

    def test_provenance_points_to_correct_volume(self):
        for i in range(1, 2001):
            c = self.graph.concepts[i]
            self.assertEqual(c.source['entry_id'], i)
            self.assertEqual(c.source['volume'], 1 if i <= 1000 else 2)
            self.assertEqual(c.source['title'], source(c.source['volume']).name)

    def test_no_empty_domains(self):
        self.assertTrue(all(len(c.domains) == 1 for c in self.graph.concepts.values()))

    def test_sample_cross_domain_labels_and_original_ids(self):
        expected = {
            1: 'Air and oxygen', 33: 'Adulthood', 171: 'Ridicule',
            576: 'Memes', 729: 'Genocide', 1000: 'Social continuity',
            1001: 'Civil timekeeping', 1069: 'Conversation framing',
            1080: 'Context collapse in conversation', 1159: 'Theory of mind',
            1645: 'Instruction precedence', 1664: 'Action authorization gates',
            1909: 'Release authorization', 1999: 'Last-mile service failure',
            2000: 'The implementation–experience gap',
        }
        for identifier, label in expected.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(self.graph.concepts[identifier].label, label)

    def test_historical_seed_label_corrected_at_1909(self):
        legacy = {x['id']: x for x in read_jsonl(RES / 'concepts.starter.jsonl')}
        self.assertEqual(legacy[1909]['label'], 'Change-control procedures')
        self.assertEqual(self.graph.concepts[1908].label, 'Change-control procedures')
        self.assertEqual(self.graph.concepts[1909].label, 'Release authorization')

    def test_duplicate_source_entry_rejected(self):
        txt = source(1).read_text(encoding='utf-8')
        txt += '\n1. **Air and oxygen:** Duplicated entry.\n'
        with self.assertRaisesRegex(InventoryImportError, 'Duplicate'):
            import_markdown(txt, volume=1, source_title='corrupt.md',
                            expected_start=1, expected_end=1000, require_contiguous=True)

    def test_missing_source_entry_rejected(self):
        txt = source(1).read_text(encoding='utf-8')
        txt = '\n'.join(line for line in txt.splitlines() if not line.startswith('576. '))
        with self.assertRaisesRegex(InventoryImportError, 'Missing 1 IDs'):
            import_markdown(txt, volume=1, source_title='corrupt.md',
                            expected_start=1, expected_end=1000, require_contiguous=True)

    def test_out_of_range_source_entry_rejected(self):
        txt = source(1).read_text(encoding='utf-8')
        txt += '\n2001. **Extra:** Must fail.\n'
        with self.assertRaisesRegex(InventoryImportError, 'above expected'):
            import_markdown(txt, volume=1, source_title='corrupt.md',
                            expected_start=1, expected_end=1000, require_contiguous=True)

    def test_compiler_read_only_validation_passes(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts'/'compile_inventory.py')],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['included'], 2000)

    def test_corrupted_compiled_record_detectable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'copy.jsonl'
            lines = (RES/'concepts.volume-01.full.jsonl').read_text(encoding='utf-8').splitlines()
            row = json.loads(lines[0]); row['summary'] = 'Changed without source edit'
            lines[0] = json.dumps(row)
            path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
            self.assertNotEqual([x.to_dict() for x in self.first], read_jsonl(path))

    def test_all_graph_edges_still_reference_source_concepts(self):
        self.assertEqual(len(self.graph.edges), 45)
        for edge in self.graph.edges:
            self.assertIn(edge.source, self.graph.concepts)
            self.assertIn(edge.target, self.graph.concepts)
            self.assertTrue(edge.provenance.startswith('curator_hypothesis'))

    def test_canonical_and_legacy_constructor_agree(self):
        self.assertEqual(KnowledgeGraph.starter().audit(), self.graph.audit())

    def test_default_search_finds_added_source_entry(self):
        result = self.graph.search('statelessness')
        self.assertTrue(any(c.id == 1797 for c in result))

    def test_first_and_last_from_runtime(self):
        self.assertEqual((self.graph.get(1).label, self.graph.get(2000).source['volume']),
                         ('Air and oxygen', 2))

    def test_full_merge_has_no_overrides_or_duplicates(self):
        merged, report = merge_concepts([self.first, self.second])
        self.assertEqual(len(merged), 2000)
        self.assertEqual(report['upgraded_from_lower_status_count'], 0)

    def test_renumbering_changes_provenance_and_causes_gate_failure(self):
        txt = source(2).read_text(encoding='utf-8').replace(
            '1999. **Last-mile service failure:**',
            '9999. **Last-mile service failure:**', 1,
        )
        with self.assertRaisesRegex(InventoryImportError, 'above expected'):
            import_markdown(txt, volume=2, source_title='corrupt.md',
                            expected_start=1001, expected_end=2000, require_contiguous=True)


if __name__ == '__main__':
    unittest.main()
