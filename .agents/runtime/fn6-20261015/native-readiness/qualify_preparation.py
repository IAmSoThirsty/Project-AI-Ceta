"""Finite FN6 preparation audit; never imports or executes a CETA module."""
from readiness_support import *
import difflib


def methods(raw):
    tree = ast.parse(raw)
    return {cls.name + '.' + node.name: ast.dump(node, include_attributes=False)
            for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


def declaration(raw, name):
    return ast.dump(next(node for node in ast.walk(ast.parse(raw))
                         if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name),
                    include_attributes=False)


def check_controls(label, count):
    path = N / label / 'RESULT.json'
    value, facts = pinned_json(path, ordinary(path)['sha256'])
    require(type(value['tests_run']) is int and value['tests_run'] == count
            and len(set(value['expected_ids'])) == count
            and value['expected_ids'] == value['executed_ids'] == value['stopped_ids']
            and all(type(value[k]) is int and value[k] == 0 for k in ('failures', 'errors', 'skips', 'exit_status'))
            and value['forbidden_calls'] == [] and value['native_execution'] == 'NOT_RUN'
            and value.get('actual_CETA_imports', []) == [], 'PURE_CONTROLS_FAILED')
    return dict(result=facts, raw=ordinary(N / label / 'tests.txt'))


def audit(label):
    require(not any(name == 'ceta' or name.startswith('ceta.') for name in sys.modules), 'UNEXPECTED_CETA_IMPORT')
    require(not any((N / name).exists() for name in ('ROOT-REVIEW.json', 'ROOT-NATIVE-RELEASE.json', 'ONE-ATTEMPT.json')),
            'UNEXPECTED_ROOT_REVIEW_RELEASE_OR_REAL_ATTEMPT')
    task = decode((N / 'TASK-BINDING.json').read_bytes())
    old = Path(task['reviewed_origin']['path'])
    old_review, old_facts = pinned_json(old / 'ROOT-REVIEW.json', task['reviewed_origin']['review_sha256'])
    require(old_review['scripts_sha256'] == task['reviewed_origin']['scripts_sha256'], 'PARENT_REVIEW_MAP_CHANGED')
    for name, pin in old_review['scripts_sha256'].items():
        require(ordinary(old / name)['sha256'] == pin
                and ordinary(N / 'reviewed-ka5-beforeimages' / name)['sha256'] == pin,
                'REVIEWED_PARENT_HELPER_CHANGED:' + name)
    old_controls = (N / 'reviewed-ka5-beforeimages/test_readiness_controls.py').read_bytes()
    new_controls = (N / 'test_readiness_controls.py').read_bytes()
    old_timing = (N / 'reviewed-ka5-beforeimages/test_timing_reader_controls.py').read_bytes()
    new_timing = (N / 'test_timing_reader_controls.py').read_bytes()
    require(len(methods(old_controls)) == 21 and methods(old_controls) == methods(new_controls), 'CONTROL21_AST_DRIFT')
    require(len(methods(old_timing)) == 3 and old_timing == new_timing, 'TIMING3_BYTES_DRIFT')
    require((Q / 'tests/contract/test_cpu_execution_admission.py').read_bytes() ==
            (F / '.agents/ka5-20261015/tests/contract/test_cpu_execution_admission.py').read_bytes(),
            'ORIGINAL_NATIVE_FILE_CHANGED')
    old_inputs = decode((old / 'PREPARED-INPUTS.json').read_bytes())
    native_raw = (Q / 'tests/contract/test_cpu_execution_admission.py').read_bytes()
    require(method_asts(native_raw) == old_inputs['original_method_ast_sha256']
            and list(IDS) == old_inputs['test_ids'], 'ORIGINAL_SEVEN_AST_OR_ORDER_DRIFT')
    current_runner = (N / 'run_native.py').read_bytes()
    previous_runner = (N / 'reviewed-ka5-beforeimages/run_native.py').read_bytes()
    require(all(declaration(current_runner, name) == declaration(previous_runner, name)
                for name in ('rejection_timing', 'Result', 'worker_gate')), 'READER_RESULT_OR_WORKER_GATE_CHANGED')
    for name in ('resource_witness.py', 'bounded_custody.py'):
        require((N / name).read_bytes() == (N / 'reviewed-ka5-beforeimages' / name).read_bytes(),
                'REVIEWED_WITNESS_OR_CUSTODY_CHANGED')
    fixture = Path(task['future_fixture_root'])
    require(fixture.parent == Q / '.agents/fixtures' and fixture.name.startswith('fn6-native-')
            and not fixture.exists(), 'FUTURE_PRIVATE_FIXTURE_NOT_ABSENT')
    fs.safe_components(fixture, allow_missing=True)
    require('fs.safe_components(fixture_root, allow_missing=True)\n    fixture_root.mkdir' in current_runner.decode('utf8'),
            'FUTURE_FIXTURE_ANCESTOR_GUARD_MISSING')
    controls = {name: check_controls(name + '-' + label, count)
                for name, count in (('pure-controls', 21), ('timing-controls', 3))}
    for path in N.glob('*.py'):
        compile(path.read_bytes(), str(path), 'exec')
    scripts = {name: ordinary(N / name) for name in SCRIPTS}
    return dict(at=utc(), author='/root/pressure_writer', independent_review=False,
                reviewed_parent=old_facts, candidate_manifest_sha256=MANIFEST_PIN,
                scripts=scripts, controls=controls, pure_methods=24, original21_ASTs_exact=True,
                timing3_bytes_exact=True, original7_ASTs_and_complete_file_exact=True,
                native_method_ASTs=method_asts(native_raw), original_native_ids=list(IDS),
                reader_Result_worker_gate_ASTs_exact=True, witness_custody_bytes_exact=True,
                future_fixture_root=str(fixture), future_fixture_absent=True,
                future_ancestor_guard='Pinned PR4 safe_components(..., allow_missing=True) before future create; no ancestor or fixture created in preparation',
                copied_product_LOC_credit=0, native_execution='NOT_RUN', actual_CPU_effects='NOT_RUN',
                profile_Hello='FORBIDDEN', live_Source_pin=False, Source_publication=False,
                genuine_authority_capacity='NOT_QUALIFIED; future native tests use original controlled providers',
                pending_controlled_pairs=11, inherited_custody_waived=False,
                no_Root_approval_release_or_real_attempt_created=True)


def main(argv):
    require(len(argv) in (1, 2), 'EXACT_CONTROL_LABEL_AND_OPTIONAL_FREEZE')
    label = argv[0]
    require(type(label) is str and label.isalnum(), 'SIMPLE_CONTROL_LABEL_REQUIRED')
    report = audit(label)
    if len(argv) == 1:
        report.update(component_review_pin_state='PENDING' if REVIEW_PIN is None else 'BOUND',
                      input_freeze='NOT_CREATED')
        save(N / ('STATIC-CHECK-' + label + '.json'), report)
        print(canonical(dict(pure_methods=24, native_execution='NOT_RUN', input_freeze='NOT_CREATED',
                             report_sha256=ordinary(N / ('STATIC-CHECK-' + label + '.json'))['sha256'])))
        return
    require(argv[1] == '--freeze', 'UNKNOWN_OPTION')
    inputs, input_facts = preflight()
    old = Path(decode((N / 'TASK-BINDING.json').read_bytes())['reviewed_origin']['path'])
    old_inputs = decode((old / 'PREPARED-INPUTS.json').read_bytes())
    require(inputs['environment'] == old_inputs['environment'], 'ENVIRONMENT_DRIFT_FROM_REVIEWED_KA5')
    membership = {'E3/' + p.relative_to(E3).as_posix() for p in E3.rglob('*') if p.is_file()}
    require(len(membership) == 3601 and membership == {k for k in inputs['environment'] if k.startswith('E3/')},
            'E3_MEMBERSHIP_DRIFT')
    require(len(inputs['candidate352']) == 352 and len(inputs['environment']) == 3612, 'FROZEN_INPUT_COUNT_MISMATCH')
    diffs = {}
    for name in SCRIPTS:
        before = (N / 'reviewed-ka5-beforeimages' / name).read_bytes()
        after = (N / name).read_bytes()
        body = ''.join(difflib.unified_diff(before.decode('utf8').splitlines(True), after.decode('utf8').splitlines(True),
            fromfile='reviewed_KA5/' + name, tofile='FN6/' + name))
        fs.write_new(N / (name + '.diff'), body.encode('utf8'))
        diffs[name] = dict(before_sha256=sha(before), after_sha256=sha(after),
                           diff=ordinary(N / (name + '.diff')), unchanged=not body)
    report.update(readiness='PREPARED_NOT_EXECUTED', component_review_sha256=REVIEW_PIN,
        inputs=input_facts, candidate352_exact=True, E3_ordinary3601_and_base11_exact=True,
        component_review_references=sum(k.startswith('parent_component/') for k in inputs['proofs']),
        finite_helper_diffs=diffs, native_bounds='Original test/driver/clock limits unchanged; no timing or native-call wrapper relaxation',
        release_limit='Fresh exact Root review plus <=900s Root release; create-only ONE-ATTEMPT;180s owned outer-child wait does not preempt synchronous calls',
        inherited_failures='KA4 consumed/FAILED; KA5 native PASSED on different cut only; rejected FN5; F4 directory metadata/r4 custody and NC3 command clarification remain explicit. No historical native acceptance inherited.',
        resource_limits='No native owner/thread/process/job/event/clock/SQLite fixture allocated by preparation. Controlled pure markers are temporary fixture files only; real marker absent.',
        expected_future_lifetimes=8, expected_future_native_cases=7,
        commands=[dict(argv=[str(PY), '-B', '-X', 'utf8', str(N / 'prepare_successor.py')], exit_status=0),
            dict(argv=[str(PY), '-B', '-X', 'utf8', str(N / 'test_readiness_controls.py'), label], exit_status=0),
            dict(argv=[str(PY), '-B', '-X', 'utf8', str(N / 'test_timing_reader_controls.py'), label], exit_status=0),
            dict(argv=[str(PY), '-B', '-X', 'utf8', str(N / 'prepare_inputs.py')], exit_status=0)])
    save(N / 'SELF-REVIEW.json', report)
    ready = dict(at=utc(), readiness='PREPARED_NOT_EXECUTED', preparer='/root/pressure_writer',
        independent_reviewer_and_release_owner='/root', inputs=input_facts,
        scripts_sha256={name: row['sha256'] for name, row in inputs['scripts'].items()},
        component_review_sha256=REVIEW_PIN, report=ordinary(N / 'SELF-REVIEW.json'),
        original_native_ids=list(IDS), pure_unique_methods=24, native_execution='NOT_RUN',
        future_command=[str(PY), '-B', '-X', 'utf8', str(N / 'supervise_native.py')],
        command_state='HELD_UNTIL_DISTINCT_ROOT_TOOL_REVIEW_AND_FRESH_ONE_ATTEMPT_RELEASE',
        fixture_root=inputs['fixture_root'], Source_publication=False, no_approval_release_or_real_attempt_created=True)
    save(N / 'READY-FOR-ROOT-REVIEW.json', ready)
    members = {path.relative_to(N).as_posix(): ordinary(path) for path in sorted(N.rglob('*')) if path.is_file()}
    save(N / 'PREPARATION-SEAL.json', dict(at=utc(), author='/root/pressure_writer', members=members,
        readiness='author_preparation_frozen', independent_approval=False, native_execution='NOT_RUN'))
    require(all(ordinary(N / name) == facts for name, facts in members.items()), 'SEALED_MEMBER_DRIFT')
    print(canonical(dict(inputs_sha256=input_facts['sha256'], ready_sha256=ordinary(N / 'READY-FOR-ROOT-REVIEW.json')['sha256'],
        report_sha256=ordinary(N / 'SELF-REVIEW.json')['sha256'], seal_sha256=ordinary(N / 'PREPARATION-SEAL.json')['sha256'],
        pure_methods=24, members=len(members), native_execution='NOT_RUN')))


if __name__ == '__main__':
    main(sys.argv[1:])
