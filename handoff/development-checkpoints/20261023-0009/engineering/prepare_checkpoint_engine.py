"""Prepare and verify an immutable development commit without moving the checkout.

Only an explicit input specification is used. New Git objects and the temporary
index stay in the specified preparation folder. Publication is a separate,
reviewed operation. This utility never updates refs or invokes git push.
"""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess

COMMAND_AUDITOR = None


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_read(path):
    path = Path(path)
    for component in (path, *path.parents):
        info = component.lstat()
        require(not stat.S_ISLNK(info.st_mode), f"symlink input: {path}")
        require(not getattr(info, 'st_file_attributes', 0) & 1024,
                f"reparse input: {path}")
    before = path.stat()
    require(stat.S_ISREG(before.st_mode), f"nonregular input: {path}")
    raw = path.read_bytes()
    after = path.stat()
    pin = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    require(pin(before) == pin(after) and len(raw) == after.st_size,
            f"input changed while reading: {path}")
    return raw, dict(device=after.st_dev, inode=after.st_ino,
                     bytes=len(raw), mtime_ns=after.st_mtime_ns, sha256=digest(raw))


def relative_path(value):
    require(isinstance(value, str) and value, 'empty path')
    require(not any(c in value for c in '\\:\x00\r\n\t'), 'unsafe path encoding')
    parts = PurePosixPath(value).parts
    require(not value.startswith('/') and '..' not in parts and '.' not in parts,
            'absolute or traversing path')
    require(PurePosixPath(value).as_posix() == value, 'noncanonical path')
    require(not any(p.lower() == '.git' for p in parts), 'Git metadata export')
    return value


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def git(root, args, *, env=None, data=None, allowed=(0,), return_completed=False):
    child_env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        child_env.pop(name, None)
    child_env['GIT_OPTIONAL_LOCKS'] = '0'
    child_env.update(env or {})
    result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'maintenance.auto=false',
                             '-c', 'gc.auto=0', *args], cwd=root,
                            env=child_env, input=data, capture_output=True, timeout=180)
    if COMMAND_AUDITOR is not None:
        COMMAND_AUDITOR(args, result)
    require(result.returncode in allowed,
            f"git {args[0]} failed ({result.returncode}): "
            + result.stderr.decode('utf-8', errors='replace')[:2000])
    return result if return_completed else result.stdout


def checkout_state(root):
    git_dir = Path(git(root, ['rev-parse', '--absolute-git-dir']).decode().strip())
    index = git_dir / 'index'
    require(index.is_file(), 'normal Git index absent')
    return dict(root=git(root, ['rev-parse', '--show-toplevel']).decode().strip(),
                branch=git(root, ['symbolic-ref', 'HEAD']).decode().strip(),
                head=git(root, ['rev-parse', 'HEAD']).decode().strip(),
                index_sha256=digest(index.read_bytes()),
                status_sha256=digest(git(root, ['status', '--porcelain=v1', '-z'])),
                remote_fetch=git(root, ['remote', 'get-url', 'origin']).decode().strip(),
                remote_push=git(root, ['remote', 'get-url', '--push', 'origin']).decode().strip())


def batch_blobs(root, oids, env):
    raw = git(root, ['cat-file', '--batch'], env=env,
              data=('\n'.join(oids) + '\n').encode('ascii'))
    cursor = 0
    result = []
    for oid in oids:
        end = raw.index(b'\n', cursor)
        header = raw[cursor:end].decode('ascii').split()
        require(len(header) == 3 and header[:2] == [oid, 'blob'], 'unexpected Git object')
        size = int(header[2]); start = end + 1; finish = start + size
        require(raw[finish:finish + 1] == b'\n', 'truncated Git blob response')
        result.append(raw[start:finish]); cursor = finish + 1
    require(cursor == len(raw), 'extra Git blob response')
    return result


