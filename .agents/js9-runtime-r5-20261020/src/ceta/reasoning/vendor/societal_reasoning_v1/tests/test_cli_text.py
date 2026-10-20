import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from societal_reasoning.cli import main


class TestTextCli(unittest.TestCase):
    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(map(str, args)))
        return code, out.getvalue(), err.getvalue()

    def test_assess_and_review_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "src.txt"
            report = Path(td) / "assessment.json"
            draft = Path(td) / "draft.txt"
            source.write_text("I might attend.\n", encoding="utf-8")
            draft.write_text('You said "I will attend."', encoding="utf-8")
            status, output, error = self.call("assess", source)
            self.assertEqual(status, 0, error)
            a = json.loads(output)
            self.assertEqual(a["utterance"]["text"], "I might attend.\n")
            report.write_text(output, encoding="utf-8")
            status, output, error = self.call("review-draft", report, draft)
            self.assertEqual(status, 1, error)
            self.assertEqual(json.loads(output)["status"], "hold")

    def test_material_dictionary_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "u.txt"
            p.write_text("What is the context?", encoding="utf-8")
            status, output, error = self.call("assess", p, "--material", "context")
            self.assertEqual(status, 0, error)
            self.assertEqual(json.loads(output)["response_mode"], "necessary_clarification")

    def test_invalid_sense_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "u.txt"
            p.write_text("What is the context?", encoding="utf-8")
            status, _, error = self.call("assess", p, "--sense", "context")
            self.assertEqual(status, 2)
            self.assertIn("WORD=ID", error)

    def test_pass_returns_zero(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            ass = Path(td) / "a.json"
            draft = Path(td) / "draft.txt"
            src.write_text("I might attend.", encoding="utf-8")
            draft.write_text('You said "I might attend."', encoding="utf-8")
            _, a, _ = self.call("assess", src)
            ass.write_text(a, encoding="utf-8")
            status, report, _ = self.call("review-draft", ass, draft)
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(report)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
