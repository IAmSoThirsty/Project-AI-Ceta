"""Prepare an explicitly rebound independent successor harness; no native effects."""
from pathlib import Path
import ast, hashlib, json, os
F = Path('T:/00-Active/Project-AI-CETA')
D = Path(__file__).resolve().parent
assert D == F / '.agents/runtime/ac5-profile-tool-review2-20261015'
old = F / '.agents/runtime/ac5-profile-tool-review-20261015/run_independent.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(old) == 'ffbdb6696e1924f1d06ffcfad08c9832ea7d5488681157647560ce4c6480fa62'
original = old.read_text(encoding='utf8')
body = original
replacements = [
    ("assert D == F / '.agents/runtime/ac5-profile-tool-review-20261015'", "assert D == F / '.agents/runtime/ac5-profile-tool-review2-20261015'"),
    ("WRAPPER = '282658ad35faa4e9c51bf5ebdf232633e66b94f9ed61a948f781422cd9a2664e'", "WRAPPER = '372a14a567ddecc4ccb67848669afe641d71ebc7b1d66aaad4dcaa0b5b709570'"),
    ("assert sha(R / 'run_one_approved_attempt.py') == WRAPPER", "assert sha(R / 'run_one_approved_attempt_v2.py') == WRAPPER"),
    ("wrapper_path = R / 'run_one_approved_attempt.py'", "wrapper_path = R / 'run_one_approved_attempt_v2.py'"),
    ("    changed_hash = None\n    def drift(path, *args, **kwargs):", "    changed_hash = None\n    captured_review_facts = []\n    def captured_review(path, expected_sha):\n        nonlocal changed_hash\n        payload, identity = module.capture(path, expected_sha)\n        captured_review_facts.append({'captured_sha256': hashlib.sha256(payload).hexdigest(), 'identity': identity})\n        if change_review_between_reads and path == review_file:\n            path.write_text(json.dumps(dict(initial_review, decision='approved')), encoding='utf8')\n            changed_hash = sha(path)\n        return payload, identity\n    fake_module.capture = captured_review\n    def drift(path, *args, **kwargs):"),
    ("with patch.object(sys, 'argv', argv), patch.object(Path, 'read_text', drift),", "with patch.object(sys, 'argv', argv),"),
    ("        'changed_review_sha256': changed_hash, 'approval_file_exists': approval_file.exists(),", "        'changed_review_sha256': changed_hash, 'captured_review_facts': captured_review_facts,\n        'approval_file_exists': approval_file.exists(),"),
    ("# Exact prefix includes real frozen tool/proposal hashes and supplied review hash.", "# Exact prefix includes real frozen tool/proposal hashes; v2 captures review later."),
    ("        'wrapper loader/approval/inspection/child controls are simulated; no genuine approval supplied'],", "        'wrapper loader/approval/inspection/child controls are simulated; no genuine approval supplied',\n        'v2 fixture calls actual frozen tool.capture, then changes ONLY own fixture bytes after capture returns; old hostile test method unchanged',\n        'R1 rejected wrapper and all failing evidence remain historical and immutable'],"),
]
for before, after in replacements:
    assert body.count(before) == 1, before
    body = body.replace(before, after)
compile(body, str(D / 'run_independent.py'), 'exec')
def method_asts(text):
    return {node.name+'.'+method.name: ast.dump(method, include_attributes=False)
        for node in ast.walk(ast.parse(text)) if isinstance(node, ast.ClassDef)
        for method in node.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')}
assert method_asts(original) == method_asts(body)
with (D / 'run_independent.py').open('x', encoding='utf8', newline='\n') as out: out.write(body)
with (D / 'HARNESS-BINDING.json').open('x', encoding='utf8', newline='\n') as out:
    json.dump({'parent_harness': str(old), 'parent_sha256': sha(old),
        'harness_sha256': sha(D / 'run_independent.py'), 'own_method_ASTs_exact': True,
        'own_method_count': len(method_asts(original)),
        'reused_original_negative_methods': 30, 'reused_original_serialization_methods': 6,
        'stimulus_change': 'Replace own review bytes AFTER actual module.capture returns the original verified bytes; v2 no longer calls Path.read_text. Literal hostile method assertion remains byte/AST exact.',
        'old_failure_relabelled': False, 'wrapper_sha256': '372a14a567ddecc4ccb67848669afe641d71ebc7b1d66aaad4dcaa0b5b709570'}, out, indent=2)
    out.write('\n'); out.flush(); os.fsync(out.fileno())
print(json.dumps({'harness_sha256': sha(D / 'run_independent.py'), 'own_method_count': len(method_asts(body)), 'method_ASTs_exact': True}))
