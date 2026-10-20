"""Seal the exact rejected wrapper review without touching the prepared tool."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, stat, sys
F = Path('T:/00-Active/Project-AI-CETA')
D = Path(__file__).resolve().parent
R = F / '.agents/runtime/ac5-profile-tool-20261015'
assert D == F / '.agents/runtime/ac5-profile-tool-review-20261015'
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
spec = importlib.util.spec_from_file_location('review_seal_native_reader', reader)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)
def ordinary(path):
    path = fs.safe_components(Path(path)); info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    native = fs.file_identity(info); size, digest, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == native and size == native['bytes']
    return {'sha256': digest, 'native_identity': native}
before, result = read(D / 'BEFORE.json'), read(D / 'RESULT-r1.json')
assert result['tests_run'] == 49 and len(result['failures']) == 1 and not result['errors'] and not result['skips']
failure = result['failures'][0]
assert failure['id'] == '__main__.WrapperNegativeTests.test_review_hash_checked_bytes_must_be_the_decoded_review'
assert result['exit_status'] == 1 and not result['forbidden_calls']
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
assert not (R / 'ONE-ATTEMPT-STARTED.json').exists() and not list(R.glob('profile-qualification-*'))
build_path = F / '.agents/runtime/ac1-20261014/build-r2/build.json'
build = read(build_path)
build_facts = {}
for name in ('source', 'actual_rustc', 'resolved_rustup_command_image', 'native_image'):
    fact = build[name]; current = ordinary(Path(fact['path']))
    assert current['sha256'] == fact['sha256'] and current['native_identity'] == fact['native_identity']
    build_facts[name] = current
assert ordinary(F / '.agents/ac5-20261015/native/windows_broker/isolated_worker.rs')['sha256'] == build['source']['sha256']
strict_path = F / '.agents/runtime/ac5-20261015/independent-root-review/review.json'
persisted_path = F / '.agents/runtime/ac5-20261015/ac5-20261015/receipts/review.json'
strict, persisted = read(strict_path), read(persisted_path)
state_path = F / '.agents/runtime/ac5-20261015/ac5-20261015/state.json'
state = read(state_path)
assert len(strict) == 13 and len(persisted) == 16
assert {key: persisted[key] for key in strict} == strict
assert strict['decision'] == 'approved' and strict['exit_status'] == 0
assert sha(strict_path) == '70c0000c1c149acc8ffa5878f84e1bd60b5f7bbd5f0e95e6d4e16bacd91f0a6c'
assert state['nodes']['review']['state'] == 'SUCCEEDED' and state['nodes']['review']['decision'] == 'approved' and state['sequence'] == 9
assert read(F / '.agents/runtime/ac5-20261015/ac5-20261015/claims.json') == {}
write(D / 'CONSERVATION-r1.json', {'at': utc(), 'source': after_source, 'candidate': after_candidate,
    'tool_tree': after_tool, 'dependencies': after_dependencies, 'originals': after_originals,
    'git': git, 'build_record': ordinary(build_path), 'observed_build_bindings': build_facts,
    'build_executed_by_reviewer': False, 'candidate_native_source_matches_build_record': True,
    'candidate_review': {'strict': ordinary(strict_path), 'persisted': ordinary(persisted_path),
        'strict_fields': 13, 'persisted_fields': 16, 'normalized_equality': True,
        'state': ordinary(state_path), 'state_review': 'SUCCEEDED', 'sequence': 9, 'claims': {}},
    'tool_root_attempt_marker_absent': True, 'tool_root_qualification_directories_absent': True})
finding = {'id': 'AC5-TOOL-R20-F01', 'classification': 'blocking_current_wrapper_approval',
    'path': str(R / 'run_one_approved_attempt.py'), 'lines': [14,15],
    'verified': 'The wrapper hashes review.read_bytes(), then separately reads review.read_text() for JSON. A controlled replacement between reads lets a checked rejected review become approved decoded data and reach the simulated invocation.',
    'reproduction': {'harness': str(D / 'run_independent.py'), 'harness_sha256': sha(D / 'run_independent.py'),
        'test_id': failure['id'], 'result_sha256': sha(D / 'RESULT-r1.json'),
        'control_case': next(row for row in result['wrapper_facts'] if row['label'] == 'review-between-reads')},
    'limits': 'Own ordinary fixture file was changed at the read boundary under a controlled callback. Approval validation, profile observation and subprocess were simulated. No real approval, child, profile or tool-root marker was created; no production bypass is claimed.',
    'repair': 'Capture the review payload once, verify that exact payload digest, then JSON-decode the same bytes. Retain ordinary-file/native identity qualification where applicable. Preserve the frozen old wrapper and failing receipt.'}
report = {'schema': 'ceta-operator-tool-independent-review-v1', 'at': utc(),
    'reviewer': '/root/history_preservation', 'decision': 'rejected', 'exit_status': 1,
    'tool_sha256': result['tool_sha256'], 'wrapper_sha256': result['wrapper_sha256'],
    'proposal_sha256': sha(R / 'PROFILE-CREATION-PROPOSAL-AC5.json'),
    'candidate_manifest_sha256': '22263a72a8208e4024b94088ba95cf651846f542c44fa6fe44a68957eb29aa3e',
    'tool_delta_disposition': 'approved_scoped_no_blocker_found', 'wrapper_disposition': 'rejected',
    'tests': {'executed': 49, 'passed': 48, 'failed': 1, 'errors': 0, 'skips': 0,
        'original_negative_methods': 30, 'controlled_variants': 18, 'original_serialization_methods': 6,
        'extra_snapshot_and_support_methods': 3, 'wrapper_methods': 10,
        'exact_expected_executed_stopped_ids': True},
    'verified_findings': [finding],
    'verified_passes': [
        'All existing custody/delete/creation/operator-record validator ASTs exact; only snapshot count key changes within the custody class.',
        'Original30 negative methods/18 controlled variants pass with native profile and process creation blocked.',
        'Six serialization cases and three extra snapshot/support binding checks pass, including false/zero retention, BaseException storage and rejected-only status.',
        'Captured support defining globals and shim both use exact AC5 Q and owned evidence child.',
        'Wrong review hash/rejected review/preexisting marker/preexisting qualification directory/invalid approval/present profile/wrong Source count deny before simulated invocation.',
        'Simulated spawn failure leaves the no-overwrite marker, and simulated nonzero child exit/raw output are preserved.',
        'All290 Source and295 candidate payloads, exact manifest, original prepared-tool tree, dependency/native pins and selected historical artifacts remain exact.',
        'Current native source/image/compiler/rustup bytes and identities match the historical build record; no build executed.',
        'AC5 Root strict13/persisted16 review equality, actual reviewSUCCEEDED/9/claims{} observed.',
        'Tracked dirty work/Git identity preserved; actual tool-root marker and qualification directory remain absent.'],
    'reasonable_hypotheses': [],
    'unresolved_questions': ['Positive native isolation remains unqualified; this review performs no profile or worker operation.'],
    'authority_limits': ['No genuine operator approval created or consumed', 'No Source publication or canonical authority grant',
        'No actual native Create/Delete profile or process launch', 'Same-host separate actor; host administrator outside test threat model',
        'Diagnostic values remain rejected observation data, not token qualification/authentication'],
    'authorship': {'reviewer_authored_CPB1': True, 'CPB1_in_this_tool': False,
        'reviewer_authored_earlier_AC1_dependency': True,
        'scope': 'AC5 operator delta and wrapper; component approval is Root separate accepted AC5 review, no self-approval of historical component'},
    'evidence': {'before_sha256': sha(D / 'BEFORE.json'), 'result_sha256': sha(D / 'RESULT-r1.json'),
        'raw_sha256': sha(D / 'independent-r1.txt'), 'conservation_sha256': sha(D / 'CONSERVATION-r1.json')},
    'commands': [{'command': str(sys.executable)+' -B -X utf8 '+str(D / 'run_independent.py'), 'exit_status': 1}],
    'reviewer_read_diagnostic': 'Initial Get-Content used nonexistent ISOLATION-PROFILE-PROPOSAL.json; corrected to exact PROFILE-CREATION-PROPOSAL-AC5.json before tests. This was a reviewer path error, not a product failure.',
    'lifecycle': 'Operator preparation workflow; no invented product TAAR transition'}
write(D / 'review-r1.json', report)
members = {p.relative_to(D).as_posix(): ordinary(p) for p in D.rglob('*') if p.is_file()}
write(D / 'SEAL-r1.json', {'at': utc(), 'scope': str(D), 'decision': 'rejected',
    'members': members, 'self_excluded': ['SEAL-r1.json'], 'native_operations': [], 'Source_changed': False})
print(json.dumps({'decision': 'rejected', 'review_sha256': sha(D / 'review-r1.json'),
    'seal_sha256': sha(D / 'SEAL-r1.json'), 'source': len(after_source), 'candidate': len(after_candidate),
    'prepared_tool_members_retained': len(after_tool)}), flush=True)
