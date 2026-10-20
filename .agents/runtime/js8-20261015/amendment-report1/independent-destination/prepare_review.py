"""Create-only reviewer helper successor; no product imports or native calls."""
from pathlib import Path
import argparse
import ast
import datetime
import difflib
import hashlib
import json
import sys
import uuid

F = Path('T:/00-Active/Project-AI-CETA')
P = F / '.agents/runtime/js8-20261015'
R = P / 'amendment-report1'
Q = F / '.agents/js8-amendment-report1-20261017'
V = R / 'independent-destination'
OLD = P / 'amendment-order1/independent-destination'
ACTOR = '/root/publication_recovery_review'
HELPERS = ('review_support.py', 'resource_observer.py', 'bounded_custody.py',
           'resource_witness.py', 'run_delivered.py', 'launch_delivered.py',
           'record_actual_delivered_review.py')


def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(path.read_bytes())
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def ref(path): return dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=sha(path))


def write(path, raw):
    assert path.parent == V
    with path.open('xb') as stream:
        assert stream.write(raw) == len(raw)


def save(name, value):
    write(V / name, (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--amendment-sha256', required=True)
    args = parser.parse_args()
    assert Path(__file__).resolve().parent == V
    assert not any(name == 'ceta' or name.startswith('ceta.') for name in sys.modules)
    pin, amendment_pin = args.manifest_sha256, args.amendment_sha256
    assert sha(Q / 'TRANSFER-MANIFEST.json') == pin
    assert sha(R / 'AMENDMENT.json') == amendment_pin
    m, a = read(Q / 'TRANSFER-MANIFEST.json'), read(R / 'AMENDMENT.json')
    assert all(sha(R / name) == value for name, value in a['reviewed_scripts'].items())
    original = {name: (OLD / name).read_bytes() for name in HELPERS}
    old_preparation = read(OLD / 'PREPARATION.json')
    assert {name: digest(raw) for name, raw in original.items()} == old_preparation['helpers']
    prepared = dict(original)
    text = original['review_support.py'].decode('utf8')
    edits = (
        ("R=F/'.agents/runtime/js8-20261015/amendment-order1';Q=F/'.agents/js8-amendment-order1-20261017'",
         "R=F/'.agents/runtime/js8-20261015/amendment-report1';Q=F/'.agents/js8-amendment-report1-20261017'"),
        ("ACTOR='/root/integration_amendment_review'", "ACTOR='" + ACTOR + "'"),
        ("PIN='6a99465610569df671fe736914ca2bd37f249e45794d3c6c4a7f5d044f32c31e'", "PIN='" + pin + "'"),
        ("AMENDMENT_PIN='3152785dde49c1cda26619b651ff89799ba03759c4594eb75004d110a75dadb4'",
         "AMENDMENT_PIN='" + amendment_pin + "'"),
        ("    for phase in ('candidate-full','destination-full'):\n",
         "    j.require_candidate_readiness(value['candidate_readiness'],source='after')\n"
         "    j.require_validation(value['candidate_readiness'],source='after')\n"
         "    for phase in ('destination-full',):\n"),
        ("    assert application['paths']==m['application_paths'] and application['Source_accepted'] is False\n",
         "    assert application['paths']==m['application_paths'] and application['Source_accepted'] is False\n"
         "    assert application['candidate_readiness']==value['candidate_readiness']\n"),
    )
    for before, after in edits:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    prepared['review_support.py'] = text.encode('utf8')
    record = original['record_actual_delivered_review.py'].decode('utf8')
    before = "        candidate_full=release['candidate_full'],candidate_full_launch=release['candidate_full_launch'],"
    after = "        candidate_readiness=release['candidate_readiness'],candidate_full_status='FAILED_PRESERVED',"
    assert record.count(before) == 1
    prepared['record_actual_delivered_review.py'] = record.replace(before, after).encode('utf8')
    delta = []
    for name, raw in prepared.items():
        compile(raw, str(V / name), 'exec')
        write(V / name, raw)
        if raw != original[name]:
            delta.extend(difflib.unified_diff(original[name].decode('utf8').splitlines(keepends=True),
                raw.decode('utf8').splitlines(keepends=True), fromfile=str(OLD / name), tofile=str(V / name)))
    write(V / 'HELPER-DELTA.diff', ''.join(delta).encode('utf8'))
    expected = m['expected_payload_hashes']
    assert len(expected) == 352 and expected == old_preparation['expected_payload_hashes']
    assert all(sha(Q / name) == value for name, value in expected.items())
    required = m['required_independent_ids']
    assert len(required) == len(set(required)) == 180 and required == old_preparation['required_ids']
    asts = {}
    for identifier in required:
        module, cls, name = identifier.split('.')
        tree = ast.parse((Q / 'tests/contract' / (module + '.py')).read_bytes())
        target = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls)
        method = next(node for node in target.body if isinstance(node, ast.FunctionDef) and node.name == name)
        asts[identifier] = digest(ast.dump(method, include_attributes=False).encode())
    assert asts == old_preparation['test_method_AST_hashes']
    assert all(name.startswith('test_cpu_execution_admission.NativeCpuExecutionAdmissionTests.') for name in required[-7:])
    assert not any(name.startswith('test_isolated_worker.') for name in required)
    tree = ast.parse((Q / 'tests/contract/test_windows_jobs.py').read_bytes())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == 'HELPERS': values[name] = ast.literal_eval(node.value)
            elif name == 'CHILD':
                assert isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add)
                assert isinstance(node.value.left, ast.Name) and node.value.left.id == 'HELPERS'
                values[name] = values['HELPERS'] + ast.literal_eval(node.value.right)
    child_pin = digest(values['CHILD'].encode('utf8'))
    assert child_pin == old_preparation['native_worker_program_sha256']
    fixture = F / '.agents/fixtures' / ('js8-report-delivered-' + uuid.uuid4().hex)
    assert not fixture.exists()
    helpers = {name: sha(V / name) for name in HELPERS}
    save('PREPARATION.json', dict(schema_version=1, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        author=ACTOR, manifest_sha256=pin, amendment=ref(R / 'AMENDMENT.json'),
        required_ids=required, expected_payload_hashes=expected, helpers=helpers,
        fixture_root=str(fixture), fixture_created=False, native_cpu_ids=required[-7:],
        test_method_AST_hashes=asts, native_worker_program_sha256=child_pin,
        execution='HELD_PENDING_ROOT_PUBLICATION_AND_EXACT_RELEASE', Source_publication=False,
        source_imports=False, native_execution=False, timeout_seconds=600, automatic_retry=False))
    save('HELPER-PROVENANCE.json', dict(author=ACTOR, original_root=str(OLD), original_preserved=True,
        manifest_sha256=pin, amendment_sha256=amendment_pin, previous_preparation=ref(OLD / 'PREPARATION.json'),
        helpers={name: dict(original_sha256=digest(original[name]), prepared_sha256=helpers[name],
            byte_identical=original[name] == prepared[name]) for name in HELPERS},
        changed_helpers=['review_support.py', 'record_actual_delivered_review.py'],
        changes='Successor cut and current reviewer identity; explicit publication readiness preserves failed candidate; strict destination full gate remains.',
        test_selection_changed=False, resource_observers_changed=False, product_changes=False,
        source_LOC_added=0, test_LOC_added=0, copied_LOC_credit=0))
    assert all((OLD / name).read_bytes() == original[name] for name in HELPERS)
    assert sha(Q / 'TRANSFER-MANIFEST.json') == pin and sha(R / 'AMENDMENT.json') == amendment_pin
    assert not fixture.exists()
    print(json.dumps(dict(preparation=ref(V / 'PREPARATION.json'), helper_pins=helpers,
        fixture_root=str(fixture), selection=180, payloads=352, source_imports=False,
        native_execution=False, original_helpers_preserved=True)))


if __name__ == '__main__': main()
