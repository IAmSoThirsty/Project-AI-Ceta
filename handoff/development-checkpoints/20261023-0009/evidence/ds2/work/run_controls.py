"""Pure controls with work-only fixture writes and no native/process/socket entry."""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,socket,subprocess,sys,unittest
from unittest.mock import patch
W=Path(__file__).resolve().parent;sys.dont_write_bytecode=True
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
assert args.label.replace('-','').isalnum()
def deny(*a,**kw):raise AssertionError('DS1 controlled cohort forbids native/process/socket entry')
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.startfile','socket.__new__','ctypes.dlopen'):deny()
    if event=='open':
        path,mode,flags=args
        write=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if write and not isinstance(path,int):assert Path(path).resolve().is_relative_to(W),'out-of-scope write'
    if event=='os.mkdir':assert Path(args[0]).resolve().is_relative_to(W),'out-of-scope mkdir'
sys.addaudithook(audit)
guards=[patch(name,side_effect=deny) for name in ('ctypes.WinDLL','ctypes.CDLL','subprocess.run','subprocess.Popen','socket.socket')]
for guard in guards:guard.start()
import directory_snapshot as provider,test_directory_snapshot as tests
tests.FIXTURE_ROOT=W/'fixtures'/args.label
suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
def flatten(s):
    for x in s:
        if isinstance(x,unittest.TestSuite):yield from flatten(x)
        else:yield x
selected=[x.id() for x in flatten(suite)];assert len(selected)==len(set(selected))
class Result(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.started=[];self.stopped=[]
    def startTest(self,test):self.started.append(test.id());super().startTest(test)
    def stopTest(self,test):self.stopped.append(test.id());super().stopTest(test)
with (W/(args.label+'.unittest.log')).open('x',encoding='utf8') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
value=dict(selected=selected,started=r.started,stopped=r.stopped,tests_run=r.testsRun,
    failures=[dict(test=t.id(),trace=trace) for t,trace in r.failures],errors=[dict(test=t.id(),trace=trace) for t,trace in r.errors],
    skips=[dict(test=t.id(),reason=reason) for t,reason in r.skipped],successful=r.wasSuccessful(),
    module_path=str(Path(provider.__file__).resolve()),module_sha256=hashlib.sha256(Path(provider.__file__).read_bytes()).hexdigest(),
    legacy_source_sha256=provider.LEGACY_SHA,native_effects=False,work_only_fixtures=True,product_acceptance=False)
with (W/(args.label+'.json')).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(tests_run=r.testsRun,successful=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped))))
raise SystemExit(0 if r.wasSuccessful() and not r.skipped and selected==r.started==r.stopped else 1)
