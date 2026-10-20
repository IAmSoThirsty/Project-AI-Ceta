"""Execute existing connected UI regressions and observe actual native titles."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import functools
import hashlib
import importlib
import json
import os
import sys
import unittest

R = Path(__file__).resolve().parent
F = R.parents[2]
CANDIDATE = F / '.agents/br1-20261014'
Q = F
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable).resolve() == PY.resolve()
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
TEMP = R / 'destination-temp'
TEMP.mkdir(exist_ok=False)
os.environ['TEMP'] = os.environ['TMP'] = str(TEMP)
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = read(CANDIDATE / 'TRANSFER-MANIFEST.json')
assert sha(CANDIDATE / 'TRANSFER-MANIFEST.json') == '12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
before = {item['relative_path']: sha(Q / item['relative_path']) for item in manifest['payloads']}
assert all(before[item['relative_path']] == item['candidate_sha256'] for item in manifest['payloads'])
assert all(sha(F / item['relative_path']) == item['candidate_sha256'] for item in manifest['payloads'])
imports = []
for path in sorted((Q / 'src/ceta').rglob('*.py')):
    parts = list(path.relative_to(Q / 'src').with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    name = '.'.join(parts)
    module = importlib.import_module(name)
    actual = Path(module.__file__).resolve()
    assert actual.is_relative_to(Q / 'src')
    imports.append({'module': name, 'actual_path': str(actual), 'sha256': sha(actual)})
assert len(imports) == 72
observed_titles = []
for relative, (_, expected_title) in manifest['title_changes'].items():
    name = '.'.join(Path(relative).relative_to('src').with_suffix('').parts)
    module = importlib.import_module(name)
    tree = ast.parse((Q / relative).read_text(encoding='utf-8'))
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)
        and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'setWindowTitle' and call.args
                and isinstance(call.args[0], ast.Constant) and call.args[0].value == expected_title
                for call in ast.walk(node))]
    assert len(classes) == 1
    cls = getattr(module, classes[0])
    original = cls.__init__
    def observe_constructor(original, source_module, expected):
        @functools.wraps(original)
        def wrapped(self, *args, **kwargs):
            original(self, *args, **kwargs)
            actual = self.windowTitle()
            assert actual == expected, (source_module, actual, expected)
            observed_titles.append({'module': source_module, 'native_window_title': actual})
        return wrapped
    cls.__init__ = observe_constructor(original, name, expected_title)
names = ('test_operator_view', 'test_preparation_view', 'test_task_meaning_view', 'test_task_view')
suite = unittest.TestLoader().loadTestsFromNames(names)
def ids(value):
    if isinstance(value, unittest.TestSuite):
        for child in value:
            yield from ids(child)
    else:
        yield value.id()
expected_ids = list(ids(suite))
assert len(expected_ids) == len(set(expected_ids)) and not any('_FailedTest' in name for name in expected_ids)
class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []
    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)
started = datetime.now(timezone.utc).isoformat()
raw = R / 'destination-desktop.txt'
with raw.open('x', encoding='utf-8', buffering=1) as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Result).run(suite)
after = {relative: sha(Q / relative) for relative in before}
assert before == after
assert all(sha(F / item['relative_path']) == item['candidate_sha256'] for item in manifest['payloads'])
observed_modules = {item['module'] for item in observed_titles}
assert observed_modules == {'.'.join(Path(relative).relative_to('src').with_suffix('').parts)
                            for relative in manifest['title_changes']}
passed = result.wasSuccessful() and not result.skipped and result.executed_ids == expected_ids
from PySide6.QtWidgets import QApplication
record = {'schema_version': 1, 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'source_root': str(F), 'candidate_root': str(CANDIDATE), 'active_destination_root': str(F), 'manifest_sha256': sha(CANDIDATE / 'TRANSFER-MANIFEST.json'),
    'python_executable': str(PY), 'Qt_platform': QApplication.instance().platformName(),
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skips': len(result.skipped), 'expected_ids': expected_ids, 'executed_ids': result.executed_ids,
    'native_title_observations': observed_titles, 'observed_title_modules': sorted(observed_modules),
    'imports': imports, 'before_hashes': before, 'after_hashes': after,
    'actual_source_unchanged': True, 'actual_application_journal_sha256': sha(R / 'active-application/APPLIED.json'), 'raw_sha256': sha(raw), 'exit_status': 0 if passed else 1,
    'limits': ['Real Qt on Windows using offscreen platform',
               'Existing controlled owner/session fixtures remain tests; production authorization claims unchanged']}
with (R / 'destination-desktop.json').open('x', encoding='utf-8') as output:
    json.dump(record, output, indent=2)
    output.write('\n')
print(json.dumps({key: record[key] for key in ('tests_run', 'failures', 'errors', 'skips', 'observed_title_modules', 'exit_status')}))
raise SystemExit(record['exit_status'])
