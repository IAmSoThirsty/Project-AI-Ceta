"""Reuse the exact independent RS3 runner with the frozen joined source cohort."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
S = R.parents[3]
source = S / ".agents/runtime/rs3-20261014/independent-review/run_affected.py"
text = source.read_text(encoding="utf-8")
assert text.count('Q = S / ".agents/rs3-20261014"') == 1
text = text.replace('Q = S / ".agents/rs3-20261014"', 'Q = S / ".agents/app3-20261014"')
text = text.replace('WR = S / ".agents/runtime/rs3-20261014"', 'WR = S / ".agents/runtime/app3-20261014"')
old = 'assert sha(manifest_path) == "864d9ab2842af8544ab69d44881ddc22a6f2ff3ec494aa3584c472ab3720e825"'
new = 'assert sha(manifest_path) == json.loads((WR / "implement.json").read_text())["result"]["manifest_sha256"]'
assert old in text
text = text.replace(old, new)
old_selectors = 'selectors = ["test_source_coverage", "test_task_meaning_view", "test_resource_management", "test_source_references", "test_task_view", "test_editor_recovery"]'
new_selectors = 'selectors = ["test_source_coverage", "test_task_meaning_view", "test_resource_management", "test_source_references", "test_task_view", "test_editor_recovery", "test_process_diagnostics", "test_windows_jobs"]'
assert old_selectors in text
text = text.replace(old_selectors, new_selectors)
text = text.replace('assert len(expected_ids) == len(set(expected_ids)) == 220',
                    'assert len(expected_ids) == len(set(expected_ids)) and len(expected_ids) > 220')
text = text.replace('"all_ceta_imports_inside_rs3": True', '"all_ceta_imports_inside_app3": True')
target = R / "run_affected.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"original_runner_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "joined_runner_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "changes": ["Exact APP3 ROOT, manifest bound to actual producer receipt", "Add diagnostics and Windows jobs selectors; retain all six earlier cohort modules", "No altered test source or qualification guard"]}))
