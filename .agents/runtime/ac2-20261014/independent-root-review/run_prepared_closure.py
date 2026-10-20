"""Resume prepared exact closure oracles after missing historical-reference copy; no oracle edits."""
from ac2_support import *

root = R / 'closure-r1'
baseline = R.parent / 'baseline-reproduction.json'
with (R / 'baseline-reproduction.json').open('xb') as out:
    out.write(baseline.read_bytes())
assert sha(R / 'baseline-reproduction.json') == sha(baseline)
write_new(R / 'closure-helper-failure.json', {'recorded_at': utc(),
    'helper': reference(R / 'prepare_closure.py'),
    'failure': 'Missing copied historical baseline-reproduction.json reference after fresh exact oracle/binary fixture was prepared; no native oracle had executed.',
    'repair': 'Copy exact historical reference without credit and execute already prepared unchanged oracle once.',
    'historical_reference': reference(baseline), 'historical_reference_is_not_current_review_execution': True})
assert sha(root / 'hostile_cleanup.py') == sha(R.parent / 'closure-r4/hostile_cleanup.py')
write_new(root / 'closure-oracle-binding.json', {'recorded_at': utc(),
    'original': reference(PRIOR_R / 'independent-review/hostile_cleanup.py'),
    'adapted': reference(root / 'hostile_cleanup.py'), 'diff': reference(root / 'oracle-adaptation.diff'),
    'identical_to_author_closure_oracle': True, 'historical_baseline': reference(baseline),
    'reviewer': '/root', 'Source_application': False})
done = subprocess.run([str(PY), '-B', '-X', 'utf8', str(root / 'hostile_cleanup.py')],
    cwd=F, capture_output=True, env=dict(os.environ, CETA_AC2_PROBE_ROOT=str(root), PYTHONPATH=str(R)))
for suffix, raw in [('stdout', done.stdout), ('stderr', done.stderr)]:
    with (root / ('root-driver.' + suffix)).open('xb') as out:
        out.write(raw)
print(done.stdout.decode('utf-8'), end='', flush=True)
if done.returncode:
    print(done.stderr.decode('utf-8'), end='', flush=True)
sys.exit(done.returncode)
