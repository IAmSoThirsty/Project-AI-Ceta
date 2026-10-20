"""Freeze the exact successor code and executable evidence for distinct review."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/ac7-token-contract-20261020'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
baseline = R / 'CANDIDATE-BASELINE-R4.json'
candidate = json.loads(baseline.read_bytes())['candidate352']
new_paths = ['tools/isolated_worker_token_oracle.py', 'tools/qualify_isolated_worker.py',
             'tools/run_one_isolation_qualification.py', 'tests/contract/test_isolation_qualification_oracle.py',
             'tests/contract/test_isolation_qualification_entry.py']
pins = {name: sha(Q / name) for name in [*candidate, *new_paths]}
assert len(pins) == 357 and all(pins[n] == v['sha256'] for n,v in candidate.items())
source = json.loads((R / 'INPUTS.json').read_bytes())['payload_hashes']
assert all(sha(F / n) == h for n,h in source.items())
test = R / 'CONTROLLED-PARENT-ORACLE-R5.json'
tests = json.loads(test.read_bytes())
assert tests['success'] and tests['tests'] == 47 and not tests['failures'] and not tests['errors']
assert all(tests['checks'].values())
assert tests['raw_sha256'] == sha(R / 'CONTROLLED-PARENT-ORACLE-R5.txt')
assert tests['tool_sha256'] == pins['tools/qualify_isolated_worker.py']
build = R / 'build-r2/BUILD.json'
built = json.loads(build.read_bytes())
assert built['source']['sha256'] == pins['native/windows_broker/isolated_worker.rs']
assert built['native_image']['sha256'] == sha(Path(built['native_image']['path']))
assert all(row['exit_status'] == 0 for row in built['commands'])
evidence_names = ['CANDIDATE-BASELINE-R4.json', 'PROFILE-CREATION-PROPOSAL-AC7-R4.json',
    'TOOL-PREPARATION-R4.json', 'CONTROLLED-PARENT-ORACLE-R5.json', 'CONTROLLED-PARENT-ORACLE-R5.txt',
    'run_controlled_r5.py', 'build_worker_r2.py', 'build-r2/BUILD.json',
    'build-r2/isolated_worker.exe', 'build-r2/isolated_worker_token_tests.exe',
    'build-r2/pure-rust-tests.stdout', 'build-r2/pure-rust-tests.stderr']
old_tool = F / '.agents/runtime/ac6-profile-preparation-20261018'
origins = {'tools/qualify_isolated_worker.py': old_tool / 'profile_qualification.py',
    'tools/run_one_isolation_qualification.py': old_tool / 'run_one_approved_attempt_v2.py'}
changes = {}
for name, pin in pins.items():
    if name in source and pin == source[name]: continue
    path = Q / name
    origin = origins.get(name, F / name)
    before = origin.read_text(encoding='utf8').splitlines() if origin.is_file() else []
    after = path.read_text(encoding='utf8').splitlines()
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    added = removed = 0
    for kind,a,b,c,d in matcher.get_opcodes():
        if kind in ('insert', 'replace'): added += sum(bool(line.strip()) for line in after[c:d])
        if kind in ('delete', 'replace'): removed += sum(bool(line.strip()) for line in before[a:b])
    role = ('product_source' if name.startswith(('src/', 'native/')) else 'test_source'
            if name.startswith('tests/') else 'engineering_tool' if name.startswith('tools/') else 'contract')
    changes[name] = dict(role=role, comparison_origin=str(origin) if origin.is_file() else None,
        source_sha256=sha(origin) if origin.is_file() else None, candidate_sha256=pin,
        nonblank_lines_added=added, nonblank_lines_removed=removed,
        copied_lines_credited_as_new=0, integrated_into_canonical_application=False)
manifest = dict(schema='ceta-ac7-qualification-review-cut-v1', at=now(), root=str(Q),
    source_head='83fc9432b4a37ee7f91d6c5b0d358a015548aed4', payload_hashes=pins,
    source352_unchanged=True, candidate_native_cut=dict(path=str(baseline), sha256=sha(baseline)),
    evidence={name: sha(R / name) for name in evidence_names}, changes=changes,
    source_publication=False, native_current_token_execution=False,
    native_profile_operations=[], restricted_worker_launches=[], actual_operator_approval=None,
    tests=dict(controlled_python=47, pure_rust=5,
        controls='DATA_ONLY values; exact entry/test bodies with explicit dependency substitutions',
        native_qualification=False),
    repaired_findings=['AC7-SR-01', 'AC7-SR-02', 'AC7-QF-01'],
    rejected_predecessor=dict(path=str(R/'AC7-QUALIFICATION-MANIFEST-R3.json'),sha256=sha(R/'AC7-QUALIFICATION-MANIFEST-R3.json')),
    rejected_review=dict(path=str(F/'.agents/runtime/ac7-qualification-review-20261020/review.json'),sha256=sha(F/'.agents/runtime/ac7-qualification-review-20261020/review.json')),
    skills_used=['thirsty-work-orchestrator', 'unfinished-work-recovery', 'protocol-interoperability-auditor'],
    governing_version='thirsty-constitution-v0.1',
    open=['Distinct successor review', 'Fresh exact one-attempt human approval',
          'Native profile qualification', 'Canonical source integration and application effect acceptance'])
with (R / 'AC7-QUALIFICATION-MANIFEST-R4.json').open('x', encoding='utf8') as out:
    json.dump(manifest, out, indent=2)
print(json.dumps(dict(payloads=len(pins), changed=len(changes),
    manifest_sha256=sha(R / 'AC7-QUALIFICATION-MANIFEST-R4.json'), tests=manifest['tests'])))
