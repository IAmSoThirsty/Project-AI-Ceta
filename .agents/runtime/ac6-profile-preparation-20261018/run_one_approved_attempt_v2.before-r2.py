"""One operator-approved invocation; this script never creates an approval."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys
F = Path('T:/00-Active/Project-AI-CETA'); R = Path(__file__).resolve().parent
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert R == F / '.agents/runtime/ac6-profile-preparation-20261018' and Path(sys.executable) == PY and not sys.flags.optimize
assert len(sys.argv) == 5, 'ACTUAL_APPROVAL_PATH_HASH_AND_REVIEW_PATH_HASH_REQUIRED'
approval, approval_sha, review, review_sha = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4]
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
tool = R / 'profile_qualification.py'
assert sha(tool) == 'b4239905c91ebeb03026771627b708f9bbd2adfbeeb796e4296b7b12b78c60c3'
assert sha(R / 'PROFILE-CREATION-PROPOSAL-AC6.json') == 'aa849834a68cd670928ea8f17dc446a50354442b2dbd658ed8889c0cdc982f49'
assert not (R / 'ONE-ATTEMPT-STARTED.json').exists(), 'PRIOR_ATTEMPT_MARKER_REFUSED'
assert not list(R.glob('q-*')), 'PRIOR_QUALIFICATION_DIRECTORY_REFUSED'
spec = importlib.util.spec_from_file_location('ac6_single_attempt_preflight', tool)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
review_payload, review_identity = module.capture(review, review_sha)
reviewed = json.loads(review_payload.decode('utf-8-sig'))
assert reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool)
module.validate_operator_record(approval, approval_sha)
profile = module.inspect()
assert profile['prior_folder']['HRESULT'] in (-2147024894, -2147024893) and profile['prior_folder']['path'] is None
source, candidate = module.source_cut(), module.candidate_cut()
assert len(source) == 352 and len(candidate) == 352
module.save(R / 'ONE-ATTEMPT-STARTED.json', {'at': module.now(), 'actual_approval_sha256': approval_sha,
    'tool_sha256': sha(tool), 'review_sha256': review_sha, 'review_native_identity': review_identity,
    'review_verified_and_decoded_payload_identical': True, 'profile_before': profile,
    'Source352': source, 'execution_source352': candidate, 'automatic_retry': False})
argv = [str(PY), '-B', '-X', 'utf8', str(tool), '--mode', 'qualify',
    '--approval-receipt', str(approval), '--approval-sha256', approval_sha]
started = module.now()
done = subprocess.run(argv, cwd=F, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
for label, raw in (('stdout', done.stdout), ('stderr', done.stderr)):
    with (R / ('APPROVED-QUALIFICATION.' + label)).open('xb') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
module.save(R / 'APPROVED-QUALIFICATION.json', {'started_at': started, 'finished_at': module.now(),
    'command_argv': argv, 'exit_status': done.returncode, 'actual_approval_sha256': approval_sha,
    'tool_sha256': sha(tool), 'review_sha256': review_sha, 'automatic_retry': False,
    'stdout_sha256': sha(R / 'APPROVED-QUALIFICATION.stdout'), 'stderr_sha256': sha(R / 'APPROVED-QUALIFICATION.stderr')})
print(json.dumps({'exit_status': done.returncode, 'automatic_retry': False}), flush=True)
print(done.stdout.decode('utf-8-sig'), flush=True)
if done.stderr: print(done.stderr.decode('utf-8-sig'), file=sys.stderr, flush=True)
sys.exit(done.returncode)
