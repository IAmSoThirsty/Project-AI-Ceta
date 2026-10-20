"""Bounded independent BR1 exact-literal/native-Qt/connected behavior review."""
from datetime import datetime,timezone
from pathlib import Path
import ast
import difflib
import functools
import hashlib
import importlib
import io
import json
import os
import sys
import time
import unittest

R=Path(__file__).resolve().parent
P=Path(r'T:\00-Active\Project-AI-CETA')
Q=P/'.agents/br1-20261014'
PY=P/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable).resolve()==PY.resolve() and os.getcwd()==str(P.parent)
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
temp=R/'independent-temp';temp.mkdir();os.environ['TMP']=os.environ['TEMP']=str(temp)
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
manifest_path=Q/'TRANSFER-MANIFEST.json';manifest=read(manifest_path)
assert sha(manifest_path)=='12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
assert sha(R.parent/'implement.json')=='1cd3d3001771fd8eb538fc6af78e266b7558cb9b4055564bb3ee88f1ac94e3ce'
claim=read(R.parent/'br1-20261014/claims.json')['review']
assert claim['executor_id']=='/root/history_preservation' and claim['workspace']==str(Q)
claim_baseline=claim['baseline_snapshot'];assert len(claim_baseline)==236
assert {key:sha(Path('T:/')/key) for key in claim_baseline}==claim_baseline
before={item['relative_path']:sha(Q/item['relative_path']) for item in manifest['payloads']}
source_before={item['relative_path']:sha(P/item['relative_path']) for item in manifest['payloads']}
assert len(before)==len(source_before)==235
assert all(before[x['relative_path']]==x['candidate_sha256'] and source_before[x['relative_path']]==x['active_before_sha256'] for x in manifest['payloads'])
rows=[]
for item in manifest['payloads']:
    name=item['relative_path']
    if name not in manifest['application_paths']:
        assert item['application_action']=='IDENTICAL_RETAINED' and before[name]==source_before[name]
        continue
    saved=R.parent/'before'/(name+'.source')
    old_bytes,new_bytes=saved.read_bytes(),(Q/name).read_bytes()
    assert hashlib.sha256(old_bytes).hexdigest()==source_before[name]
    old_title,new_title=manifest['title_changes'][name]
    assert new_title.startswith('Project-AI: CETA | ')
    old_literal=('setWindowTitle("'+old_title+'")').encode();new_literal=('setWindowTitle("'+new_title+'")').encode()
    assert old_bytes.count(old_literal)==1 and old_bytes.replace(old_literal,new_literal,1)==new_bytes
    left,right=ast.parse(old_bytes),ast.parse(new_bytes);replacements=0
    for node in ast.walk(left):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='setWindowTitle' and len(node.args)==1 and isinstance(node.args[0],ast.Constant) and node.args[0].value==old_title:
            node.args[0].value=new_title;replacements+=1
    assert replacements==1 and ast.dump(left,include_attributes=False)==ast.dump(right,include_attributes=False)
    diff=list(difflib.unified_diff(old_bytes.decode().splitlines(),new_bytes.decode().splitlines(),lineterm=''))
    added=[line for line in diff if line.startswith('+') and not line.startswith('+++')]
    removed=[line for line in diff if line.startswith('-') and not line.startswith('---')]
    assert len(added)==len(removed)==1
    location=next(node.lineno for node in ast.walk(right) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='setWindowTitle' and node.args and isinstance(node.args[0],ast.Constant) and node.args[0].value==new_title)
    rows.append({'relative_path':name,'line':location,'old_title':old_title,'new_title':new_title,'only_one_title_argument_changed':True,'entire_remaining_AST_equivalent':True,'before_sha256':source_before[name],'candidate_sha256':before[name],'physical_added':1,'physical_removed':1,'diff':diff})
assert len(rows)==4 and sum(x['physical_added'] for x in rows)==sum(x['physical_removed'] for x in rows)==4
imports=[]
for path in sorted((Q/'src/ceta').rglob('*.py')):
    parts=list(path.relative_to(Q/'src').with_suffix('').parts)
    if parts[-1]=='__init__':parts.pop()
    name='.'.join(parts);module=importlib.import_module(name);actual=Path(module.__file__).resolve()
    assert actual==path.resolve()
    imports.append({'module':name,'actual_path':str(actual),'sha256':sha(actual)})
