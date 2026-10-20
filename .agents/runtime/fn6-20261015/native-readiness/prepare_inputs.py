"""Freeze already-approved FN6 inputs for a future separately released run."""
from readiness_support import *
import struct


def verify_actual_review():
    review, _ = pinned_json(R / 'independent-review/review.json', REVIEW_PIN)
    persisted = decode((R / 'fn6-20261015/receipts/review.json').read_bytes())
    state = decode((R / 'fn6-20261015/state.json').read_bytes())
    result = decode((R / 'fn6-20261015/results/review.json').read_bytes())
    require(set(persisted) == set(review) | {'git_baseline', 'observed_git', 'receipt_hash'}, 'REVIEW_PERSISTED_FIELDS')
    require(all(canonical(persisted[k]) == canonical(v) for k, v in review.items()), 'REVIEW_PERSISTED_MISMATCH')
    fingerprint = sha(canonical({k: v for k, v in persisted.items() if k != 'receipt_hash'}).encode('utf8'))
    require(fingerprint == persisted['receipt_hash'], 'REVIEW_FINGERPRINT_MISMATCH')
    require(len(review) == 13 and len(persisted) == 16 and review['run_id'] == 'fn6-20261015'
            and review['node_id'] == 'review' and review['changed_files'] == []
            and all(type(row['exit_status']) is int and row['exit_status'] == 0 for row in review['commands']),
            'STRICT_LOCAL_REVIEW_REQUIRED')
    require(decode((R / 'fn6-20261015/claims.json').read_bytes()) == {}, 'COMPONENT_CLAIMS_NOT_RELEASED')
    node = state['nodes']['review']
    artifact = sha(canonical(dict(input_hash=review['input_hash'], result=review['result'])).encode('utf8'))
    require(node['artifact_hash'] == artifact and node['executor_id'] == '/root/wt1_reviewer'
            and state['sequence'] == 9, 'REVIEW_ARTIFACT_OR_STATE_MISMATCH')
    require(node['state'] == 'SUCCEEDED' and node['receipt_hash'] == fingerprint
            and review['decision'] == 'approved' and type(review['exit_status']) is int
            and review['exit_status'] == 0 and review['executor_id'] == '/root/wt1_reviewer'
            and review['result']['manifest_sha256'] == MANIFEST_PIN, 'ROOT_COMPONENT_REVIEW_NOT_ACCEPTED')
    require(set(result) == {'node_id', 'receipt_hash', 'result'} and result['node_id'] == 'review'
            and result['receipt_hash'] == fingerprint and canonical(result['result']) == canonical(review['result']),
            'ROOT_REVIEW_RESULT_ENVELOPE')
    return review


def literal_worker(tree):
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key == 'HELPERS':
                values[key] = ast.literal_eval(node.value)
            elif key == 'CHILD':
                require(isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add)
                        and isinstance(node.value.left, ast.Name) and node.value.left.id == 'HELPERS',
                        'FIXED_CHILD_EXPRESSION_CHANGED')
                values[key] = values['HELPERS'] + ast.literal_eval(node.value.right)
    require(set(values) == {'HELPERS', 'CHILD'}, 'WORKER_SOURCE_NOT_FOUND')
    return values['CHILD']


