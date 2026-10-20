"""Reject frozen FN5 once on actual initializer failure; preserve all evidence."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/fn5-20261015'
Q = F / '.agents/fn5-20261015'
V = Path(__file__).resolve().parent
RUN = 'fn5-20261015'
ACTOR = '/root/wt1_reviewer'
PIN = '7c324af5d0a5293e5fab57785e7ffabc3e2b69b6530ef5c1d4320d5cb303fa2d'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.R = V
read = lambda path: json.loads(Path(path).read_bytes())


def methods(path):
    tree = ast.parse(Path(path).read_bytes())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'KernelTransactions')
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_methods(path):
    tree = ast.parse(Path(path).read_bytes())
    return {cls.name + '.' + node.name: s.digest(ast.dump(node, include_attributes=False).encode())
        for cls in tree.body if isinstance(cls, ast.ClassDef)
        for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


def main():
    assert s.sha(Q / 'TRANSFER-MANIFEST.json') == PIN
    assert s.sha(R / 'implement.json') == 'abd5c85fa9e1b3945f418b06e7bf69f48f0aea64866e7c5b69b3e4ec0aaaf5d3'
    assert s.sha(R / 'AUTHOR-SEAL.json') == 'cc3357f3968f8d505287bb3a684c55689bbb3acd5a8ce904baac33708ba48e7b'
    m, inputs = read(Q / 'TRANSFER-MANIFEST.json'), read(R / 'INPUTS.json')
    probe = read(V / 'initializer-binding-r1/RESULT.json')
    assert probe['tests_run'] == 1 and probe['failures'] == 3 and probe['errors'] == probe['skips'] == 0 and probe['exit_status'] == 1
    assert probe['primary_type'] is None and len(probe['facts']) == 3
    assert all(row['exact_primary'] and row['manual_binding_calls'] == 1 and row['exact_owner']
        and not row['owner_unbound'] and row['bound_kernel_missing_preparation_check']
        and row['next_constructor_error'] == 'OWNER_PREPARATION_KERNEL_BINDING at $'
        and row['borrowed_store_stays_open'] and row['borrowed_connection_executes_select']
        and not row['transaction_open'] for row in probe['facts'])
    physical = probe['physical_resources']
    assert len(physical['sqlite']) == 3 and physical['owned_resources_closed'] is True and physical['remaining_resources'] == []
    assert all(row['physical_closed_probe'] for row in physical['sqlite'])
    assert all(row['closed'] and row['fileno_denied'] for row in physical['streams'])
    assert all(row['closed'] for row in physical['os_descriptors'])
    assert probe['remaining_threads'] == probe['forbidden_calls'] == []
    current = {name: s.ordinary(Q / name) for name in m['payloads']}
    assert current == probe['candidate_before'] == probe['candidate_after']
    assert current == {name: row['candidate'] for name, row in m['payloads'].items()}
    for name, pin in m['scripts'].items(): assert s.sha(R / name) == pin
    parents = {}
    inherited_mismatches = []
    for label, package in inputs['packages'].items():
        reference = package['manifest'];path = F / reference['repository_relative_path']
        assert s.sha(path) == reference['sha256']
        manifest = read(path);root = path.parent
        observed = {name: s.ordinary(root / name) for name in manifest['payloads']}
        assert observed == {name: row['candidate'] for name, row in manifest['payloads'].items()}
        tested = {}
        for name in manifest['payloads']:
            if not (name.startswith('tests/') and name.endswith('.py') and (Q / name).exists()): continue
            original, joined = test_methods(root / name), test_methods(Q / name)
            mismatches = [identifier for identifier, pin in original.items() if joined.get(identifier) != pin]
            for identifier in mismatches:
                inherited_mismatches.append(dict(package=label, path=name, method=identifier))
            tested[name] = dict(original_methods=len(original), mismatches=mismatches)
        parents[label] = dict(manifest=reference, payloads=len(observed), ordinary_native_exact=True,
            test_method_comparison=tested, own_review_reference=package['review']['review'],
            live_state_snapshot_is_historical=True)
    assert all(row['path'] == 'tests/contract/test_projections.py'
        and row['method'] == 'ProjectionTests.test_read_failure_preserves_primary_exception_when_rollback_observation_fails'
        for row in inherited_mismatches), inherited_mismatches
    base = methods(F / '.agents/ka5-20261015/src/ceta/kernel/transactions.py')
    owner = methods(F / '.agents/os5-20261015/src/ceta/kernel/transactions.py')
    joined = methods(Q / 'src/ceta/kernel/transactions.py')
    conserved = {name: ast.dump(node, include_attributes=False) == ast.dump(joined[name], include_attributes=False)
        for name, node in base.items() if name not in ('__init__', 'prepare')}
    assert len(conserved) == 31 and all(conserved.values())
    for name in ('prepare', '_prepare'):
        assert ast.dump(ast.Module(body=joined[name].body, type_ignores=[]), include_attributes=False) == \
            ast.dump(ast.Module(body=owner[name].body, type_ignores=[]), include_attributes=False)
    assert ast.unparse(joined['prepare'].decorator_list[0]) == '_coordinated'
    e3 = s.PY.parents[1]
    environment = {name: s.ordinary(e3 / name) for name in inputs['E33601']}
    assert environment == inputs['E33601'] and len(environment) == 3601
    observed_members = {path.relative_to(e3).as_posix() for path in e3.rglob('*') if path.is_file()}
    assert observed_members == set(environment)
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt
    from taar.orchestration_persistence import sha256_json
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files, _artifact_hash
    state, claims = read(R / RUN / 'state.json'), read(R / RUN / 'claims.json')
    claim = claims['review'];graph = read(R / RUN / 'graph.json')['graph']
    assert state['sequence'] == 8 and state['nodes']['review']['state'] == 'RUNNING'
    assert claim['executor_id'] == ACTOR and Path(claim['workspace']) == Q and claim['effective_write_scope'] == []
    author, stored_author = read(R / 'implement.json'), read(R / RUN / 'receipts/implement.json')
    assert len(author) == 12 and len(stored_author) == 15
    normalized = validate_receipt(author, run_id=RUN, node_id='implement', executor_id='/root/pressure_writer',
        input_hash=author['input_hash'], claimed_at=author['started_at'], node=graph['nodes']['implement'])
    normalized.pop('receipt_hash');normalized.update(git_baseline=stored_author['git_baseline'], observed_git=stored_author['observed_git'])
    author_fp = sha256_json(normalized)
    assert author_fp == stored_author['receipt_hash'] == state['nodes']['implement']['receipt_hash']
    assert read(R / RUN / 'results/implement.json') == dict(node_id='implement', receipt_hash=author_fp, result=author['result'])
    snapshot = _snapshot_workspace(Q, Path('T:/'))
    assert _artifact_hash(snapshot, author['changed_files']) == state['nodes']['implement']['artifact_hash']
    assert _changed_files(claim['baseline_snapshot'], snapshot) == []
    conservation = dict(at=s.utc(), candidate351=current, parents=parents, E33601=environment,
        E3_membership_exact=True, KA5_31_methods=conserved, OS5_prepare_bodies_exact=True,
        KA5_coordinated_prepare_decorator=True, accepted_test_successor_mismatches=inherited_mismatches,
        author_official_fingerprint=author_fp, author_artifact_verified=True,
        no_Source_mutation_by_job=True, no_live_Source_hash_claim=True)
    s.write_new(V / 'CONSERVATION.json', conservation)
    report = dict(at=s.utc(), author='/root/pressure_writer', reviewer=ACTOR, decision='rejected',
        manifest_sha256=PIN, finding=dict(id='FN5-INIT-POST-BIND-ALLOCATION', classification='blocking current integrated-library acceptance',
            source='src/ceta/kernel/transactions.py:59-63; src/ceta/identity/owner_session.py:508-524',
            defect='Owner binding is published before the remaining fallible bound-method allocation. A failed constructor leaves the owner tied to an incomplete new kernel and prevents a subsequent constructor.',
            measured_controls=['KeyboardInterrupt', 'SystemExit', 'MemoryError'], probe=s.reference(V / 'probe_initializer_binding.py'),
            result=s.reference(V / 'initializer-binding-r1/RESULT.json'), raw=s.reference(V / 'initializer-binding-r1/RAW.txt'),
            repair='In a fresh successor, compute the bound preparation check before final owner binding publication; retain all existing coordinator/events/key/lock/import validation before publication. Replay the unchanged three failure subcases.'),
        actual_execution=dict(methods=1, failed_subcases=3, errors=0, skips=0, process_exit_status=1,
            selected458_independent_execution='NOT_RUN: initializer acceptance blocker established first',
            author458_result='Preserved author evidence only, not independent acceptance',
            original7native='NOT_RUN', no_inheritance_of_KA5_native_success=True),
        physical_custody=dict(SQL_connections=3, streams=len(physical['streams']), descriptors=len(physical['os_descriptors']),
            exact_physical_closed=True, remaining_resources=[], remaining_threads=[], borrowed_store_closed_only_by_fixture=True),
        independent_inspection=dict(KA5_31_methods_exact=True, OS5_prepare_bodies_exact=True,
            KA5_coordinated_decorator_exact=True, all_parent_test_method_ASTs_exact_except_approved_projection_successor=True,
            default_admission_unchanged=True, Source_publication=False),
        author_receipt=dict(raw12=s.reference(R / 'implement.json'), persisted15=s.reference(R / RUN / 'receipts/implement.json'),
            official_fingerprint=author_fp, author_artifact=state['nodes']['implement']['artifact_hash']),
        conservation=s.reference(V / 'CONSERVATION.json'),
        reviewer_read_preparation_failures=[
            'Read-only rg initially named nonexistent identity/native_cpu_owner.py and cpu_owner.py; actual implementation is owner_session.py.',
            'Read-only metadata inspection expected nonexistent INPUTS.parent_payloads and stopped with KeyError; actual packages reference their exact manifests. No product assertion or execution was relabelled.'],
        controlled_provider_limit='Existing fixture controls native identity, approval, clock and target observations; actual canonical constructor/SQLite execute. No native product process, profile, Hello or CPU Set.',
        dependency_authorship_disclosure='Reviewer authored earlier WT4/AC3/OS2 dependencies. Rely on prior distinct Root reviews; independently reject this FN5 initializer integration.',
        copied_product_LOC_credit=0, integrated_Source_LOC_credit=0, Source_publication=False,
        complete_gate=False, disposition='Separate FN6 author repair required; frozen FN5 remains unchanged and rejected')
    s.write_new(V / 'REPORT.json', report)
    receipt = dict(schema_version=1, run_id=RUN, node_id='review', executor_id=ACTOR,
        started_at=claim['claimed_at'], finished_at=s.utc(), input_hash=claim['input_hash'], changed_files=[],
        result=dict(manifest_sha256=PIN, report=s.reference(V / 'REPORT.json'),
            initializer_failure=s.reference(V / 'initializer-binding-r1/RESULT.json'),
            conservation=s.reference(V / 'CONSERVATION.json'), selected458_independent='NOT_RUN', Source_publication=False),
        commands=[dict(command=subprocess.list2cmdline([str(s.PY), '-B', '-X', 'utf8', str(V / 'probe_initializer_binding.py')]), exit_status=1)],
        validations=[dict(name='final_bound_method_failure_does_not_publish_owner_binding', passed=False),
            dict(name='exact_primary_borrowed_SQLite_and_physical_fixture_retirement', passed=True),
            dict(name='candidate351_parent_payloads_E33601_and_author_receipt_conserved', passed=True)],
        exit_status=1, decision='rejected')
    validate_receipt(receipt, run_id=RUN, node_id='review', executor_id=ACTOR, input_hash=claim['input_hash'],
        claimed_at=claim['claimed_at'], node=graph['nodes']['review'])
    s.write_new(V / 'review.json', receipt)
    argv = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        'node', 'complete', RUN, 'review', str(V / 'review.json'), '--runtime-root', str(R)]
    done = subprocess.run(argv, cwd=F, capture_output=True)
    for suffix, raw in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (V / ('review-complete.' + suffix + '.txt')).open('xb') as out: out.write(raw)
    # Read installed state before interpreting any command/status response.
    final, final_claims = read(R / RUN / 'state.json'), read(R / RUN / 'claims.json')
    stored, result = read(R / RUN / 'receipts/review.json'), read(R / RUN / 'results/review.json')
    s.write_new(V / 'review-complete.json', dict(argv=argv, exit_status=done.returncode,
        response=json.loads(done.stdout.decode('utf-8-sig')), actual_state=final['nodes']['review']['state']))
    assert final['sequence'] == 9 and final['nodes']['review']['state'] == 'FAILED' and final_claims == {}
    assert final['nodes']['review']['artifact_hash'] is None
    assert len(receipt) == 13 and len(stored) == 16 and all(stored[k] == value for k, value in receipt.items())
    fingerprint = sha256_json({k: value for k, value in stored.items() if k != 'receipt_hash'})
    assert fingerprint == stored['receipt_hash'] == final['nodes']['review']['receipt_hash']
    assert result == dict(node_id='review', receipt_hash=fingerprint, result=receipt['result'])
    s.write_new(V / 'REVIEW-READBACK.json', dict(at=s.utc(), reviewer=ACTOR, decision='rejected',
        actual_state='FAILED', sequence=9, claims={}, local13=s.reference(V / 'review.json'),
        persisted16=s.reference(R / RUN / 'receipts/review.json'), result3=s.reference(R / RUN / 'results/review.json'),
        official_fingerprint=fingerprint, artifact_hash=None, Source_publication=False, native7='NOT_RUN'))
    members = {path.relative_to(V).as_posix(): s.ordinary(path) for path in sorted(V.rglob('*')) if path.is_file()}
    s.write_new(V / 'REVIEW-SEAL.json', dict(at=s.utc(), reviewer=ACTOR, scope_closed=True,
        actual_state='FAILED', sequence=9, claims={}, members=members, Source_publication=False))
    assert all(s.ordinary(V / name) == row for name, row in members.items())
    print(json.dumps(dict(actual_review='FAILED', sequence=9, claims={}, decision='rejected',
        report=s.reference(V / 'REPORT.json'), review=s.reference(V / 'review.json'),
        readback=s.reference(V / 'REVIEW-READBACK.json'), seal=s.reference(V / 'REVIEW-SEAL.json'),
        members=len(members), official_fingerprint=fingerprint, methods=1, failed_subcases=3, native7='NOT_RUN')))


if __name__ == '__main__': main()