assert len(imports)==72
observations=[]
for item in rows:
    module_name='.'.join(Path(item['relative_path']).relative_to('src').with_suffix('').parts)
    module=importlib.import_module(module_name);tree=ast.parse((Q/item['relative_path']).read_text())
    classes=[node.name for node in tree.body if isinstance(node,ast.ClassDef) and any(isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='setWindowTitle' and call.args and isinstance(call.args[0],ast.Constant) and call.args[0].value==item['new_title'] for call in ast.walk(node))]
    assert len(classes)==1
    cls=getattr(module,classes[0]);original=cls.__init__
    def observe(original,module_name,class_name,expected):
        @functools.wraps(original)
        def wrapped(self,*args,**kwargs):
            original(self,*args,**kwargs)
            actual=self.windowTitle();assert actual==expected
            observations.append({'module':module_name,'class':class_name,'native_window_title':actual,'actual_source_path':str(Path(sys.modules[module_name].__file__).resolve()),'method':'Actual QWidget/QDialog.windowTitle after unchanged production constructor; observer never sets title'})
        return wrapped
    cls.__init__=observe(original,module_name,classes[0],item['new_title'])
names=('test_operator_view','test_preparation_view','test_task_meaning_view','test_task_view')
suite=unittest.TestLoader().loadTestsFromNames(names)
def ids(suite):
    if isinstance(suite,unittest.TestSuite):
        for test in suite:yield from ids(test)
    else:yield suite.id()
expected_ids=list(ids(suite));author=read(R.parent/'connected-desktop.json')
assert len(expected_ids)==len(set(expected_ids))==118 and expected_ids==author['expected_ids']
class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.executed_ids=[]
    def startTest(self,test):self.executed_ids.append(test.id());super().startTest(test)
with (R/'connected-desktop.txt').open('x',encoding='utf-8',buffering=1) as output:result=unittest.TextTestRunner(stream=output,verbosity=2,resultclass=Result).run(suite)
from PySide6.QtWidgets import QApplication
observed={o['module'] for o in observations}
expected_modules={'.'.join(Path(row['relative_path']).relative_to('src').with_suffix('').parts) for row in rows}
assert observed==expected_modules
source_after={name:sha(P/name) for name in source_before};after={name:sha(Q/name) for name in before}
assert before==after and source_before==source_after and {key:sha(Path('T:/')/key) for key in claim_baseline}==claim_baseline
for name,module in tuple(sys.modules.items()):
    if name=='ceta' or name.startswith('ceta.'):assert Path(module.__file__).resolve().is_relative_to(Q/'src')
passed=result.wasSuccessful() and not result.skipped and expected_ids==result.executed_ids
report={'schema_version':1,'reviewer':'/root/history_preservation','writer':'/root','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-tick,'source_root':str(P),'candidate_root':str(Q),'manifest_sha256':sha(manifest_path),'author_implement_sha256':sha(R.parent/'implement.json'),'claim_input_hash':claim['input_hash'],'claimed_at':claim['claimed_at'],'claimed_members':236,'claim_baseline':claim_baseline,'claim_after':{key:sha(Path('T:/')/key) for key in claim_baseline},'candidate_before':before,'candidate_after':after,'source_before':source_before,'source_after':source_after,'payload_count':235,'retained_dependencies':231,'source_changes_by_reviewer':[],'ast_rows':rows,'physical_source_LOC':{'added':4,'removed':4},'new_test_LOC':0,'namespace_and_operation_IDs_retained':True,'imports':imports,'module_count':72,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'expected_ids':expected_ids,'executed_ids':result.executed_ids,'failure_details':[{'test_id':test.id(),'traceback':trace} for test,trace in result.failures+result.errors],'native_title_observations':observations,'observed_title_modules':sorted(observed),'Qt_platform':QApplication.instance().platformName(),'python_executable':sys.executable,'python_version':sys.version,'sys_prefix':sys.prefix,'command_argv':[sys.executable,'-B','-X','utf8',str(Path(__file__))],'raw_sha256':sha(R/'connected-desktop.txt'),'decision':'approved' if passed else 'rejected','exit_status':0 if passed else 1,'limits':['Same Windows host/principal; distinct author/reviewer actors','Actual Qt widgets using offscreen platform; no visible installed-launch/UI geometry qualification','Existing controlled owner/session/transport test fixtures retained; product positive-authority acceptance not inferred','Read-only claim conserves236 candidate members and235 active before payloads at endpoints; privileged simultaneous mutation not qualified','Exact display-name literals only; no namespace/record/operation/actor identity change','Source application and actual-destination verification remain coordinator actions']}
with (R/'connected-desktop.json').open('x',encoding='utf-8') as output:json.dump(report,output,indent=2);output.write('\n')
print(json.dumps({'decision':report['decision'],'exit_status':report['exit_status'],'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'actual_title_observations':len(observations),'observed_modules':sorted(observed),'proof_sha256':sha(R/'connected-desktop.json')}))
raise SystemExit(report['exit_status'])
