from pathlib import Path
import ast, hashlib, importlib, json, os, subprocess, sys, unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/en2-20261014';BASE=P/'.agents/runtime/en2-20261014';D=BASE/'independent-review'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q=Q;s.R=D;s.RUN='en2-20261014'
RUN=s.RUN;ACTOR=s.ACTOR

def call(args,label):
    cmd=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(BASE)]
    start=s.utc();r=subprocess.run(cmd,cwd='T:/00-Active',capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    (D/(label+'.stdout.txt')).write_bytes(r.stdout);(D/(label+'.stderr.txt')).write_bytes(r.stderr)
    parsed=json.loads(r.stdout.decode('utf-8-sig'));s.write_new(D/(label+'.json'),dict(command_argv=cmd,started_at=start,finished_at=s.utc(),exit_status=r.returncode,response=parsed))
    assert r.returncode==0 and parsed['allowed'],parsed
    return parsed

state=json.loads((BASE/RUN/'state.json').read_text());assert state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY'
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='e06ff0b6570c4484513cc3c18be1735e1e6fe97f818678745565f7864ae3efe7'
assert s.sha(BASE/'implement.json')=='da73894bbe71129466d538e6d1f86358c3f966680328c82d1140bc7623d2af26'
claim=call(['node','claim',RUN,'review','--executor',ACTOR,'--workspace',str(Q)],'review-claim')['claim']
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text());parent=P/'.agents/en1-20261014'
before={row['relative_path']:s.ordinary(Q/row['relative_path']) for row in manifest['payloads']}
assert len(before)==295 and all(before[row['relative_path']]['sha256']==row['candidate_sha256'] for row in manifest['payloads'])
source_receipt=P/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json'
source_hashes=json.loads(source_receipt.read_text())['after_hashes']
source_before={name:s.ordinary(P/name) for name in source_hashes}
assert len(source_before)==290 and all(source_before[name]['sha256']==value for name,value in source_hashes.items())
changes=[name for name in before if s.sha(Q/name)!=s.sha(parent/name)]
assert set(changes)==set(manifest['eligible_application_paths'])
name='src/ceta/contracts/owner_enrollment.py'
old=(parent/name).read_text();new=(Q/name).read_text()
needle="re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,63}', component) is not None"
replacement="re.fullmatch(r'[A-Za-z0-9.][A-Za-z0-9._ -]{0,63}', component) is not None"
assert old.count(needle)==1 and new==old.replace(needle,replacement)
name='tests/contract/test_owner_enrollment.py'
def methods(path):
    tree=ast.parse(path.read_text());return {item.name:ast.dump(item,include_attributes=False) for cls in tree.body if isinstance(cls,ast.ClassDef) for item in cls.body if isinstance(item,ast.FunctionDef) and item.name.startswith('test_')}
a=methods(parent/name);b=methods(Q/name);assert len(a)==35 and len(b)==38 and all(b[k]==v for k,v in a.items())
assert set(b)-set(a)=={'test_ordinary_dot_directories_preserve_exact_native_path_binding','test_dot_component_support_keeps_traversal_alias_and_device_denials','test_dot_directory_case_and_copy_still_require_exact_expected_identity'}
name='contracts/OWNER_ENROLLMENT_V1.md';assert (Q/name).read_bytes().startswith((parent/name).read_bytes())
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
mods=[importlib.import_module(name) for name in ('test_owner_enrollment','test_temporal','test_wire','test_all_records')]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in mods)
def ids(group):
    for case in group:
        if isinstance(case,unittest.TestSuite):yield from ids(case)
        else:yield case.id()
expected=list(ids(suite));assert len(expected)==len(set(expected))==85
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
executed=[]
with (D/'tests.txt').open('x',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
assert result.wasSuccessful() and not result.skipped and executed==expected
assert all(s.ordinary(Q/name)==facts for name,facts in before.items())
assert all(s.ordinary(P/name)==facts for name,facts in source_before.items())
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='e06ff0b6570c4484513cc3c18be1735e1e6fe97f818678745565f7864ae3efe7'
report=dict(recorded_at=s.utc(),decision='approved',exit_status=0,manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),
 implement_sha256=s.sha(BASE/'implement.json'),author='/root',reviewer=ACTOR,tests_run=85,failures=0,errors=0,skips=0,
 expected_ids=expected,executed_ids=executed,raw=s.reference(D/'tests.txt'),candidate_files=295,changed_paths=changes,
 verified_findings=['Exact one-character predicate extension only; all other source AST/public interfaces unchanged.',
 '35 prior enrollment methods remain exact; three new methods cover ordinary leading dots, traversal/device/ADS/alias rejection and exact case/file-ID expected binding.',
 '47 original temporal/wire/schema cases and38 enrollment cases independently pass; current Source290 and all295 candidate payloads retain native IDs and bytes during this review.'],
 limitations=['DATA_ONLY contract; no actual native object observation, enrollment ceremony, grants, policy activation or Source publication.','Case-sensitive canonical data equality does not claim Windows path spelling uniqueness without retained native identity.'],
 source_before=source_before,candidate_before=before,prior_read_lookup_failure='Guessed CANDIDATE-MANIFEST.json was absent; actual TRANSFER-MANIFEST.json read and pinned before claim. No source failure.')
s.write_new(D/'REPORT.json',report)
print(json.dumps(dict(report_sha256=s.sha(D/'REPORT.json'),tests_run=85,decision='approved',claim_id=claim.get('claim_id'))),flush=True)
