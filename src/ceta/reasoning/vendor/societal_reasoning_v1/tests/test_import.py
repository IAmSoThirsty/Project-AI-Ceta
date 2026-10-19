import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.ingest import InventoryImportError, import_markdown, write_jsonl


class ImportTests(unittest.TestCase):
    def sample(self):
        return "# Volume I\n## First section\n1. **Air and oxygen:** Sustains life; pollution damages populations.\n2. **Water:** Drinking, sanitation, and farming.\n continued information here.\n\n## Second section\n3. **Food:** Provides nutrition.\n"

    def test_import_preserves_ids_and_source(self):
        entries, report = import_markdown(self.sample(),volume=1,source_title="volume1.md",expected_start=1,expected_end=3,require_contiguous=True)
        self.assertEqual([x.id for x in entries], [1,2,3])
        self.assertEqual(entries[0].label, "Air and oxygen")
        self.assertEqual(entries[1].original_text, "2. **Water:** Drinking, sanitation, and farming.\n continued information here.")
        self.assertEqual(entries[0].status, "source_transcribed")
        self.assertEqual(entries[2].source["line_start"], 8)
        self.assertEqual(report["missing_expected_ids"], [])

    def test_partial_report_does_not_silently_fill_gaps(self):
        source = "1. **A:** Description.\n3. **B:** Description."
        _, report = import_markdown(source,volume=1,source_title="x",expected_start=1,expected_end=3)
        self.assertEqual(report["missing_expected_ids"], [2])

    def test_missing_contiguous_rejected(self):
        with self.assertRaises(InventoryImportError):
            import_markdown("1. **A:** x\n3. **B:** y",volume=1,source_title="x",expected_start=1,expected_end=3,require_contiguous=True)

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(InventoryImportError, "Duplicate"):
            import_markdown("1. **A:** x\n1. **B:** y",volume=1,source_title="x")

    def test_out_of_range_rejected(self):
        with self.assertRaisesRegex(InventoryImportError, "above expected"):
            import_markdown("1001. **A:** x",volume=1,source_title="x",expected_start=1,expected_end=1000)

    def test_bare_numbered_prose_ignored(self):
        entries,_=import_markdown("1. ordinary list line\n2. **Valid:** Actual.\n",volume=1,source_title="x")
        self.assertEqual(len(entries),1)

    def test_blank_description_rejected(self):
        with self.assertRaisesRegex(InventoryImportError, "No description"):
            import_markdown("1. **A:**\n",volume=1,source_title="x")

    def test_write_jsonl_roundtrip(self):
        entries,_=import_markdown(self.sample(),volume=1,source_title="x")
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"out.jsonl"
            write_jsonl(entries,p)
            self.assertEqual(len([json.loads(x) for x in p.read_text().splitlines()]),3)


if __name__ == "__main__":
    unittest.main()
