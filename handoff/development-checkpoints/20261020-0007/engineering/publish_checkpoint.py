"""Publish the exact reviewed checkpoint under the actual Git-directory lease.

One attempt only. A failed push preserves the local descendant ref and all
evidence; it does not roll back, force, retry or touch the active checkout.
"""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import urllib.request
from urllib.parse import quote
import prepare_checkpoint as engine
from prepare_checkpoint import batch_blobs, checkout_state, digest, git, stable_read, verify

W = Path(__file__).resolve().parent
P = W.parent
F = Path('T:/00-Active/Project-AI-CETA')
s = importlib.util.spec_from_file_location('checkpoint_client', P / 'client.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m); c = m.c
command_sequence = 0


def audit_command(args, completed):
    global command_sequence
    if any(x in args for x in ('index-pack', 'update-ref', 'push', 'ls-remote')):
        command_sequence += 1
        c.save(c.R / f'publication-command-{command_sequence:03}.json', dict(
            at=datetime.now(timezone.utc).isoformat(), argv=completed.args,
            cwd=str(F), exit_status=completed.returncode,
            stdout=completed.stdout.decode('utf-8', errors='replace'),
            stderr=completed.stderr.decode('utf-8', errors='replace')))


def canonical_pins(exports):
    result = {}
    for name in exports:
        path = F / name
        result[name] = stable_read(path)[1] if path.is_file() else None
    return result


def refs():
    return dict(line.decode().split(' ', 1) for line in
                git(F, ['for-each-ref', '--format=%(refname) %(objectname)']).splitlines())


def main():
    prepared_path = W / 'prepared-0001/PREPARED.json'
    prepared_raw = prepared_path.read_bytes(); p = json.loads(prepared_raw)
    before = verify(prepared_path)
    runtime = json.loads((c.R / c.RUN / 'state.json').read_bytes())
    claims = json.loads((c.R / c.RUN / 'claims.json').read_bytes())
    assert claims['integrate']['executor_id'] == '/root'
    assert Path(claims['integrate']['workspace']).resolve() == (F / '.git').resolve()
    assert runtime['nodes']['review']['decision'] == 'approved'
    assert runtime['nodes']['validate']['validation_passed'] is True
    c.invoke('integrate-preflight-verify', ['run', 'verify', c.RUN])
    engine.COMMAND_AUDITOR = audit_command
    # Preconditions are repeated immediately before the first canonical write.
    assert checkout_state(F) == p['checkout_before']
    before_refs = refs(); before_source = canonical_pins(p['exports'])
    target = p['ref']; tracking = 'refs/remotes/origin/development/checkpoints'
    previous = before_refs.get(target)
    assert previous == p['parent'], 'checkpoint ref drift'
    remote = git(F, ['ls-remote', '--refs', 'origin', target]).decode().splitlines()
    assert remote == ([] if previous is None else [f"{previous}\t{target}"]), 'remote checkpoint drift'
    hook = F / '.git/hooks/pre-push'
    assert hook.is_file() and b'git lfs pre-push' in hook.read_bytes(), 'expected pre-push hook missing'
    start = dict(at=datetime.now(timezone.utc).isoformat(), commit=p['commit'], tree=p['tree'],
                 ref=target, parent=p['parent'], prepared_sha256=digest(prepared_raw),
                 checkout_before=p['checkout_before'], canonical_pins=before_source,
                 refs_before=before_refs, pre_push_hook_sha256=digest(hook.read_bytes()),
                 authorized_instruction=json.loads((P / 'packet/INPUTS.json').read_bytes())['instruction'],
                 command=['git', 'push', '--porcelain', 'origin', p['commit'] + ':' + target])
    c.save(c.R / 'INTEGRATION-START.json', start)
    result = dict(attempt_started=True, checkpoint_commit=p['commit'], checkpoint_ref=target,
                  push_succeeded=False, anonymous_readback=False, product_acceptance=False)
    try:
        pack = next(Path(name) for name in p['pack_files'] if name.endswith('.pack'))
        assert digest(pack.read_bytes()) == p['pack_files'][str(pack)]
        imported = git(F, ['index-pack', '--stdin'], data=pack.read_bytes())
        result['index_pack_stdout'] = imported.decode('ascii')
        # Verify using ONLY the canonical object database, without preparation alternates.
        entries = {}
        for item in git(F, ['ls-tree', '-r', '-z', p['tree']]).split(b'\0'):
            if item:
                header, name = item.split(b'\t', 1)
                entries[name.decode()] = header.decode().split()[2]
        names = list(p['exports'])
        for name, raw in zip(names, batch_blobs(F, [entries[x] for x in names], {}), strict=True):
            assert digest(raw) == p['exports'][name]['sha256'], 'canonical Git blob mismatch'
        assert git(F, ['rev-parse', p['commit'] + '^{tree}']).decode().strip() == p['tree']
        git(F, ['merge-base', '--is-ancestor', p['parent'], p['commit']])
        git(F, ['update-ref', '--create-reflog', '-m', 'CETA reviewed development checkpoint',
                target, p['commit'], previous or '0' * 40])
        result['local_ref_updated'] = True
        pushed = git(F, ['-c', 'push.followTags=false', '-c', 'remote.origin.mirror=false',
                         '-c', 'push.recurseSubmodules=no', 'push', '--porcelain', 'origin',
                         p['commit'] + ':' + target])
        result['push_stdout'] = pushed.decode('utf-8', errors='replace')
        result['push_succeeded'] = True
        readback = git(F, ['ls-remote', '--refs', 'origin', target]).decode().splitlines()
        assert readback == [p['commit'] + '\t' + target], 'remote readback mismatch'
        result['remote_readback'] = readback
        samples = []
        for name in ('src/ceta/supervisor/isolated_worker.py',
                     'src/ceta/identity/owner_session.py', 'DEVELOPMENT-CHECKPOINT.json'):
            url = 'https://raw.githubusercontent.com/IAmSoThirsty/Project-AI-Ceta/' + p['commit'] + '/' + quote(name)
            request = urllib.request.Request(url, headers={'User-Agent':'CETA-development-checkpoint-readback'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(8_000_001)
                assert len(raw) <= 8_000_000
                assert digest(raw) == p['exports'][name]['sha256'], 'public byte mismatch'
                samples.append(dict(path=name, url=url, final_url=response.url,
                                    status=response.status, bytes=len(raw), sha256=digest(raw)))
        result['anonymous_samples'] = samples
        result['anonymous_readback'] = True
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        result['checkout_after'] = checkout_state(F)
        result['canonical_pins_unchanged'] = before_source == canonical_pins(p['exports'])
        result['checkout_and_normal_index_unchanged'] = result['checkout_after'] == p['checkout_before']
        after_refs = refs(); result['refs_after'] = after_refs
        allowed = {target, tracking}
        result['unrelated_refs_unchanged'] = all(
            before_refs.get(name) == after_refs.get(name)
            for name in set(before_refs) | set(after_refs) if name not in allowed)
        c.save(c.R / 'INTEGRATION-RESULT.json', result)
    assert result['canonical_pins_unchanged'] and result['checkout_and_normal_index_unchanged']
    assert result['unrelated_refs_unchanged'] and result['anonymous_readback']
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
