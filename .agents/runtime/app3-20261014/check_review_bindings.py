"""Personally inspect finite report identities and the separate line audit."""
from pathlib import Path
import hashlib
import json
S = Path(__file__).resolve().parents[3]
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
audit = read(S / '.agents/runtime/app3-20261014/independent-review/joined-audit.json')
totals = {}
for item in audit['exact_seven_path_line_changes']:
    group = item['relative_path'].split('/')[0]
    values = totals.setdefault(group, {'added': 0, 'removed': 0})
    for change in item['line_changes']:
        values['added'] += len(change['new_lines'])
        values['removed'] += len(change['old_lines'])
assert totals == {'contracts': {'added': 74, 'removed': 0},
                  'src': {'added': 348, 'removed': 4},
                  'tests': {'added': 805, 'removed': 9}}
full_path = S / '.agents/runtime/rs2-20261014/active-application/destination-full-r2.json'
full = read(full_path)
r = S / '.agents/runtime/hp2-provenance-20261014'
freeze = read(r / 'HP2-FREEZE.json')
for entry in freeze['files']:
    path = r / entry['path']
    assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
report = read(r / 'HP2-FINAL-REPORT.json')
assert sha(r / 'HP2-FINAL-REPORT.json') == '59d6b4fe06d0baf9b43199b7c7c9ff7a5825d71227ef217b9732076c3c96a65c'
assert len(report['entries']) == len({item['entry_id'] for item in report['entries']}) == 69
primary = read(r / 'upstream-artifact-comparison-r1.json')
assert len(primary['groups']) == 12
published_members = []
for group in primary['groups']:
    assert group['artifact_hash_matches_pypi'] is True and group['all_target_members_match'] is True
    assert group['downloaded_bytes'] == group['artifact']['size']
    for member in group['entries']:
        assert member['whole_file_match'] is True
        assert member['local_whole_file_sha256'] == member['wheel_member_sha256']
        assert member['local_bytes'] == member['wheel_member_bytes']
        published_members.append(member['id'])
assert len(published_members) == len(set(published_members)) == 31
print(json.dumps({'independent_line_audit_totals': totals, 'full_suite_sha256': sha(full_path),
    'actual_native_census': full['native_census']['result'], 'HP2_frozen_files_verified': len(freeze['files']),
    'HP2_finite_classifications': report['counts'], 'primary_public_groups': 12, 'public_members': 31,
    'Root_public_wheel_download_repeated': False, 'admitted_in_this_check': 0,
    'HP2_report_integrity_and_internal_bindings': 'PASS'}))
