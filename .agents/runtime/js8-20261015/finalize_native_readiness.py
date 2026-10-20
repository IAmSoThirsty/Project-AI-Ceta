"""Execute input preparation only; no engineering release or native attempt."""
from foundation_support import *
import ast
import subprocess

N = R / 'native-readiness'
ORIGIN = F / '.agents/runtime/fn6-20261015/native-readiness'
assert not (N / 'PREPARATION-COMMAND.json').exists()
argv = [str(PY), '-B', '-X', 'utf8', str(N / 'prepare_inputs.py')]
done = subprocess.run(argv, cwd='T:/00-Active', capture_output=True)
for name, value in (('prepare-inputs.stdout', done.stdout), ('prepare-inputs.stderr', done.stderr)):
    fs.write_new(N / name, value)
write_new(N / 'PREPARATION-COMMAND.json', dict(at=utc(), argv=argv, cwd='T:/00-Active',
    exit_status=done.returncode, stdout=reference(N / 'prepare-inputs.stdout'),
    stderr=reference(N / 'prepare-inputs.stderr'), native_or_test_execution=False))
assert done.returncode == 0, done.stderr.decode('utf8', 'replace')
sys.path.insert(0, str(N))
import readiness_support as n
prepared, prepared_facts = n.preflight()
subject = n.pinned_json(N / 'SOURCE-SUBJECT.json', n.MANIFEST_PIN)[0]
assert n.payload_snapshot(subject) == prepared['candidate352']
assert n.method_asts((Q / 'tests/contract/test_cpu_execution_admission.py').read_bytes()) == prepared['original_method_ast_sha256']
assert (Q / 'tests/contract/test_cpu_execution_admission.py').read_bytes() == (F / '.agents/fn6-20261015/tests/contract/test_cpu_execution_admission.py').read_bytes()
assert (N / 'resource_witness.py').read_bytes() == (ORIGIN / 'resource_witness.py').read_bytes()
assert (N / 'supervise_native.py').read_bytes() == (ORIGIN / 'supervise_native.py').read_bytes()
assert (N / 'bounded_custody.py').read_bytes() == (ORIGIN / 'bounded_custody.py').read_bytes()
for name in n.SCRIPTS:
    ast.parse((N / name).read_bytes())
assert not any(name == 'ceta' or name.startswith('ceta.') for name in sys.modules)
assert not (N / 'ROOT-REVIEW.json').exists() and not (N / 'ROOT-NATIVE-RELEASE.json').exists()
assert not (N / 'ONE-ATTEMPT.json').exists()
assert not Path(prepared['fixture_root']).exists()
readback = dict(at=utc(), source_subject=reference(N / 'SOURCE-SUBJECT.json'),
    inputs=reference(N / 'PREPARED-INPUTS.json'), scripts={name:prepared['scripts'][name]['sha256'] for name in n.SCRIPTS},
    payload_count=len(prepared['candidate352']), environment_files=len(prepared['environment']),
    component_proof_count=len(prepared['proofs']), original_seven_method_count=len(prepared['original_method_ast_sha256']),
    original_seven_method_ast_sha256=prepared['original_method_ast_sha256'],
    original_seven_file_byte_exact=True, unchanged_witness_supervision_custody=True,
    parent24_controls='Historical retained proof only; no repeated control campaign',
    preparation_command=reference(N / 'PREPARATION-COMMAND.json'),
    source_subject_semantics='Separately frozen source352; whole JS8 author/review remains pending.',
    current_FN6_component_review='Actual SUCCEEDED9/claims{} authenticated by prepare_inputs',
    Stop_component_review=subject['Stop_component_review'],
    execution='NOT_RUN', profile_Hello='FORBIDDEN', Source_publication=False,
    Root_review_release_attempt_files_absent=True, future_fixture_absent=True,
    required_release_schema=dict(exact_fields=['schema_version','kind','executor','issued_at','expires_at',
        'attempt_id','inputs_sha256','scripts_sha256','candidate_manifest_sha256','test_ids',
        'environment_digest','output_root','child_wait_seconds','allowed_effects','review_path','review_sha256'],
        kind='JS8_SEVEN_NATIVE_ENGINEERING', executor='/root', max_validity_seconds=900,
        source_subject_sha256=n.MANIFEST_PIN, inputs_sha256=prepared_facts['sha256'],
        scripts_sha256={name:row['sha256'] for name,row in prepared['scripts'].items()},
        test_ids=list(n.IDS), environment_digest=n.sha(n.canonical(prepared['environment']).encode('utf8')),
        output_root_pattern=str(N / 'attempt-<32lowerhex>'), child_wait_seconds=n.WAIT_SECONDS,
        allowed_effects=prepared['future_effects'], review_path=str(N / 'ROOT-REVIEW.json')),
    launch_entry_point=dict(executable=str(PY), arguments=['-B','-X','utf8',str(N / 'supervise_native.py')],
        note='Root only, after its exact review and fresh release; no arguments accepted by supervisor.'),
    remaining_limits=prepared['unresolved_prior_custody'], product_LOC_credit=0)
write_new(N / 'PREPARATION-READBACK.json', readback)
members = {p.name:ordinary(p) for p in sorted(N.iterdir()) if p.is_file()}
write_new(N / 'PREPARATION-SEAL.json', dict(at=utc(), author=AUTHOR, members=members,
    own_preparation_scripts={name:reference(R / name) for name in ('prepare_native_readiness.py','finalize_native_readiness.py')},
    immutable_preparation_members=True, future_Root_review_release_attempt_outputs_excluded=True,
    native_execution='NOT_RUN', Source_publication=False))
print(canonical(dict(inputs_sha256=prepared_facts['sha256'], source_subject_sha256=n.MANIFEST_PIN,
    readback_sha256=sha(N / 'PREPARATION-READBACK.json'), seal_sha256=sha(N / 'PREPARATION-SEAL.json'),
    payloads=352, scripts=6, environment_files=len(prepared['environment']), native_execution='NOT_RUN')))
