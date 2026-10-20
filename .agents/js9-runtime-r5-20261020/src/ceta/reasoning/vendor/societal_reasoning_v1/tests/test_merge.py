import unittest
from societal_reasoning.merge import merge_concepts
from societal_reasoning.models import Concept


def make(id, label="Concept", status="seed_summary_pending_transcription", description="Placeholder"):
    return Concept.from_dict({
        "id":id,"label":label,"summary":description,"status":status,
        "original_text":description if status != "seed_summary_pending_transcription" else None,
        "source":{"kind":"test","entry_id":id},
    })


class MergeTests(unittest.TestCase):
    def test_transcription_upgrades_seed(self):
        items, report = merge_concepts([[make(1)], [make(1,status="source_transcribed", description="Original recorded")]])
        self.assertEqual(len(items),1)
        self.assertEqual(items[0].summary,"Original recorded")
        self.assertEqual(report["upgraded_ids"],[1])

    def test_does_not_downgrade(self):
        items,_=merge_concepts([[make(1,status="source_transcribed", description="Original")], [make(1)]])
        self.assertEqual(items[0].status,"source_transcribed")

    def test_same_grade_conflict_rejected(self):
        with self.assertRaisesRegex(ValueError,"Competing equal-status"):
            merge_concepts([[make(1,description="A")],[make(1,description="B")]])

    def test_label_collision_rejected(self):
        with self.assertRaisesRegex(ValueError,"Conflicting labels"):
            merge_concepts([[make(1,"X")],[make(1,"Y")]])

    def test_non_overlapping_sources_merge(self):
        entries,report=merge_concepts([[make(2)],[make(1)]])
        self.assertEqual([c.id for c in entries],[1,2])
        self.assertEqual(report["merged_count"],2)

if __name__ == "__main__":
    unittest.main()
