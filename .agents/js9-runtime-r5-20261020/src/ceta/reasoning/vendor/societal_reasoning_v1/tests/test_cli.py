import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from societal_reasoning.cli import main


class CLITests(unittest.TestCase):
    def run_cli(self, argv):
        out=io.StringIO()
        err=io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result=main(argv)
        return result,out.getvalue(),err.getvalue()

    def test_demo(self):
        code,out,_=self.run_cli(["demo"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["primary"]["rule_id"],"public_group_ridicule")

    def test_audit(self):
        code,out,_=self.run_cli(["audit"])
        self.assertEqual(code,0)
        self.assertGreaterEqual(json.loads(out)["concept_count"],100)

    def test_search(self):
        code,out,_=self.run_cli(["search","ridicule"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)[0]["id"],171)

    def test_concept_lookup(self):
        code,out,_=self.run_cli(["concept","1069"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["label"],"Conversation framing")

    def test_unknown_concept_error(self):
        code,_,err=self.run_cli(["concept","999999"])
        self.assertEqual(code,2)
        self.assertIn("Unknown concept",err)

    def test_ingest_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"volume.md"
            dest=Path(tmp)/"volume.jsonl"
            src.write_text("2001. **Example:** New concept.\n2002. **Another:** Second one.\n",encoding="utf-8")
            code,out,_=self.run_cli(["ingest",str(src),str(dest),"--volume","3","--expected-start","2001","--expected-end","2002","--require-contiguous"])
            self.assertEqual(code,0)
            self.assertEqual(json.loads(out)["report"]["imported"],2)
            self.assertTrue(dest.exists())

    def test_reason_file(self):
        p=Path(__file__).resolve().parents[1]/"examples"/"technical_review.json"
        code,out,_=self.run_cli(["reason",str(p)])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["primary"]["rule_id"],"technical_work_criticism")


if __name__ == "__main__":
    unittest.main()