def scan_exports(inputs):
    """Scan every byte payload's ASCII and NUL-stripped byte projections."""
    patterns = [
        ('aws_access_id', re.compile(r'AKIA[0-9A-Z]{16}')),
        ('slack_token', re.compile(r'xox[baprs]-[A-Za-z0-9-]{20,}')),
        ('quoted_secret_assignment', re.compile(
            r'''(?i)(?:api[_-]?key|private[_-]?key|secret[_-]?key|password)\s*[:=]\s*["']([^"']{10,})["']''')),
        ('pem_private_key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----')),
        ('github_token', re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})')),
    ]
    findings = []; checked = []
    for name, item in inputs.items():
        raw, pin = stable_read(item['input_path'])
        require(pin == item['input_pin'], 'export changed before secret scan')
        try:
            text = raw.decode('utf-8-sig'); encoding = 'UTF-8'
        except UnicodeDecodeError:
            text = raw.decode('latin1'); encoding = 'binary-byte-projection'
        checked.append(dict(path=name, bytes=len(raw), sha256=digest(raw), encoding=encoding))
        views = [('byte_or_utf8', text)]
        if b'\0' in raw:
            views.append(('nul_stripped_bytes', raw.replace(b'\0', b'').decode('latin1')))
        for projection, view in views:
            for line_number, line in enumerate(view.splitlines(), 1):
                for label, pattern in patterns:
                    if pattern.search(line):
                        findings.append(dict(path=name, line=line_number, pattern=label,
                                             projection=projection,
                                             line_sha256=digest(line.encode('utf-8'))))
    return dict(scope='every exact exported text or binary blob; ASCII and NUL-stripped projections', files=checked,
                pattern_names=[x[0] for x in patterns], findings=findings,
                result='PASS' if not findings else 'REVIEW_REQUIRED',
                limit='Configured patterns only; no completeness or runtime-security claim')


ARCHIVAL_POLICY_PATH = Path(__file__).with_name('ARCHIVAL-WHITESPACE-POLICY.json')
ARCHIVAL_POLICY_SHA = '575fa929b27dfbac41540cd6b30b0aa9270b38f42153313845f7b5bfcceef6a6'
ARCHIVAL_PREFIX = 'handoff/development-checkpoints/20261023-0009/'
CHECKPOINT_PARENT = '2c8f73eb354915d0328e227121436259a9592446'
FAILED_PRIVATE_COMMIT = '8b8142c56d23a338262894e9d4601195bc26f652'
SUCCESSOR_OUTPUT = Path('T:/00-Active/Project-AI-CETA/.agents/runtime/oq23/cp9/work/prepared-0002')
WHITESPACE_RULES = 'blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol'


def archival_policy():
    raw, _ = stable_read(ARCHIVAL_POLICY_PATH)
    require(digest(raw) == ARCHIVAL_POLICY_SHA, 'archival policy drift')
    policy = json.loads(raw)
    rows = policy['exceptions']
    require(policy['checkpoint_prefix'] == ARCHIVAL_PREFIX and policy['parent'] == CHECKPOINT_PARENT,
            'wrong archival checkpoint policy')
    require(len(rows) == 7 and len({row['destination'] for row in rows}) == 7,
            'exactly seven archival pairs required')
    require(sum(row['diagnostic_count'] for row in rows) == 40 and
            policy['expected_full_diagnostic_rows'] == 40, 'wrong archival diagnostic count')
    require(policy['unchanged_whitespace_rules'] == WHITESPACE_RULES,
            'whitespace validation rules changed')
    for row in rows:
        relative_path(row['destination'])
        require(row['destination'].startswith(ARCHIVAL_PREFIX), 'archival destination outside checkpoint')
        require(Path(row['input_path']).is_relative_to(Path('T:/00-Active/Project-AI-CETA')) and
                '..' not in Path(row['input_path']).parts, 'archival input outside project')
        require(re.fullmatch('[a-f0-9]{64}', row['sha256']) is not None, 'invalid archival hash')
    expected = policy['expected_full_stdout_utf8'].encode('utf8')
    require(digest(expected) == policy['expected_full_stdout_sha256'] ==
            '3fdf03bb63279414739b153052a98901ce9ff00ac54c6039bff5e1e1fb9d6f39',
            'archival diagnostic bytes drift')
    return policy


