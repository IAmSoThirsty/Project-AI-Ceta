"""Read-only Source31 byte/identity overlap and focused textual/AST projection."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import os
import stat
import subprocess

F = Path(r'T:\00-Active\Project-AI-CETA')
Q = F / '.agents/js9-runtime-20261020'
D = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
O = F / '.agents/runtime/js9-source-overlap-review-20261020'
PINS = {'PACKET.json': 'eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055',
        'SOURCE-BEFORE.json': 'a76dbdf4301eb0120bd646430c76e277827de46f888bb38d3a7c2fdad1d6958b'}
MANIFEST = F / '.agents/runtime/js9-runtime-20261020/MANIFEST-R4.json'
MANIFEST_PIN = '212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def native(path):
    s = path.stat(follow_symlinks=False)
    assert stat.S_ISREG(s.st_mode) and not s.st_file_attributes & 0x400
    return {'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'mode': s.st_mode & 0o777,
            'device': s.st_dev, 'inode': s.st_ino, 'attributes': s.st_file_attributes}


def save(name, value):
    with (O / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def symbols(text):
    tree = ast.parse(text)
    functions = {}
    imports = []
    def visit(nodes, prefix=''):
        for n in nodes:
            if isinstance(n, ast.ClassDef):
                visit(n.body, prefix + n.name + '.')
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[prefix + n.name] = {'line': n.lineno, 'end_line': n.end_lineno,
                    'signature': ast.unparse(n.args)}
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                imports.append({'line': n.lineno, 'statement': ast.unparse(n)})
    visit(tree.body)
    return {'functions': functions, 'imports': imports}


def main():
    for name, pin in PINS.items():
        assert sha(D / name) == pin
    assert sha(MANIFEST) == MANIFEST_PIN
    packet, before, manifest = read(D / 'PACKET.json'), read(D / 'SOURCE-BEFORE.json'), read(MANIFEST)
    payloads = manifest['payload_hashes']
    paths = packet['application_paths']
    assert len(paths) == len(set(paths)) == 31 and len(payloads) == len(before['targets']) == 530
    assert set(paths) == set(before['changed_or_new_paths'])
    git = ['git', '-c', 'safe.directory=T:/00-Active/Project-AI-CETA', '-C', str(F)]
    git_head = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
    git_branch = subprocess.check_output([*git, 'branch', '--show-current'], text=True).strip()
    assert {'HEAD': git_head, 'branch': git_branch} == packet['Git']
    status = subprocess.check_output([*git, 'status', '--porcelain', '--untracked-files=no'], text=True)
    tracked = set(subprocess.check_output([*git, 'ls-files', '-z', '--', *paths], text=True).split('\0')) - {''}
    all_rows, deltas, ast_rows = [], [], {}
    raw_diffs = []
    conflicts = []
    for name, expected in payloads.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        candidate = Q / name
        destination = F / name
        assert candidate.resolve().is_relative_to(Q.resolve())
        assert destination.resolve().is_relative_to(F.resolve())
        actual_candidate = sha(candidate)
        assert actual_candidate == expected
        baseline = before['targets'][name]
        current = None
        if baseline is None:
            if destination.exists():
                conflicts.append({'path': name, 'issue': 'Previously absent destination now exists'})
        else:
            try:
                current = {'sha256': sha(destination), 'native_identity': native(destination)}
                if current['sha256'] != baseline['sha256'] or current['native_identity'] != baseline['native_identity']:
                    conflicts.append({'path': name, 'issue': 'Destination differs from frozen Source-before', 'baseline': baseline, 'current': current})
            except FileNotFoundError:
                conflicts.append({'path': name, 'issue': 'Existing frozen destination disappeared'})
        content_delta = baseline is None or baseline['sha256'] != expected
        row = {'path': name, 'in_Source31': name in paths, 'baseline_exists': baseline is not None,
            'git_tracked': name in tracked, 'baseline': baseline, 'current': current,
            'candidate_sha256': expected, 'candidate_native_identity': native(candidate), 'candidate_differs_from_baseline': content_delta}
        all_rows.append(row)
        if content_delta:
            deltas.append(name)
        if name not in paths:
            continue
        old_text = '' if baseline is None else destination.read_text(encoding='utf-8-sig')
        new_text = candidate.read_text(encoding='utf-8-sig')
        diff = list(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(),
            fromfile='Source/' + name, tofile='Q530/' + name, lineterm='', n=4))
        raw_diffs.extend(diff + [''])
        row['diff_added_lines'] = sum(x.startswith('+') and not x.startswith('+++') for x in diff)
        row['diff_removed_lines'] = sum(x.startswith('-') and not x.startswith('---') for x in diff)
        if name.endswith('.py'):
            old_ast, new_ast = symbols(old_text), symbols(new_text)
            a, b = old_ast['functions'], new_ast['functions']
            ast_rows[name] = {'before': old_ast, 'candidate': new_ast,
                'removed_symbols': sorted(set(a) - set(b)), 'added_symbols': sorted(set(b) - set(a)),
                'changed_signatures': {k: {'before': a[k], 'candidate': b[k]} for k in set(a) & set(b)
                                       if a[k]['signature'] != b[k]['signature']}}
    assert set(deltas) == set(paths), ('Publication list differs from actual content delta', deltas)
    with (O / 'SOURCE31.diff').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(raw_diffs) + '\n')
    save('CALLER-SIGNATURES.json', ast_rows)
    # These tracked reasoning edits belong to the frozen Source/Q baseline and
    # must not be mislabelled as new JS9 publication changes.
    reasoning = [r for r in all_rows if r['path'].startswith(('src/ceta/reasoning/', 'tests/contract/reasoning/'))]
    assert all(not r['in_Source31'] and not r['candidate_differs_from_baseline'] for r in reasoning)
    for row in all_rows:
        candidate = Q / row['path']
        assert native(candidate) == row['candidate_native_identity'] and sha(candidate) == row['candidate_sha256']
        if row['current'] is not None:
            destination = F / row['path']
            assert native(destination) == row['current']['native_identity'] and sha(destination) == row['current']['sha256']
    result = {'at_utc': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/ac7_native_artifact_review20',
        'scope': 'Read-only exact Source31 overlap; no publication, tests or native work',
        'packet_sha256': PINS['PACKET.json'], 'Source_before_sha256': PINS['SOURCE-BEFORE.json'],
        'candidate_manifest_sha256': MANIFEST_PIN, 'git': {'head': git_head, 'branch': git_branch},
        'tracked_dirty_status': status.splitlines(), 'candidate_payloads_verified': len(all_rows),
        'Source_before_targets_verified': len(all_rows), 'Source31': [r for r in all_rows if r['in_Source31']],
        'actual_delta_paths': sorted(deltas), 'new_paths': sum(r['baseline'] is None for r in all_rows if r['in_Source31']),
        'existing_replacements': sum(r['baseline'] is not None for r in all_rows if r['in_Source31']),
        'reasoning_baseline_rows': reasoning, 'conflicts': conflicts, 'input_drift': 0,
        'same_project_paths': True, 'all_Source31_listed_in_frozen_packet': True,
        'Source_mutated_by_reviewer': False, 'publication_or_full_acceptance': False}
    save('OVERLAP-CHECKS.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('Source31','reasoning_baseline_rows','tracked_dirty_status','actual_delta_paths')}, indent=2))


if __name__ == '__main__':
    main()
