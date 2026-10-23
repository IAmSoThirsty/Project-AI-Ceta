"""Retain exact current disposable control IDs, source bytes and process outcome."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
W=Path(__file__).resolve().parent
sources=('complete_observer.py','bound_runtime.py','run_broader.py','test_br_controls.py','run_controls.py')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if '--worker' in sys.argv:
    before={name:sha(W/name) for name in sources}
    suite=unittest.defaultTestLoader.loadTestsFromName('test_br_controls.Controls');ids=[t.id() for t in suite]
    class Result(unittest.TextTestResult):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.started=[];self.stopped=[]
        def startTest(self,t):self.started.append(t.id());super().startTest(t)
        def stopTest(self,t):self.stopped.append(t.id());super().stopTest(t)
    result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2,resultclass=Result).run(suite)
    after={name:sha(W/name) for name in sources}
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        successful=result.wasSuccessful(),selected=ids,started=result.started,stopped=result.stopped,
        source_before=before,source_after=after,canonical_test_bodies_executed=False,canonical_fixture_writes=False,
        only_disposable_controls=True,full_product_acceptance=False)
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() and not result.skipped and ids==result.started==result.stopped and before==after else 1)
assert len(sys.argv)==2 and sys.argv[1].replace('-','').isalnum()
label=sys.argv[1]
completed=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'--worker'],cwd=W,
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false'),capture_output=True)
for suffix,raw in [('stdout',completed.stdout),('stderr',completed.stderr)]:
    with (W/(label+'.'+suffix)).open('xb') as stream:stream.write(raw)
report=json.loads(completed.stdout.decode());report['process_exit_status']=completed.returncode
with (W/(label+'.json')).open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ('tests','failures','errors','skips','successful','process_exit_status')}))
raise SystemExit(completed.returncode)