def archival_whitespace(prepared):
    """Qualify only seven fixed archived byte pairs; all other paths stay strict."""
    policy = archival_policy()
    root = Path(prepared['root']); env = prepared['git_environment']
    require(root == Path('T:/00-Active/Project-AI-CETA') and
            prepared['parent'] == CHECKPOINT_PARENT and
            prepared['commit'] != FAILED_PRIVATE_COMMIT, 'wrong successor root or parent')
    require(prepared['archival_whitespace_policy_sha256'] == ARCHIVAL_POLICY_SHA,
            'prepared archival policy binding differs')
    verified = []
    for row in policy['exceptions']:
        name = row['destination']
        require(name in prepared['exports'], 'expected archival export missing')
        item = prepared['exports'][name]
        require(item['source_kind'] == 'explicit_evidence' and item['sha256'] == row['sha256'] and
                Path(item['input_path']) == Path(row['input_path']), 'archival export pair differs')
        raw, pin = stable_read(item['input_path'])
        require(pin == item['input_pin'] and digest(raw) == row['sha256'], 'archival input bytes drift')
        blob = git(root, ['cat-file', 'blob', prepared['commit'] + ':' + name], env=env)
        require(digest(blob) == row['sha256'], 'archival blob bytes drift')
        verified.append(dict(destination=name, input_sha256=digest(raw), blob_sha256=digest(blob)))
    args = ['-c', 'core.whitespace=' + WHITESPACE_RULES, 'diff-tree', '--check',
            prepared['parent'], prepared['commit']]
    full = git(root, args, env=env, allowed=(0, 2), return_completed=True)
    expected = policy['expected_full_stdout_utf8'].encode('utf8')
    require(full.returncode == 2 and full.stderr == b'' and full.stdout == expected,
            'unexpected or missing full whitespace diagnostics')
    exclusions = [':(top,exclude,literal)' + row['destination'] for row in policy['exceptions']]
    strict = git(root, args + ['--', '.', *exclusions], env=env, return_completed=True)
    require(strict.returncode == 0 and strict.stdout == b'' and strict.stderr == b'',
            'strict whitespace check failed outside exact archival pairs')
    return dict(policy_sha256=ARCHIVAL_POLICY_SHA, exact_archival_pairs=verified,
                full_check_actual_exit_status=full.returncode,
                full_check_stdout_sha256=digest(full.stdout), expected_archival_diagnostic_rows=40,
                strict_other_paths_actual_exit_status=strict.returncode,
                strict_other_paths_stdout_sha256=digest(strict.stdout),
                first_failed_private_attempt_remains_failed=True,
                canonical_or_new_source_exception=False)


def verify(prepared_path):
    require(Path(prepared_path).resolve() == SUCCESSOR_OUTPUT / 'PREPARED.json',
            'only distinct prepared-0002 may be verified by successor')
    prepared = json.loads(Path(prepared_path).read_bytes())
    root = Path(prepared['root']); env = prepared['git_environment']
    require(checkout_state(root) == prepared['checkout_before'], 'active checkout drift')
    tree = git(root, ['rev-parse', prepared['commit'] + '^{tree}'], env=env).decode().strip()
    require(tree == prepared['tree'], 'commit/tree mismatch')
    parents = git(root, ['rev-list', '--parents', '-n', '1', prepared['commit']],
                  env=env).decode().split()
    require(parents == [prepared['commit'], prepared['parent']], 'commit parent mismatch')
    entries = {}
    for item in git(root, ['ls-tree', '-r', '-z', tree], env=env).split(b'\0'):
        if item:
            header, name = item.split(b'\t', 1)
            mode, kind, oid = header.decode('ascii').split()
            entries[name.decode('utf-8')] = (mode, kind, oid)
    names = list(prepared['exports'])
    oids = [entries[name][2] for name in names]
    for name, blob in zip(names, batch_blobs(root, oids, env), strict=True):
        item = prepared['exports'][name]
        require(entries[name][1] == 'blob' and digest(blob) == item['sha256'],
                f"export blob mismatch: {name}")
        raw, pin = stable_read(item['input_path'])
        require(pin == item['input_pin'] and digest(raw) == digest(blob),
                f"export input drift: {name}")
    changed = git(root, ['diff-tree', '--no-commit-id', '--name-only', '-r', '-z',
                         prepared['parent'], prepared['commit']], env=env).split(b'\0')
    changed = sorted(x.decode('utf-8') for x in changed if x)
    require(changed == prepared['changed_paths'], 'unexpected Git change surface')
    require(set(changed) <= set(names), 'unexported path changed')
    whitespace = archival_whitespace(prepared)
    for path, expected in prepared['pack_files'].items():
        require(digest(stable_read(path)[0]) == expected, 'prepared Git pack drift')
    require(not scan_exports(prepared['exports'])['findings'], 'secret scan requires review')
    require(checkout_state(root) == prepared['checkout_before'], 'checkout changed during verification')
    return dict(status='PASS', commit=prepared['commit'], tree=tree,
                exported_paths=len(names), changed_paths=len(changed),
                active_checkout_and_index_unchanged=True, archival_whitespace=whitespace,
                development_only=True, product_acceptance=False)


