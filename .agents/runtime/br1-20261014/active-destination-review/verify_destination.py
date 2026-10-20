"""Independent BR1 actual-source/originals/claim/suite/native-title destination proof."""
from datetime import datetime,timezone
from pathlib import Path
import ast
import functools
import hashlib
import importlib
import importlib.util
import json
import os
import sys
import time
import unittest

P=Path(r'T:\00-Active\Project-AI-CETA');Q=P/'.agents/br1-20261014';R=P/'.agents/runtime/br1-20261014';OUT=R/'active-destination-review';APP=R/'active-application'
PY=P/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable).resolve()==PY.resolve() and os.getcwd()==str(P.parent)
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
TEMP=OUT/'review-temp';TEMP.mkdir();os.environ['TMP']=os.environ['TEMP']=str(TEMP)
sys.path[:0]=[str(P/'src'),str(P/'tests/contract')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
p4=P/'.agents/pr4-20261014/preserve_ceta_complete.py';assert sha(p4)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec=importlib.util.spec_from_file_location('br1_destination_verified_native_reads',p4);fs=importlib.util.module_from_spec(spec);spec.loader.exec_module(fs)
def exact(path):
    with fs.open_source(fs.safe_components(path),exclusive=True) as source:return source.read()
manifest_path=Q/'TRANSFER-MANIFEST.json';manifest_hash=sha(manifest_path);assert manifest_hash=='12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
manifest=read(manifest_path);journal_path=APP/'APPLIED.json';journal_hash=sha(journal_path);assert journal_hash=='1a53057f5cd670f8edec2cb987f4d9eccb763d4f2863919519b225b51bedcfed'
journal=read(journal_path);review_path=R/'independent-review/review.json';review=read(review_path)
assert journal['review_sha256']==sha(review_path)=='fff491bbab60d4e92856cbb737b34fb1095490431fd8010247f7d6ddd90a9934'
assert journal['source_root']==str(P) and journal['executor']=='/root' and journal['manifest_sha256']==manifest_hash
assert sha(R/'apply_reviewed_titles.py')==review['result']['publication_script_sha256']=='a5787a1dba9f8fd816f0d9394c5bda10f07a731552505378423c5bd81d6275e6'
state=read(R/'br1-20261014/state.json');claim=read(R/'br1-20261014/claims.json')['integrate']
assert state['nodes']['review']['state']==state['nodes']['validate']['state']=='SUCCEEDED'
assert claim['executor_id']=='/root' and claim['workspace']==str(P) and claim['input_hash']==journal['claim_input_hash']
claim_identity={key:claim[key] for key in ('executor_id','workspace','input_hash','claimed_at')}
expected={x['relative_path']:x['candidate_sha256'] for x in manifest['payloads']};assert len(expected)==235
source_before={name:hashlib.sha256(exact(P/name)).hexdigest() for name in expected};assert source_before==expected
assert {name:hashlib.sha256(exact(Q/name)).hexdigest() for name in expected}==expected
selected=set(manifest['application_paths']);originals={x['relative_path']:x for x in journal['before_images']};completed={x['relative_path']:x for x in journal['completed']}
assert selected==set(originals)==set(completed) and len(selected)==4
original_rows=[]
for item in manifest['payloads']:
    name=item['relative_path']
    if name not in selected:assert item['candidate_sha256']==item['active_before_sha256'];continue
    logical=APP/'before'/(name+'.source');native=APP/'native-backups'/(name+'.original');retained=R/'before'/(name+'.source')
    data=exact(logical);assert data==exact(native)==exact(retained) and hashlib.sha256(data).hexdigest()==item['active_before_sha256']==originals[name]['sha256']
    info=fs.lstat(native);old=originals[name]
    assert (info.st_dev,info.st_ino,info.st_size,info.st_mode,info.st_mtime_ns)==(old['device'],old['inode'],old['bytes'],old['mode'],old['mtime_ns'])
    assert not fs.reparse(info) and not fs.exists(APP/'staged'/name) and completed[name]['sha256']==expected[name]
    original_rows.append({'relative_path':name,'current_sha256':source_before[name],'logical_sha256':sha(logical),'native_sha256':sha(native),'recorded_native_identity_metadata':old,'bytes_and_recorded_native_metadata_match':True})
suite_path=R/'destination-desktop.json';suite_hash=sha(suite_path);root_suite=read(suite_path);candidate_suite=read(R/'independent-review/connected-desktop.json')
assert root_suite['source_root']==root_suite['active_destination_root']==str(P) and root_suite['candidate_root']==str(Q)
assert root_suite['manifest_sha256']==manifest_hash and root_suite['actual_application_journal_sha256']==journal_hash
assert root_suite['exit_status']==root_suite['failures']==root_suite['errors']==root_suite['skips']==0 and root_suite['tests_run']==118
assert root_suite['expected_ids']==root_suite['executed_ids']==candidate_suite['expected_ids'] and len(set(root_suite['executed_ids']))==118
assert root_suite['before_hashes']==root_suite['after_hashes']==source_before and root_suite['actual_source_unchanged']
raw=R/'destination-desktop.txt';assert sha(raw)==root_suite['raw_sha256']
lines=raw.read_text(encoding='utf-8').splitlines();assert sum(line.endswith(' ... ok') for line in lines)==118 and 'OK' in lines
expected_titles={'.'.join(Path(path).relative_to('src').with_suffix('').parts):titles[1] for path,titles in manifest['title_changes'].items()}
assert set(root_suite['observed_title_modules'])==set(expected_titles)
assert root_suite['native_title_observations'] and all(obs['native_window_title']==expected_titles[obs['module']] for obs in root_suite['native_title_observations'])
assert len(root_suite['imports'])==72 and all(Path(x['actual_path']).resolve().is_relative_to(P/'src') and sha(Path(x['actual_path']))==x['sha256'] for x in root_suite['imports'])
imports=[]
for path in sorted((P/'src/ceta').rglob('*.py')):
    parts=list(path.relative_to(P/'src').with_suffix('').parts)
    if parts[-1]=='__init__':parts.pop()
    name='.'.join(parts);module=importlib.import_module(name);actual=Path(module.__file__).resolve();assert actual==path.resolve()
    imports.append({'module':name,'actual_path':str(actual),'sha256':sha(actual)})
assert len(imports)==72
observations=[]
for name,title in expected_titles.items():
    module=importlib.import_module(name);tree=ast.parse(Path(module.__file__).read_text())
    names=[node.name for node in tree.body if isinstance(node,ast.ClassDef) and any(isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='setWindowTitle' and call.args and isinstance(call.args[0],ast.Constant) and call.args[0].value==title for call in ast.walk(node))]
    assert len(names)==1;cls=getattr(module,names[0]);original=cls.__init__
    def observe(original,module_name,expected_title):
        @functools.wraps(original)
        def wrapped(self,*args,**kwargs):
            original(self,*args,**kwargs);actual=self.windowTitle();assert actual==expected_title
            observations.append({'module':module_name,'native_window_title':actual,'actual_source_path':str(Path(sys.modules[module_name].__file__).resolve())})
        return wrapped
    cls.__init__=observe(original,name,title)
selectors=['test_operator_view.OperatorViewTests.test_each_current_operation_picker_calls_only_injected_session','test_preparation_view.PreparationViewTests.test_taskview_modal_entry_uses_same_session_and_return_keeps_existing_edits','test_task_meaning_view.TaskMeaningViewTests.test_form_exposes_original_saved_basis_and_all_ten_separate_fields']
suite=unittest.TestLoader().loadTestsFromNames(selectors)
def ids(suite):
    if isinstance(suite,unittest.TestSuite):
        for test in suite:yield from ids(test)
    else:yield suite.id()
expected_ids=list(ids(suite));assert len(expected_ids)==3 and not any('_FailedTest' in name for name in expected_ids)
class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.executed_ids=[]
    def startTest(self,test):self.executed_ids.append(test.id());super().startTest(test)
with (OUT/'bounded-native-title.txt').open('x',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
assert set(obs['module'] for obs in observations)==set(expected_titles)
source_after={name:hashlib.sha256(exact(P/name)).hexdigest() for name in expected};assert source_after==source_before==expected
assert sha(manifest_path)==manifest_hash and sha(journal_path)==journal_hash and sha(suite_path)==suite_hash
for name,module in tuple(sys.modules.items()):
    if name=='ceta' or name.startswith('ceta.'):assert Path(module.__file__).resolve().is_relative_to(P/'src')
from PySide6.QtWidgets import QApplication
passed=result.wasSuccessful() and not result.skipped and result.executed_ids==expected_ids
record={'schema_version':1,'reviewer':'/root/history_preservation','decision':'approved' if passed else 'rejected','exit_status':0 if passed else 1,'source_root':str(P),'candidate_root':str(Q),'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-tick,'manifest_sha256':manifest_hash,'application_journal_sha256':journal_hash,'destination_suite_sha256':suite_hash,'destination_raw_sha256':sha(raw),'accepted_review_sha256':sha(review_path),'publication_script_sha256':sha(R/'apply_reviewed_titles.py'),'integration_claim_observed':claim_identity,'actual_state_sequence_observed':state['sequence'],'tests_run':root_suite['tests_run'],'destination_failures':0,'destination_errors':0,'destination_skips':0,'root_expected_ids':root_suite['expected_ids'],'root_executed_ids':root_suite['executed_ids'],'expected_payload_hashes':expected,'before_current_hashes':source_before,'after_current_hashes':source_after,'all235_active_bytes_exact_and_unchanged':True,'logical_originals':4,'native_originals':4,'original_rows':original_rows,'all_original_bytes_and_recorded_native_metadata_preserved':True,'remaining_staged_source_files':0,'retained_dependencies':231,'all72_fresh_imports_actual_T_repository':True,'fresh_imports':imports,'root_native_title_observations':root_suite['native_title_observations'],'independent_tests_run':result.testsRun,'independent_failures':len(result.failures),'independent_errors':len(result.errors),'independent_skips':len(result.skipped),'independent_expected_ids':expected_ids,'independent_executed_ids':result.executed_ids,'independent_native_title_observations':observations,'independent_raw_sha256':sha(OUT/'bounded-native-title.txt'),'actual_python':sys.executable,'python_version':sys.version,'Qt_platform':QApplication.instance().platformName(),'command_argv':[sys.executable,'-B','-X','utf8',str(Path(__file__))],'source_mutations_by_reviewer':[],'governance_mutations_by_reviewer':[],'qualification':'Bounded actual-source identity/branding destination acceptance; four existing title literal changes only','limits':['Same Windows host/principal; distinct reviewer observes Root actual source and application journal','Real Qt offscreen widgets; visible installed desktop/window-manager rendering not qualified','Original controlled application/session/transport fixtures remain tests; positive authority/full product acceptance remains outside this scope','Root destination118 suite independently checked; only three additional actual-source cases run, covering all four title classes; counts kept separate','Claim/runtime state was observed read-only; integration completion remains Root action'],'remaining_obligations':['Root binds this exact destination review and suite to its actual integration completion','Product completion and other source/history work retain their independent acceptance requirements']}
with (OUT/'destination-review.json').open('x',encoding='utf-8') as out:json.dump(record,out,indent=2);out.write('\n')
print(json.dumps({'decision':record['decision'],'exit_status':record['exit_status'],'root_tests_verified':118,'independent_tests':result.testsRun,'independent_failures':len(result.failures),'independent_errors':len(result.errors),'independent_skips':len(result.skipped),'active_payloads':235,'imports':72,'preserved_originals':4,'native_title_modules':sorted({x['module'] for x in observations}),'destination_review_sha256':sha(OUT/'destination-review.json'),'destination_suite_sha256':suite_hash}))
raise SystemExit(record['exit_status'])
