"""Narrow editor-retention continuation after the preserved JS3 full failure."""
from pathlib import Path
import json
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er2-20261015'
P = F / '.agents/js3-20261015'
PR = F / '.agents/runtime/js3-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PR))
import js3_support as j
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def main():
    assert not Q.exists() and not (R / s.RUN).exists()
    m, pin = j.manifest_record()
    assert pin == '19450a9fd28a45fc8b61d1e014bbe3a671f22324e0f02f772e3d7c95484b56a3'
    state = j.current_json(PR / j.RUN / 'state.json')
    assert state['nodes']['validate']['state'] == 'FAILED'
    assert state['nodes']['integrate']['state'] == 'BLOCKED'
    assert j.current_json(PR / j.RUN / 'claims.json') == {}
    inputs = j.verify()
    parent = {name: s.ordinary(P / name) for name in m['expected_payload_hashes']}
    assert len(parent) == 294
    assert {name: row['sha256'] for name, row in parent.items()} == m['expected_payload_hashes']
    s.write_new(R / 'SOURCE-INPUTS.json', {
        'at': s.utc(), 'Source290': inputs['Source290'], 'parent294': parent,
        'E33601': inputs['E33601'], 'python': inputs['python'],
        'base_python': inputs['base_python'], 'Git': inputs['Git'],
        'auxiliary_source11': inputs['auxiliary_source11'],
        'auxiliary_parent11': inputs['auxiliary_copies11'],
        'parent_manifest': s.reference(P / 'TRANSFER-MANIFEST.json'),
        'parent_assembly_review': s.reference(PR / 'independent-review/review.json'),
        'parent_complete_failure': s.reference(PR / 'root-validation/FAILED-VALIDATION-READBACK.json'),
        'actual_full_failure': s.reference(PR / 'candidate-full/RESULT.json'),
        'authority': 'Current project implementation; new independent repair unit. JS3 validation remains FAILED. Source remains290.'})
    Q.mkdir(exist_ok=False)
    s.invoke(['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', s.RUN], 'run-init')
    s.claim('discover')
    s.complete('discover', {'inputs': s.reference(R / 'SOURCE-INPUTS.json')},
        [{'command': 'E3 bootstrap.py finite native and hash inspection of Source290, parent294 and JS3 failed full proof', 'exit_status': 0}],
        [('exact current inputs and preserved failed predecessor', True)])
    s.claim('plan')
    paths = ['src/ceta/application/task_operator.py',
             'tests/contract/test_editor_retention_queue.py', 'contracts/EDITOR_RECOVERY_V1.md']
    s.write_new(R / 'TASK-BINDING.json', {
        'at': s.utc(), 'author': '/root', 'eligible_paths': paths,
        'scope': 'Fix the queued successor handoff after an acknowledged older inline editor-retention request; preserve ordinary typing coalescing and the existing authenticated single writer.',
        'observed_failure': 'Original TaskMeaningViewTests.test_invalid_last_field_preserves_whole_prior_form_until_atomic_repair observed one result instead of two in JS3 full1551.',
        'candidate_cause_to_verify': 'New capture sets editor_next_attempt_at=monotonic+0.15; old retain acknowledgement queues a differing latest payload but keeps that future deadline. An immediate ordinary poll can report no pending request.',
        'acceptance': ['Deterministic controlled-clock failure before repair and passing counterpart after repair',
            'Original failing method body unchanged, including its assertions',
            'Ordinary valid-input debounce preserved',
            'Only the latest complete serialized capture follows the acknowledged older write',
            'Uncertain/denied responses and unserialized capture failures never become automatic writes or durable claims',
            'All original editor recovery and task-meaning session/view methods unchanged and relevant cohorts executed',
            'Real fixture SQLite connections closed; no native/profile/Hello operation'],
        'exclusions': ['Source publication', 'retry of failed JS3 validate', 'changing original tests or deadlines',
            'new state stores or authority', 'live worker or host-profile operation']})
    s.complete('plan', {'binding': s.reference(R / 'TASK-BINDING.json'), 'eligible_paths': paths},
        [{'command': 'E3 bootstrap.py exact meaning-view capture, session drain/result and held-delivery helper inspection', 'exit_status': 0}],
        [('narrow existing handoff surface and unchanged authority', True)])
    s.claim('implement')
    for name, row in {**parent, **inputs['auxiliary_copies11']}.items():
        target = Q / name
        s.fs.safe_components(target.parent, allow_missing=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = s.ordinary(P / name)
        assert before == row
        with s.fs.open_source(P / name, exclusive=True) as stream:
            raw = stream.read()
        assert s.digest(raw) == row['sha256'] and s.ordinary(P / name) == before
        s.fs.write_new(target, raw)
    s.write_new(R / 'COPIED-INPUTS.json', {
        'at': s.utc(), 'candidate294': {name: s.ordinary(Q / name) for name in parent},
        'auxiliary_copies11': {name: s.ordinary(Q / name) for name in inputs['auxiliary_copies11']},
        'copied_code_new_authorship_credit': 0, 'Source_publication': False})
    print(json.dumps({'implement': 'RUNNING', 'candidate': str(Q), 'paths': paths,
                      'copied_payloads': 294, 'copied_auxiliaries': 11,
                      'copied_code_new_authorship_credit': 0}), flush=True)


if __name__ == '__main__':
    main()