def prepare(spec_path):
    spec_raw, spec_pin = stable_read(spec_path); spec = json.loads(spec_raw)
    root = Path(spec['root']).resolve(); output = Path(spec['output']).resolve()
    require(root == Path('T:/00-Active/Project-AI-CETA').resolve(), 'wrong repository')
    require(output.is_relative_to(root / '.agents/runtime'), 'output outside project runtime')
    require(spec['ref'] == 'refs/heads/development/checkpoints', 'wrong publication ref')
    policy = archival_policy()
    require(output == SUCCESSOR_OUTPUT and spec['parent'] == CHECKPOINT_PARENT and
            spec['archival_whitespace_policy_sha256'] == ARCHIVAL_POLICY_SHA,
            'wrong distinct preparation output, parent or policy')
    output.mkdir(exist_ok=False)
    before = checkout_state(root)
    require(before['head'] == spec['expected_head'] and before['branch'] == spec['expected_branch'],
            'unexpected active Git identity')
    require(before['remote_fetch'] == spec['origin'] == before['remote_push'], 'wrong origin')
    require(before['status_sha256'] == spec.get('expected_status_sha256', digest(b'')),
            'working-state drift; freeze and explicitly enroll the current change set')
    canonical_git = Path(git(root, ['rev-parse', '--absolute-git-dir']).decode().strip())
    objects = output / 'objects'; objects.mkdir()
    env = dict(GIT_INDEX_FILE=str(output / 'index'), GIT_OBJECT_DIRECTORY=str(objects),
               GIT_ALTERNATE_OBJECT_DIRECTORIES=str(canonical_git / 'objects'))
    manifest_raw, manifest_pin = stable_read(spec['manifest'])
    require(digest(manifest_raw) == spec['manifest_sha256'], 'source manifest changed')
    manifest = json.loads(manifest_raw); candidate = Path(manifest['candidate']).resolve()
    require(candidate.is_relative_to(root), 'candidate outside project')
    require(len(manifest['payload_hashes']) == manifest['payload_count'], 'payload count mismatch')
    inputs = {}
    for name, expected in manifest['payload_hashes'].items():
        relative_path(name)
        require(name.casefold() not in {x.casefold() for x in inputs}, 'case-colliding paths')
        source = candidate / name; raw, pin = stable_read(source)
        require(pin['sha256'] == expected, f"candidate pin mismatch: {name}")
        require(len(raw) < 95_000_000, 'oversize Git blob')
        inputs[name] = dict(input_path=str(source), input_pin=pin, sha256=expected,
                            mode='100644', source_kind='frozen_candidate')
    for item in spec['extra_exports']:
        name = relative_path(item['destination']); source = Path(item['source']).resolve()
        require(source.is_relative_to(root), 'evidence outside project')
        require(name.casefold() not in {x.casefold() for x in inputs}, 'export collision')
        raw, pin = stable_read(source)
        require(pin['sha256'] == item['sha256'], f"evidence pin mismatch: {name}")
        require(len(raw) < 95_000_000, 'oversize evidence')
        inputs[name] = dict(input_path=str(source), input_pin=pin, sha256=pin['sha256'],
                            mode='100644', source_kind='explicit_evidence')
    require(len(inputs) > manifest['payload_count'], 'development acceptance disclosure missing')
    for row in policy['exceptions']:
        item = inputs.get(row['destination'])
        require(item is not None and item['sha256'] == row['sha256'] and
                item['input_path'] == row['input_path'] and item['source_kind'] == 'explicit_evidence',
                'exact archival pair absent from new preparation')
    secret_scan = scan_exports(inputs)
    save(output / 'EXACT-EXPORT-SECRET-SCAN.json', secret_scan)
    require(not secret_scan['findings'], 'secret scan requires independent resolution')
    parent = spec['parent']
    require(re.fullmatch('[a-f0-9]{40}', parent) is not None, 'invalid parent')
    require(git(root, ['merge-base', '--is-ancestor', before['head'], parent], env=env) == b'',
            'parent does not preserve active history')
    git(root, ['read-tree', parent], env=env)
    path_input = ''.join(json.dumps(x['input_path'].replace('\\', '/'), ensure_ascii=False) + '\n'
                         for x in inputs.values()).encode('utf-8')
    oids = git(root, ['hash-object', '-w', '--no-filters', '--stdin-paths'], env=env,
               data=path_input).decode('ascii').splitlines()
    require(len(oids) == len(inputs) and all(re.fullmatch('[a-f0-9]{40}', x) for x in oids),
            'Git blob inventory mismatch')
    index_input = b''.join(f"{item['mode']} {oid}\t{name}".encode('utf-8') + b'\0'
                           for (name, item), oid in zip(inputs.items(), oids, strict=True))
    git(root, ['update-index', '-z', '--index-info'], env=env, data=index_input)
    tree = git(root, ['write-tree'], env=env).decode('ascii').strip()
    require(tree != git(root, ['rev-parse', parent + '^{tree}'], env=env).decode().strip(),
            'no new content; empty checkpoint refused')
    commit = git(root, ['commit-tree', tree, '-p', parent], env=env,
                 data=(spec['message'] + '\n').encode('utf-8')).decode('ascii').strip()
    changed_raw = git(root, ['diff-tree', '--no-commit-id', '--name-only', '-r', '-z',
                              parent, commit], env=env)
    changed = sorted(x.decode('utf-8') for x in changed_raw.split(b'\0') if x)
    pack_dir = output / 'pack'; pack_dir.mkdir()
    pack_name = git(root, ['pack-objects', '--revs', str(pack_dir / 'checkpoint')], env=env,
                    data=f"{commit}\n^{parent}\n".encode()).decode().strip()
    pack_files = {str(pack_dir / f'checkpoint-{pack_name}.{suffix}'):
                  digest((pack_dir / f'checkpoint-{pack_name}.{suffix}').read_bytes())
                  for suffix in ('pack', 'idx')}
    prepared = dict(schema='ceta.development-checkpoint.prepared.v1',
                    at=datetime.now(timezone.utc).isoformat(), root=str(root),
                    ref=spec['ref'], origin=spec['origin'], commit=commit, tree=tree, parent=parent,
                    checkout_before=before, git_environment=env, exports=inputs,
                    manifest_pin=manifest_pin, spec_pin=spec_pin,
                    spec_path=str(Path(spec_path).resolve()), pack_files=pack_files,
                    changed_paths=changed, source_acceptance='DEVELOPMENT_ONLY',
                    whitespace_policy='blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol; preserve exact Windows CRLF',
                    archival_whitespace_policy_sha256=ARCHIVAL_POLICY_SHA,
                    product_acceptance=False, ref_publication=False)
    save(output / 'PREPARED.json', prepared)
    outcome = verify(output / 'PREPARED.json')
    save(output / 'VERIFICATION.json', outcome)
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'verify'))
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    result = prepare(args.path) if args.mode == 'prepare' else verify(args.path)
    print(json.dumps(result, indent=2))
