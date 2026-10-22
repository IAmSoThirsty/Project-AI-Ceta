"""One exact reviewed descendant publication; ordinary pre-push hook retained."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import urllib.request
from urllib.parse import quote
import prepare_checkpoint as engine
from prepare_checkpoint import batch_blobs, checkout_state, digest, git, save, stable_read
import exact_git_scope  # Add the already declared installed TAAR dependency path.
from taar.orchestration_graph import path_matches_scope
from taar.orchestration_runtime import _snapshot_workspace
from taar.orchestration_runtime import OrchestrationRuntime

W = Path(__file__).resolve().parent
P = W.parent
F = Path('T:/00-Active/Project-AI-CETA')
CONTROL = P / 'publication-control'
RUN = 'ceta-checkpoint-0008-publication-20261022'
sequence = 0


def refs():
    return dict(row.split(' ', 1) for row in git(F, ['for-each-ref', '--format=%(refname) %(objectname)']).decode().splitlines())


def audit_command(args, completed):
    global sequence
    if any(word in args for word in ('index-pack', 'update-ref', 'push', 'ls-remote')):
        sequence += 1
        save(CONTROL / ('publication-command-%03d.json' % sequence), dict(at=datetime.now(timezone.utc).isoformat(),
            argv=completed.args, exit_status=completed.returncode,
            stdout=completed.stdout.decode('utf-8', errors='replace'), stderr=completed.stderr.decode('utf-8', errors='replace')))


def require_current_claim(spec, expected=None):
    verified = OrchestrationRuntime(CONTROL).verify(RUN)
    assert verified['allowed'] and verified['receipts_valid'] and verified['states']['integrate'] == 'RUNNING'
    state = json.loads((CONTROL / RUN / 'state.json').read_bytes())
    claims = json.loads((CONTROL / RUN / 'claims.json').read_bytes())
    assert state['run_id'] == RUN and Path(state['scope']).resolve() == CONTROL.resolve()
    claim = claims['integrate']; current = state['nodes']['integrate']
    assert current['state'] == 'RUNNING' and current['claim'] == claim
    assert claim['executor_id'] == '/root' and claim['node_id'] == 'integrate'
    assert Path(claim['workspace']).resolve() == F / '.git'
    assert current['effective_write_scope'] == claim['effective_write_scope'] == spec['git_scope']
    assert claim['input_hash'] and (expected is None or claim == expected)
    assert state['nodes']['review']['state'] == 'SUCCEEDED' and state['nodes']['review']['decision'] == 'approved'
    assert state['nodes']['validate']['state'] == 'SUCCEEDED' and state['nodes']['validate']['validation_passed'] is True
    return claim


def main():
    spec = json.loads((P / 'publication-packet/INPUTS.json').read_bytes())
    assert spec['run_id'] == RUN
    assert digest((W / 'WORK-FREEZE.json').read_bytes()) == spec['work_freeze_sha256']
    from verify_prepared import audit
    audit()
    prepared_path = W / 'prepared-0002/PREPARED.json'
    p = json.loads(prepared_path.read_bytes())
    assert digest(prepared_path.read_bytes()) == spec['prepared_sha256']
    claim = require_current_claim(spec)
    pack = next(Path(n) for n in p['pack_files'] if n.endswith('.pack'))
    pack_id = pack.stem.removeprefix('checkpoint-')
    assert len(pack_id) == 40 and all(c in '0123456789abcdef' for c in pack_id)
    expected_destinations = [F / '.git/objects/pack' / ('pack-' + pack_id + '.' + suffix) for suffix in ('pack','idx','rev')]
    assert all(path.relative_to(Path('T:/')).as_posix() in claim['effective_write_scope'] for path in expected_destinations)
    assert all(not path.exists() for path in expected_destinations), 'New-object destinations already exist'
    assert digest(pack.read_bytes()) == p['pack_files'][str(pack)]
    assert checkout_state(F) == p['checkout_before']
    before_refs = refs(); target = p['ref']; tracking = 'refs/remotes/origin/development/checkpoints'
    assert before_refs[target] == before_refs[tracking] == p['parent']
    engine.COMMAND_AUDITOR = audit_command
    assert git(F, ['ls-remote', '--refs', 'origin', target]).decode().splitlines() == [p['parent'] + '\t' + target]
    hook = F / '.git/hooks/pre-push'
    hook_path = git(F, ['config', '--get', 'core.hooksPath'], allowed=(0, 1)).decode().strip()
    assert not hook_path or Path(hook_path).resolve() == hook.parent.resolve()
    assert digest(stable_read(hook)[0]) == spec['pre_push_hook_sha256']
    assert b'git lfs pre-push' in hook.read_bytes()
    result = dict(commit=p['commit'], ref=target, parent=p['parent'], push_succeeded=False,
        anonymous_readback=False, full_product_acceptance=False, attempt_count=1)
    # Exclusive marker prevents any publisher replay, even after a partial failure.
    save(CONTROL / 'INTEGRATION-START.json', dict(at=datetime.now(timezone.utc).isoformat(),
        prepared_sha256=spec['prepared_sha256'], claim_input_hash=claim['input_hash'], git_scope=claim['effective_write_scope'],
        checkout_before=p['checkout_before'], refs_before=before_refs, instruction=spec['instruction'], normal_pre_push_hook=True))
    primary = None
    require_current_claim(spec, claim)
    try:
        assert digest(pack.read_bytes()) == p['pack_files'][str(pack)]
        result['index_pack_stdout'] = git(F, ['index-pack', '--stdin'], data=pack.read_bytes()).decode('ascii')
        entries = {}
        for item in git(F, ['ls-tree', '-r', '-z', p['tree']]).split(b'\0'):
            if item:
                header, name = item.split(b'\t', 1); entries[name.decode()] = header.decode().split()[2]
        names = list(p['exports'])
        for name, blob in zip(names, batch_blobs(F, [entries[n] for n in names], {}), strict=True):
            assert digest(blob) == p['exports'][name]['sha256']
        git(F, ['merge-base', '--is-ancestor', p['parent'], p['commit']])
        git(F, ['update-ref', '--create-reflog', '-m', 'CETA reviewed development checkpoint8', target, p['commit'], p['parent']])
        result['local_ref_updated'] = True
        result['push_stdout'] = git(F, ['-c', 'push.followTags=false', '-c', 'remote.origin.mirror=false',
            '-c', 'push.recurseSubmodules=no', 'push', '--porcelain', 'origin', p['commit'] + ':' + target]).decode()
        result['push_succeeded'] = True
        remote = git(F, ['ls-remote', '--refs', 'origin', target]).decode().splitlines()
        assert remote == [p['commit'] + '\t' + target]
        result['remote_readback'] = remote
        samples = []
        for name in ('DEVELOPMENT-CHECKPOINT.json',
            'handoff/development-checkpoints/20261022-0008/candidate/src/ceta/store/journal.py',
            'handoff/development-checkpoints/20261022-0008/candidate/tests/contract/test_journal_read_budget.py'):
            url = 'https://raw.githubusercontent.com/IAmSoThirsty/Project-AI-Ceta/' + p['commit'] + '/' + quote(name)
            request = urllib.request.Request(url, headers={'User-Agent':'CETA-development-checkpoint-readback'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(8_000_001)
                assert len(raw) <= 8_000_000 and digest(raw) == p['exports'][name]['sha256']
                samples.append(dict(path=name, url=url, status=response.status, bytes=len(raw), sha256=digest(raw)))
        result['anonymous_samples'] = samples
        result['anonymous_readback'] = True
    except BaseException as exc:
        primary = exc
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
    try:
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        result['checkout_after'] = checkout_state(F)
        result['normal_checkout_index_unchanged'] = result['checkout_after'] == p['checkout_before']
        canonical = json.loads((W / 'CANONICAL-BEFORE.json').read_bytes())
        result['canonical_source_native_pins_unchanged'] = all(stable_read(F / n)[1] == pin for n,pin in canonical['canonical_pins'].items())
        result['normal_index_native_unchanged'] = stable_read(F / '.git/index')[1] == canonical['normal_index_native']
        after_refs = refs(); result['refs_after'] = after_refs
        result['unrelated_refs_unchanged'] = all(before_refs.get(n) == after_refs.get(n)
            for n in set(before_refs) | set(after_refs) if n not in (target, tracking))
        after = _snapshot_workspace(F / '.git', Path('T:/'))
        baseline = claim['baseline_snapshot']
        changed = sorted(n for n in set(after) | set(baseline) if after.get(n) != baseline.get(n))
        result['observed_changed_git_paths'] = changed
        result['outside_exact_scope'] = [n for n in changed if not any(path_matches_scope(n, scope) for scope in spec['git_scope'])]
        object_prefix = '00-Active/Project-AI-CETA/.git/objects/'
        result['existing_objects_unchanged'] = all(after.get(n) == pin for n,pin in baseline.items() if n.startswith(object_prefix))
        result['remaining_locks'] = [n for n in after if n.endswith('.lock') and n not in baseline]
        result['git_snapshot_after'] = after
        assert not result['outside_exact_scope'] and result['existing_objects_unchanged'] and not result['remaining_locks']
        assert result['normal_checkout_index_unchanged'] and result['canonical_source_native_pins_unchanged']
        assert result['normal_index_native_unchanged'] and result['unrelated_refs_unchanged']
    except BaseException as exc:
        result['postcheck_error'] = dict(type=type(exc).__name__, message=str(exc))
        if primary is None: primary = exc
        else:
            try: primary.checkpoint_postcheck_error = exc
            except BaseException: pass
    try:
        save(CONTROL / 'INTEGRATION-RESULT.json', result)
    except BaseException as persistence_error:
        if primary is None: raise
        try: primary.checkpoint_result_persistence_error = persistence_error
        except BaseException as attachment_error:
            raise primary from BaseExceptionGroup('Checkpoint evidence persistence and attachment failed', [persistence_error, attachment_error])
    if primary is not None: raise primary
    assert result['push_succeeded'] and result['anonymous_readback']
    print(json.dumps({k:v for k,v in result.items() if k != 'git_snapshot_after'}, indent=2))


if __name__ == '__main__': main()
