"""Finite independent successor disposition; no native effects or Source edits."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, importlib.util, json, os, stat, sys
F = Path('T:/00-Active/Project-AI-CETA')
D = Path(__file__).resolve().parent
R = F / '.agents/runtime/ac5-profile-tool-20261015'
PRIOR = F / '.agents/runtime/ac5-profile-tool-review-20261015'
assert D == F / '.agents/runtime/ac5-profile-tool-review2-20261015'
sys.dont_write_bytecode = True
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
utc = lambda: datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path, value):
    assert Path(path).is_relative_to(D)
    with Path(path).open('x', encoding='utf8', newline='\n') as out:
        json.dump(value, out, indent=2, allow_nan=False); out.write('\n'); out.flush(); os.fsync(out.fileno())
reader = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(reader) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('ac5_review2_native_reader', reader)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)
def ordinary(path):
    path = fs.safe_components(Path(path)); info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    native = fs.file_identity(info); size, digest, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == native and size == native['bytes']
    return {'sha256': digest, 'native_identity': native}
before, result = read(D / 'BEFORE.json'), read(D / 'RESULT-r1.json')
assert result['tests_run'] == 49 and result['exit_status'] == 0
assert not result['failures'] and not result['errors'] and not result['skips'] and not result['forbidden_calls']
assert result['expected_ids'] == result['executed_ids'] == result['stopped_ids']
prior_result = read(PRIOR / 'RESULT-r1.json')
assert prior_result['expected_ids'] == result['expected_ids']
assert len(prior_result['failures']) == 1 and prior_result['exit_status'] == 1
assert sha(PRIOR / 'SEAL-r1.json') == 'a8b8970077645260c776d3be0a224ef7f6a9055de0b34daff81ea46139897bf4'
prior_seal = read(PRIOR / 'SEAL-r1.json')
for name, expected in prior_seal['members'].items(): assert ordinary(PRIOR / name) == expected
after_source = {name: ordinary(F / name) for name in before['source']}
after_candidate = {name: ordinary(F / '.agents/ac5-20261015' / name) for name in before['candidate']}
after_tool = {name: ordinary(R / name) for name in before['tool_tree']}
after_dependencies = {name: ordinary(F / name) for name in before['dependencies']}
after_originals = {name: ordinary(F / name) for name in before['originals']}
git = [fs.text_git(F, 'rev-parse', '--show-toplevel', '--git-common-dir', 'HEAD'),
       fs.text_git(F, 'status', '--porcelain=v1', '--untracked-files=no')]
assert before['source'] == after_source and len(after_source) == 290
assert before['candidate'] == after_candidate and len(after_candidate) == 295
assert before['tool_tree'] == after_tool and before['dependencies'] == after_dependencies and before['originals'] == after_originals
assert before['git'] == git
assert before['manifest'] == ordinary(F / '.agents/ac5-20261015/TRANSFER-MANIFEST.json')
prior_conservation = read(PRIOR / 'CONSERVATION-r1.json')
assert {name: after_tool[name] for name in prior_conservation['tool_tree']} == prior_conservation['tool_tree']
assert set(after_tool) - set(prior_conservation['tool_tree']) == {'run_one_approved_attempt_v2.py'}
assert not (R / 'ONE-ATTEMPT-STARTED.json').exists() and not list(R.glob('profile-qualification-*'))
old_wrapper = R / 'run_one_approved_attempt.py'
wrapper = R / 'run_one_approved_attempt_v2.py'
assert sha(old_wrapper) == '282658ad35faa4e9c51bf5ebdf232633e66b94f9ed61a948f781422cd9a2664e'
assert sha(wrapper) == '372a14a567ddecc4ccb67848669afe641d71ebc7b1d66aaad4dcaa0b5b709570'
old_body = old_wrapper.read_text(encoding='utf8')
expected = old_body.replace("assert sha(review) == review_sha\nreviewed = json.loads(review.read_text())\nassert reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool)\n", '')
needle = "module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)\n"
assert expected.count(needle) == 1
expected = expected.replace(needle, needle + "review_payload, review_identity = module.capture(review, review_sha)\nreviewed = json.loads(review_payload.decode('utf-8-sig'))\nassert reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool)\n")
expected = expected.replace("'tool_sha256': sha(tool), 'review_sha256': review_sha, 'profile_before': profile,", "'tool_sha256': sha(tool), 'review_sha256': review_sha, 'review_native_identity': review_identity,\n    'review_verified_and_decoded_payload_identical': True, 'profile_before': profile,")
assert ast.dump(ast.parse(expected), include_attributes=False) == ast.dump(ast.parse(wrapper.read_text()), include_attributes=False)
changed_case = next(row for row in result['wrapper_facts'] if row['label'] == 'review-between-reads')
assert changed_case['initial_review_sha256'] != changed_case['review_after_sha256']
assert changed_case['changed_review_sha256'] == changed_case['review_after_sha256']
assert changed_case['captured_review_facts'][0]['captured_sha256'] == changed_case['initial_review_sha256']
assert changed_case['exception_type'] == 'AssertionError' and changed_case['calls'] == []
assert not changed_case['marker_exists'] and not changed_case['approval_file_exists']
nonzero = next(row for row in result['wrapper_facts'] if row['label'] == 'nonzero-child')
marker = read(Path(nonzero['directory']) / 'ONE-ATTEMPT-STARTED.json')
assert marker['review_verified_and_decoded_payload_identical'] is True
assert marker['review_native_identity'] == nonzero['captured_review_facts'][0]['identity']
assert marker['review_sha256'] == nonzero['initial_review_sha256']
build_path = F / '.agents/runtime/ac1-20261014/build-r2/build.json'
build = read(build_path); build_facts = {}
for name in ('source', 'actual_rustc', 'resolved_rustup_command_image', 'native_image'):
    fact = build[name]; current = ordinary(Path(fact['path']))
    assert current['sha256'] == fact['sha256'] and current['native_identity'] == fact['native_identity']
    assert current == prior_conservation['observed_build_bindings'][name]
    build_facts[name] = current
assert ordinary(F / '.agents/ac5-20261015/native/windows_broker/isolated_worker.rs')['sha256'] == build['source']['sha256']
python_image = ordinary(Path(sys.executable))
assert python_image['sha256'] == '0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14'
strict_path = F / '.agents/runtime/ac5-20261015/independent-root-review/review.json'
persisted_path = F / '.agents/runtime/ac5-20261015/ac5-20261015/receipts/review.json'
strict, persisted = read(strict_path), read(persisted_path)
state_path = F / '.agents/runtime/ac5-20261015/ac5-20261015/state.json'
state = read(state_path)
assert len(strict) == 13 and len(persisted) == 16 and {key: persisted[key] for key in strict} == strict
assert strict['decision'] == 'approved' and strict['exit_status'] == 0
assert sha(strict_path) == '70c0000c1c149acc8ffa5878f84e1bd60b5f7bbd5f0e95e6d4e16bacd91f0a6c'
assert state['nodes']['review']['state'] == 'SUCCEEDED' and state['sequence'] == 9
assert read(F / '.agents/runtime/ac5-20261015/ac5-20261015/claims.json') == {}
write(D / 'CONSERVATION.json', {'at': utc(), 'source': after_source, 'candidate': after_candidate,
    'tool_tree': after_tool, 'dependencies': after_dependencies, 'originals': after_originals, 'git': git,
    'prior_seal': ordinary(PRIOR / 'SEAL-r1.json'), 'prior_sealed_member_count': len(prior_seal['members']),
    'all_prior_sealed_members_native_and_hash_exact': True,
    'build_record': ordinary(build_path), 'observed_build_bindings': build_facts, 'python': python_image,
    'candidate_review': {'strict': ordinary(strict_path), 'persisted': ordinary(persisted_path),
        'strict_fields': 13, 'persisted_fields': 16, 'normalized_equality': True,
        'state': ordinary(state_path), 'state_review': 'SUCCEEDED', 'sequence': 9, 'claims': {}},
    'old_wrapper_retained': True, 'tool_root_attempt_marker_absent': True,
    'tool_root_qualification_directories_absent': True})
report = {'schema': 'ceta-operator-tool-independent-review-v2', 'at': utc(),
    'reviewer': '/root/history_preservation', 'decision': 'approved', 'exit_status': 0,
    'source_root': str(F), 'tool_root': str(R),
    'tool_sha256': '530238cbb5d5601802e96864a085a4d4becb0d0d045e3bf13286b5718b7d9a6e',
    'wrapper_sha256': sha(wrapper), 'wrapper_path': str(wrapper),
    'proposal_sha256': '320b5dcc8bb807fad97b46a34faf8be25ed55423afa5d8e81d977947a02d4163',
    'candidate_manifest_sha256': '22263a72a8208e4024b94088ba95cf651846f542c44fa6fe44a68957eb29aa3e',
    'scope': 'Exact frozen AC5 operator tool/proposal plus separately named v2 one-attempt wrapper; engineering preparation only',
    'tests': {'executed': 49, 'passed': 49, 'failed': 0, 'errors': 0, 'skips': 0,
        'original_negative_methods': 30, 'controlled_variants': 18, 'original_serialization_methods': 6,
        'extra_snapshot_and_support_methods': 3, 'wrapper_methods': 10,
        'exact_expected_executed_stopped_ids': True, 'R1_method_IDs_exact': True,
        'reviewer_owned13method_ASTs_exact': True, 'other36methods_loaded_from_exact_original_inputs': True},
    'closed_finding': {'id': 'AC5-TOOL-R20-F01', 'disposition': 'closed_in_exact_v2_wrapper_only',
        'old_wrapper_disposition': 'rejected_and_unchanged', 'literal_hostile_method_unchanged': True,
        'stimulus_relocation': 'V2 no longer reads review.read_text. Fixture now changes ONLY own on-disk review after actual frozen module.capture returns; the same rejected bytes used for the verified digest are decoded and deny before approval, marker or simulated invocation.',
        'changed_on_disk_review_sha256': changed_case['review_after_sha256'],
        'captured_rejected_review_sha256': changed_case['initial_review_sha256'], 'calls': changed_case['calls']},
    'verified_findings': [
        'V2 differs only by one native-bracketed review payload capture/decode and marker identity/identical-payload fields; exact expected successor AST checked.',
        'Old custody/creation/delete/operator-record-validator ASTs retain the previously verified exact tool behavior.',
        'All49 methods pass on exact frozen input bytes with no errors/skips and no forbidden native call.',
        'Captured defining support globals and shim bind exact AC5 Q and owned evidence child.',
        'Rejected or malformed diagnostics preserve primary and rejected status; false/zero/native SID values reach primary/failure snapshot JSON.',
        'Wrong hash/rejected review/existing marker/existing directory/invalid approval/present profile/wrong Source count all deny.',
        'Simulated spawn failure preserves the marker with no retry; simulated nonzero exit and raw streams are retained.',
        'Synthetic successful-preflight marker binds exact capture identity and verified/decoded-identical declaration.',
        'All290 Source payloads/295 candidate payloads/all228 frozen tool-root members/native dependency bindings and tracked dirty Git state conserved.',
        'All prior R1 sealed members, rejected wrapper and failed raw result retained exactly.',
        'AC5 Root component review is actual SUCCEEDED/9/claims{} with strict13/persisted16 equality.'],
    'remaining_issues': [{'classification': 'requires_user_decision',
        'issue': 'A new exact actual human approval is still required before any profile attempt; this engineering review supplies no approval.'},
        {'classification': 'requires_separate_followup_work',
        'issue': 'Positive native isolation remains unqualified. This review performs no profile, worker or native CPU effect.'}],
    'trust_and_measurement_limits': ['Same host, separate reviewer actor; no external attestation',
        'Wrapper loader/approval/profile/child controls are simulated and labelled; actual capture uses the pinned native reader',
        'No actual human approval or tool-root attempt marker created',
        'No real native profile/process operations, Source publication, CETA authority or isolation qualification',
        'Trusted operator preserves approval origin; a JSON source label alone is not native authentication',
        'Wrapper does not introduce a hard wall-clock timeout for arbitrary filesystem/host stalls; test scope verifies finite guarded control flow and retained one-attempt marker'],
    'authorship': {'reviewer_authored_CPB1': True, 'CPB1_in_this_tool': False,
        'reviewer_authored_earlier_AC1_dependency': True,
        'component_authority': 'Root distinct AC5 accepted component review; this review is operator delta/publication fidelity, not self-approval of historical component'},
    'prior_failure': {'report': str(PRIOR / 'review-r1.json'), 'report_sha256': sha(PRIOR / 'review-r1.json'),
        'result_sha256': sha(PRIOR / 'RESULT-r1.json'), 'raw_exit_status': 1,
        'tests': {'executed': 49, 'passed': 48, 'failed': 1}, 'seal_sha256': sha(PRIOR / 'SEAL-r1.json')},
    'evidence': {'harness_binding_sha256': sha(D / 'HARNESS-BINDING.json'),
        'result_sha256': sha(D / 'RESULT-r1.json'), 'raw_sha256': sha(D / 'independent-r1.txt'),
        'before_sha256': sha(D / 'BEFORE.json'), 'conservation_sha256': sha(D / 'CONSERVATION.json')},
    'commands': [{'command': str(sys.executable)+' -B -X utf8 '+str(D / 'prepare_review2.py'), 'exit_status': 0},
        {'command': str(sys.executable)+' -B -X utf8 '+str(D / 'run_independent.py'), 'exit_status': 0}],
    'lifecycle': 'Operator preparation workflow; no product TAAR node or acceptance invented',
    'scope_released': True}
write(D / 'review.json', report)
members = {p.relative_to(D).as_posix(): ordinary(p) for p in D.rglob('*') if p.is_file()}
write(D / 'SEAL.json', {'at': utc(), 'scope': str(D), 'decision': 'approved',
    'tool_sha256': report['tool_sha256'], 'wrapper_sha256': report['wrapper_sha256'],
    'members': members, 'self_excluded': ['SEAL.json'], 'native_operations': [], 'Source_changed': False})
assert read(D / 'review.json')['decision'] == 'approved'
assert read(D / 'review.json')['tool_sha256'] == report['tool_sha256']
assert read(D / 'review.json')['wrapper_sha256'] == report['wrapper_sha256']
print(json.dumps({'decision': 'approved', 'review_sha256': sha(D / 'review.json'),
    'seal_sha256': sha(D / 'SEAL.json'), 'tests_passed': 49, 'Source': len(after_source),
    'candidate': len(after_candidate), 'prior_sealed_members_retained': len(prior_seal['members'])}), flush=True)
