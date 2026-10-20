"""Final Source31 CAS/identity check and compact exact-cut review record."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import stat

F = Path(r'T:\00-Active\Project-AI-CETA')
O = F / '.agents/runtime/js9-source-overlap-review-20261020'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
checks = read(O / 'OVERLAP-CHECKS.json')
assert checks['conflicts'] == []
symbols = read(O / 'CALLER-SIGNATURES.json')
assert all(not r['removed_symbols'] for r in symbols.values())
rows = []
for row in checks['Source31']:
    target = F / row['path']
    if row['baseline'] is None:
        assert not target.exists(), row['path']
    else:
        n = target.stat(follow_symlinks=False)
        identity = {'bytes': n.st_size, 'mtime_ns': n.st_mtime_ns, 'mode': n.st_mode & 0o777,
                    'device': n.st_dev, 'inode': n.st_ino, 'attributes': n.st_file_attributes}
        assert identity == row['baseline']['native_identity'] and sha(target) == row['baseline']['sha256']
    candidate = F / '.agents/js9-runtime-20261020' / row['path']
    assert sha(candidate) == row['candidate_sha256']
    rows.append({'path': row['path'], 'operation': 'CREATE' if row['baseline'] is None else 'REPLACE_EXACT_BEFOREIMAGE',
        'expected_before': row['baseline'], 'candidate_sha256': row['candidate_sha256'],
        'git_tracked': row['git_tracked']})
result = {'at_utc': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/ac7_native_artifact_review20',
    'disposition': 'APPROVED_SOURCE31_OVERLAP_AT_RECORDED_CUT',
    'packet_sha256': checks['packet_sha256'], 'Source_before_sha256': checks['Source_before_sha256'],
    'Q530_manifest_sha256': checks['candidate_manifest_sha256'], 'git': checks['git'],
    'exact_Source31': rows, 'new_paths': 20, 'existing_replacements': 11,
    'candidate_payloads_and_Source_before_targets_checked': 530,
    'unchanged_other_candidate_paths': 499, 'reasoning_baseline_paths_unchanged': len(checks['reasoning_baseline_rows']),
    'tracked_reasoning_edits_preserved': 5, 'existing_python_symbols_removed': 0,
    'Python_files_AST_checked': len(symbols), 'signature_changes': sum(len(r['changed_signatures']) for r in symbols.values()),
    'concrete_destination_conflicts': [], 'concrete_changed_caller_conflicts_found': [],
    'same_project_authorized_paths': True, 'unknown_destination_changes_to_overwrite': False,
    'source_or_candidate_modified_by_reviewer': False, 'native_or_tests_run': False,
    'publication_or_full_product_accepted': False,
    'limits': ['Overlap and focused caller-hunk review only; no runtime/whole-product proof',
        'Q5 and eleven additional test dependency copies are not a reviewed new cut here; Source31 bytes must match this exact hash table and a later publisher must recheck current destination CAS/identity',
        'Git-untracked does not mean absent: eleven existing untracked Source files are protected by native identity and before digest']}
with (O / 'REVIEW.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in result.items() if k != 'exact_Source31'}, indent=2))
