"""One operator-approved invocation; this script never creates an approval."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys
F = Path('T:/00-Active/Project-AI-CETA'); R = Path(__file__).resolve().parent
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert R == F / '.agents/runtime/ac5-profile-tool-20261015' and Path(sys.executable) == PY and not sys.flags.optimize
assert len(sys.argv) == 5, 'ACTUAL_APPROVAL_PATH_HASH_AND_REVIEW_PATH_HASH_REQUIRED'
approval, approval_sha, review, review_sha = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4]
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
tool = R / 'profile_qualification.py'
assert sha(tool) == '530238cbb5d5601802e96864a085a4d4becb0d0d045e3bf13286b5718b7d9a6e'
assert sha(R / 'PROFILE-CREATION-PROPOSAL-AC5.json') == '320b5dcc8bb807fad97b46a34faf8be25ed55423afa5d8e81d977947a02d4163'
assert sha(review) == review_sha
reviewed = json.loads(review.read_text())
assert reviewed['decision'] == 'approved' and reviewed['tool_sha256'] == sha(tool)
assert not (R / 'ONE-ATTEMPT-STARTED.json').exists(), 'PRIOR_ATTEMPT_MARKER_REFUSED'
assert not list(R.glob('profile-qualification-*')), 'PRIOR_QUALIFICATION_DIRECTORY_REFUSED'
spec = importlib.util.spec_from_file_location('ac5_single_attempt_preflight', tool)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
module.validate_operator_record(approval, approval_sha)
profile = module.inspect()
assert profile['prior_folder']['HRESULT'] in (-2147024894, -2147024893) and profile['prior_folder']['path'] is None
source, candidate = module.source_cut(), module.candidate_cut()
assert len(source) == 290 and len(candidate) == 295
module.save(R / 'ONE-ATTEMPT-STARTED.json', {'at': module.now(), 'actual_approval_sha256': approval_sha,
    'tool_sha256': sha(tool), 'review_sha256': review_sha, 'profile_before': profile,
    'Source290': source, 'candidate295': candidate, 'automatic_retry': False})
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