def main():
    require(Path(sys.executable) == PY and sys.flags.dont_write_bytecode and struct.calcsize('P') == 8,
            'EXACT_E3_PREPARATION_REQUIRED')
    require(not (N / INPUTS_NAME).exists(), 'INPUTS_ALREADY_FROZEN')
    manifest, manifest_facts = pinned_json(Q / 'TRANSFER-MANIFEST.json', MANIFEST_PIN)
    payloads = payload_snapshot(manifest)
    review = verify_actual_review()
    ordinary_custody = ordinary(R / 'bounded_custody.py')
    require(ordinary_custody['sha256'] == CUSTODY_PIN, 'REVIEWED_CUSTODY_CHANGED')
    raw, _ = pinned_bytes(R / 'bounded_custody.py', CUSTODY_PIN)
    if (N / 'bounded_custody.py').exists():
        require(ordinary(N / 'bounded_custody.py')['sha256'] == CUSTODY_PIN, 'EXISTING_CUSTODY_COPY_CHANGED')
    else:
        fs.write_new(N / 'bounded_custody.py', raw)
    lineage = decode((R / 'INPUTS.json').read_bytes())
    e3_before = lineage['E33601']
    require(len(e3_before) == 3601, 'EXPECTED_E3_3601')
    environment = {'E3/' + name: ordinary(E3 / name) for name in sorted(e3_before)}
    require(all(environment['E3/' + name] == facts for name, facts in e3_before.items()), 'E3_NATIVE_DRIFT_FROM_FN6')
    current_members = {p.relative_to(E3).as_posix() for p in E3.rglob('*') if p.is_file()}
    require(current_members == set(e3_before), 'E3_ORDINARY_MEMBERSHIP_DRIFT')
    base = Path(sys._base_executable).resolve(strict=True)
    environment['base_python'] = ordinary(base)
    for name in ('python312.dll', 'DLLs/_sqlite3.pyd', 'Lib/threading.py', 'Lib/subprocess.py',
                 'Lib/unittest/case.py', 'Lib/unittest/result.py', 'Lib/unittest/runner.py',
                 'Lib/unittest/suite.py', 'Lib/unittest/loader.py', 'Lib/ctypes/__init__.py'):
        environment['base/' + name] = ordinary(Path(sys.base_prefix) / name)
    proof_paths = {
        'FN6_manifest': Q / 'TRANSFER-MANIFEST.json',
        'FN6_author_implement': R / 'implement.json',
        'FN6_author_seal': R / 'AUTHOR-SEAL.json',
        'FN6_distinct_review': R / 'independent-review/review.json',
        'FN6_distinct_persisted_review': R / 'fn6-20261015/receipts/review.json',
        'FN6_distinct_result': R / 'fn6-20261015/results/review.json',
        'FN6_distinct_report': R / 'independent-review/REPORT.json',
        'FN6_distinct_readback': R / 'independent-review/REVIEW-READBACK.json',
        'FN6_distinct_seal': R / 'independent-review/REVIEW-SEAL.json',
        'FN5_rejected_manifest': F / '.agents/fn5-20261015/TRANSFER-MANIFEST.json',
        'FN5_rejected_review': F / '.agents/runtime/fn5-20261015/independent-review/review.json',
        'FN5_rejected_report': F / '.agents/runtime/fn5-20261015/independent-review/REPORT.json',
        'FN5_rejected_readback': F / '.agents/runtime/fn5-20261015/independent-review/REVIEW-READBACK.json',
        'FN5_rejected_seal': F / '.agents/runtime/fn5-20261015/independent-review/REVIEW-SEAL.json',
        'FN6_parent_failure_readback': R / 'FAILED-PARENT-READBACK.json',
        'KA5_parent_manifest': F / '.agents/ka5-20261015/TRANSFER-MANIFEST.json',
        'KA5_controlled_component_review': F / '.agents/runtime/ka5-20261015/independent-review/review.json',
        'KA5_prior_native_findings_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/ROOT-NATIVE-FINDINGS.json',
        'KA5_prior_native_readiness_review_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/ROOT-REVIEW.json',
        'KA5_prior_native_inputs_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/PREPARED-INPUTS.json',
        'KA4_consumed_native_findings': F / '.agents/runtime/ka4-20261015/native-readiness/ROOT-NATIVE-FINDINGS.json',
        'KA4_consumed_native_seal': F / '.agents/runtime/ka4-20261015/native-readiness/FAILED-ATTEMPT-SEAL.json',
        'KA4_readiness_Root_review': F / '.agents/runtime/ka4-20261015/native-readiness/ROOT-REVIEW.json',
        'KA4_readiness_frozen_inputs': F / '.agents/runtime/ka4-20261015/native-readiness/PREPARED-INPUTS-r2.json',
        'KA3_rejected_manifest': F / '.agents/ka3-20261015/TRANSFER-MANIFEST.json',
        'KA2_rejected_manifest': F / '.agents/ka2-20261015/TRANSFER-MANIFEST.json',
        'KA2_historical_native_recipe_only': F / '.agents/runtime/ka2-20261015/native-r7/RESULT.json',
        'F4_library_manifest': F / '.agents/re-foundation4-20261015/TRANSFER-MANIFEST.json',
    }
    foundation = decode(proof_paths['F4_library_manifest'].read_bytes())
    # Preserve the actual accepted parent review references as data. The FN6
    # Root approval above qualifies only the controlled FN6 component; neither
    # a lineage pin nor this preparation credits seven native test execution.
    references = {}
    def collect(value, label, depth=0):
        require(depth <= 24, 'LINEAGE_BOUND')
        if type(value) is dict:
            if set(value) == {'repository_relative_path', 'sha256'} and 'review' in label.lower():
                path = F / fs.relative_name(value['repository_relative_path'])
                facts = ordinary(path)
                require(facts['sha256'] == value['sha256'], 'PARENT_REVIEW_PIN_MISMATCH')
                references[label] = facts
            else:
                for key, item in value.items():
                    collect(item, label + '/' + key, depth + 1)
        elif type(value) is list:
            for index, item in enumerate(value):
                collect(item, label + '/' + str(index), depth + 1)
    for key in ('parent_packages', 'successor_adoptions', 'owner_extensions', 'parent_qualification'):
        collect(foundation.get(key), key)
    proof_facts = {name: ordinary(path) for name, path in proof_paths.items()}
    require(decode(proof_paths['KA2_historical_native_recipe_only'].read_bytes())['expected_ids'] == list(IDS),
            'ORIGINAL_NATIVE_ORDER_CHANGED')
    proof_facts.update({'parent_component/' + name: facts for name, facts in references.items()})
    original, _ = pinned_bytes(Q / 'tests/contract/test_cpu_execution_admission.py',
                              payloads['tests/contract/test_cpu_execution_admission.py']['sha256'])
    methods = method_asts(original)
    jobs_raw, _ = pinned_bytes(Q / 'tests/contract/test_windows_jobs.py',
                              payloads['tests/contract/test_windows_jobs.py']['sha256'])
    child = literal_worker(ast.parse(jobs_raw))
    script_facts = {name: ordinary(N / name) for name in SCRIPTS}
    inputs = dict(schema_version=1, at=utc(), prepared_by='/root/pressure_writer',
        component_author='/root/pressure_writer', independent_component_reviewer='/root/wt1_reviewer',
        independence_limit='I authored FN6 and this readiness adaptation; the distinct FN6 component review is a prerequisite, and Root must independently review/release these tools. Controlled providers are not genuine authority.',
        candidate_root=str(Q), candidate_manifest=manifest_facts, candidate352=payloads,
        scripts=script_facts, proofs=proof_facts, environment=environment,
        python_version=sys.version, python_base_prefix=sys.base_prefix, SystemRoot=os.environ['SystemRoot'],
        fixture_root=decode((N / 'TASK-BINDING.json').read_bytes())['future_fixture_root'],
        test_ids=list(IDS), original_method_ast_sha256=methods,
        historical_native_recipe='Only original method ID/order; no KA2 native pass or Source acceptance transferred to FN6.',
        worker_child_source_sha256=sha(child.encode('utf8')), fixture_expected_lifetimes_when_complete=8,
        native_execution='NOT_RUN', actual_CPU_effects='NOT_RUN', profile_Hello='FORBIDDEN',
        source_conservation_claim=False, live_Source_pin=False, Source_publication=False,
        original_restricted_no_profile_case='EXCLUDED_NOT_RUN',
        authority_capacity_settlement='Controlled providers; no genuine approval/native observer qualification',
        inner_timing='All original method bodies, 500ms acquisition,60s request,1/2s barriers,1s cleanup restore,5s fixture retirement and native clock bounds unchanged',
        child_wait_seconds=WAIT_SECONDS,
        wait_limit='Held job wait is finite; arbitrary synchronous native launch/cleanup is not preempted by Python.',
        release_required='Exact Root review plus fresh <=15min Root engineering release; create-only ONE-ATTEMPT before native import/creation.',
        future_effects=['OWNED_ORDINARY_WORKERS', 'CLASS9_JOB_SETUP', 'ORIGINAL_SEVEN_CLASS15_CASES',
                       'DISPOSABLE_SQLITE', 'NATIVE_CLOCK_REGISTRATION', 'OWNED_EVENTS_THREADS'],
        unresolved_prior_custody='No adoption/waiver of parent unsupervised probe, old timed-out SQLite closure, F4 fixture metadata109, OS2 or pending controlled lease pairs.',
        prior_preparation_read_errors=decode((N / 'TASK-BINDING.json').read_bytes())['preparation_read_errors'],
        no_native_run_or_approval_record_created=True)
    fixture = Path(inputs['fixture_root'])
    require(fixture.parent == Q / '.agents/fixtures' and fixture.name.startswith('fn6-native-')
            and not fixture.exists(), 'FUTURE_PRIVATE_FIXTURE_NOT_FRESH')
    fs.safe_components(fixture, allow_missing=True)
    save(N / INPUTS_NAME, inputs)
    print(canonical(dict(payloads=len(payloads), environment_files=len(environment), scripts=len(script_facts),
                         exact_methods=len(methods), component_review_references=len(references), native_execution='NOT_RUN')))


if __name__ == '__main__':
    main()
