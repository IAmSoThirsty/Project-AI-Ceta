"""Disposable controls for exact status preservation and complete policy snapshot."""
from pathlib import Path
import json,os,sys,unittest,stat
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import patch
import status_core as s
ROOT=s.W/'controls-r6';ROOT.mkdir(exist_ok=False)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
import taar.orchestration_runtime as stock
class Controls(unittest.TestCase):
 def setUp(self):
  self.p=ROOT/self._testMethodName;self.p.mkdir()
 def test_root_denied_is_not_empty(self):
  with patch.object(s.os,'scandir',side_effect=PermissionError('ROOT_DENIED')):
   with self.assertRaises(PermissionError):s.snapshot(self.p,self.p)
 def test_nested_denied_is_not_omitted(self):
  (self.p/'child').mkdir();original=os.scandir
  def guarded(path):
   if str(path).endswith('child'):raise PermissionError('NESTED_DENIED')
   return original(path)
  with patch.object(s.os,'scandir',guarded):
   with self.assertRaises(PermissionError):s.snapshot(self.p,self.p)
 def test_empty_directories_are_observed(self):
  (self.p/'empty').mkdir();o=s.snapshot(self.p,self.p);self.assertEqual(set(o['directories']),{'.','empty'});self.assertEqual(o['files'],{})
 def test_ignored_directories_are_explicit(self):
  (self.p/'.agents').mkdir();(self.p/'.agents'/'hidden').write_bytes(b'x');(self.p/'visible').write_bytes(b'y')
  o=s.snapshot(self.p,self.p);self.assertEqual(set(o['files']),{'visible'});self.assertEqual(o['policy']['ignored_directory_names'],sorted(stock.IGNORED_DIR_NAMES))
 def test_ignored_name_regular_file_is_not_ignored(self):
  (self.p/'.agents').write_bytes(b'x');self.assertEqual(set(s.snapshot(self.p,self.p)['files']),{'.agents'})
 def test_stock_file_hash_compatibility(self):
  (self.p/'child').mkdir();(self.p/'child'/'x').write_bytes(b'payload');(self.p/'empty').mkdir()
  self.assertEqual(s.file_map(s.snapshot(self.p,self.p)),stock._snapshot_workspace(self.p,self.p))
 def test_project_automation_policy(self):
  p=self.p/'.project-ai'/'automation';p.mkdir(parents=True);(p/'x').write_bytes(b'x');(self.p/'.project-ai'/'visible').write_bytes(b'y')
  self.assertEqual(s.file_map(s.snapshot(self.p,self.p)),stock._snapshot_workspace(self.p,self.p))
 def test_long_windows_file_observed(self):
  p=self.p
  while len(str(p))<310:p=p/'abcdefghijklmno';s.physical(p).mkdir()
  q=p/'long.txt';s.physical(q).write_bytes(b'long');o=s.snapshot(self.p,self.p);self.assertEqual(o['files'][q.relative_to(self.p).as_posix()]['sha256'],s.sha(s.physical(q)));self.assertEqual(s.sha(q),s.sha(s.physical(q)))
 def test_unignored_reparse_refused(self):
  (self.p/'x').write_bytes(b'x');original=os.lstat
  def guarded(path):
   info=original(path)
   if str(path).endswith('x'):
    class Reparse:
     st_file_attributes=0x400
     st_mode=stat.S_IFREG
    return Reparse()
   return info
  with patch.object(s.os,'lstat',guarded):
   with self.assertRaisesRegex(AssertionError,'reparse'):s.snapshot(self.p,self.p)
 def test_file_mutation_during_read_refused(self):
  q=self.p/'x';q.write_bytes(b'x');original=s.native;seen=0
  def native(path):
   nonlocal seen
   value=original(path)
   if Path(path)==q:
    seen+=1
    if seen==2:value['mtime_ns']+=1
   return value
  with patch.object(s,'native',native):
   with self.assertRaisesRegex(AssertionError,'file changed'):s.stable(q)
 def test_directory_mutation_during_enumeration_refused(self):
  original=s.native;seen=0
  def native(path):
   nonlocal seen
   value=original(path)
   if Path(path)==self.p:
    seen+=1
    if seen==2:value['mtime_ns']+=1
   return value
  with patch.object(s,'native',native):
   with self.assertRaisesRegex(AssertionError,'directory changed'):s.snapshot(self.p,self.p)
 def test_historical_json_values_preserved(self):
  old={'halt':{'state':'PAUSED'},'failures':[{'state':'FAILED'}]};s.preserve_json(old,{**old,'current':'ACTIVE'})
  with self.assertRaises(AssertionError):s.preserve_json(old,{'halt':{'state':'ACTIVE'},'failures':old['failures']})
 def test_removed_historical_field_refused(self):
  with self.assertRaises(AssertionError):s.preserve_json({'halt':False},{})
 def test_strict_constructor_only_hash_changes(self):
  a='a'*64;b='b'*64;old=('_GATE_SHA = '+chr(34)+a+chr(34)+'\nPUBLIC=1\n').encode();new=s.constructor_successor(old,a,b)
  self.assertEqual(new.replace(b.encode(),a.encode()),old)
 def test_constructor_nonunique_or_removed_pin_refused(self):
  with self.assertRaises(AssertionError):s.constructor_successor(b'PUBLIC=1','a'*64,'b'*64)
 @contextmanager
 def hook_context(self,review='approved',validation=True):
  state=dict(run_id=s.RUN,graph_fingerprint='g',nodes=dict(implement=dict(executor_id='/root'),review=dict(state='SUCCEEDED',decision=review,executor_id='/root/reviewer'),validate=dict(state='SUCCEEDED',validation_passed=validation)))
  binding=dict(graph_fingerprint='g',runtime_sha256=s.sha(Path(stock.__file__)));original=Path.read_bytes
  def read(path):
   if path==s.W/'BINDING.json':return json.dumps(binding).encode()
   if path==s.S/'control'/s.RUN/'state.json':return json.dumps(state).encode()
   return original(path)
  with patch.object(Path,'read_bytes',read),patch('taar.orchestration_graph.compile_graph',return_value=SimpleNamespace(root=str(s.F),fingerprint='g')):yield
 def test_hook_restores_after_normal_body(self):
  original=stock._snapshot_workspace
  with self.hook_context(),s.qualified_runtime() as runtime:self.assertIs(runtime,stock);self.assertIsNot(stock._snapshot_workspace,original)
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_restores_original_body_exception(self):
  original=stock._snapshot_workspace;primary=RuntimeError('ORIGINAL_BODY')
  try:
   with self.hook_context(),s.qualified_runtime():raise primary
  except RuntimeError as caught:self.assertIs(caught,primary)
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_tamper_restores_and_retains_body_exception(self):
  original=stock._snapshot_workspace;primary=RuntimeError('ORIGINAL_BODY')
  try:
   with self.hook_context(),s.qualified_runtime():stock._snapshot_workspace=lambda *a:{};raise primary
  except RuntimeError as caught:
   self.assertIs(caught,primary);self.assertIn('STATUS_SNAPSHOT_HOOK_CHANGED',str(vars(caught)['ceta_status_snapshot_secondary_error']))
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_tamper_without_body_error_fails(self):
  original=stock._snapshot_workspace
  with self.assertRaisesRegex(RuntimeError,'STATUS_SNAPSHOT_HOOK_CHANGED'):
   with self.hook_context(),s.qualified_runtime():stock._snapshot_workspace=lambda *a:{}
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_rejects_wrong_graph_root(self):
  original=stock._snapshot_workspace
  with self.hook_context(),s.qualified_runtime():
   with self.assertRaisesRegex(AssertionError,'unexpected graph root'):stock._snapshot_workspace(s.F,s.F.parent)
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_other_workspaces_keep_stock_semantics(self):
  (self.p/'x').write_bytes(b'x');expected=stock._snapshot_workspace(self.p,self.p)
  with self.hook_context(),s.qualified_runtime():self.assertEqual(stock._snapshot_workspace(self.p,self.p),expected)
 def test_hook_rejects_unapproved_review(self):
  original=stock._snapshot_workspace
  with self.hook_context(review='rejected'):
   with self.assertRaises(AssertionError):
    with s.qualified_runtime():pass
  self.assertIs(stock._snapshot_workspace,original)
 def test_hook_rejects_failed_gate(self):
  original=stock._snapshot_workspace
  with self.hook_context(validation=False):
   with self.assertRaises(AssertionError):
    with s.qualified_runtime():pass
  self.assertIs(stock._snapshot_workspace,original)
 def test_boolean_integer_substitution_rejected(self):
  with self.assertRaises(AssertionError):s.preserve_json({'state':False},{'state':0})
 def test_integer_float_nested_substitution_rejected(self):
  with self.assertRaises(AssertionError):s.preserve_json({'rows':[{'value':1}]},{'rows':[{'value':1.0}]})
 def test_typed_json_equal_copy_preserved(self):
  old={'values':[None,False,0,1.0,'x',{'a':[True]}]};s.preserve_json(old,json.loads(json.dumps(old)))
 def test_application_diagnostic_fault_keeps_original(self):
  primary=KeyboardInterrupt('ORIGINAL_PARTIAL_APPLICATION');fault=RuntimeError('DIAGNOSTIC_FAULT')
  def describe(error):raise fault
  try:
   with s.application_journal(self.p/'ops.jsonl',describe):raise primary
  except KeyboardInterrupt as caught:
   self.assertIs(caught,primary);self.assertIs(vars(caught)['ceta_status_application_primary_exc_info'][1],primary);self.assertIn(fault,vars(caught)['ceta_status_application_secondary_errors'])
 def test_application_close_fault_keeps_original(self):
  primary=KeyboardInterrupt('ORIGINAL_PARTIAL_APPLICATION');fault=OSError('CLOSE_FAULT');path=self.p/'ops.jsonl';stream=path.open('xb');original=Path.open
  class Wrapper:
   def write(self,data):return stream.write(data)
   def flush(self):return stream.flush()
   def fileno(self):return stream.fileno()
   def close(self):stream.close();raise fault
  def open_file(p,*a,**kw):return Wrapper() if p==path else original(p,*a,**kw)
  try:
   with patch.object(Path,'open',open_file),s.application_journal(path,lambda error:{'type':'KeyboardInterrupt'}):raise primary
  except KeyboardInterrupt as caught:self.assertIs(caught,primary);self.assertIn(fault,vars(caught)['ceta_status_application_secondary_errors'])
  self.assertTrue(stream.closed)
 def test_application_event_fault_keeps_original(self):
  primary=KeyboardInterrupt('ORIGINAL_PARTIAL_APPLICATION');fault=OSError('EVENT_WRITE_FAULT');path=self.p/'ops.jsonl';stream=path.open('xb');original=Path.open
  class Wrapper:
   def write(self,data):raise fault
   def flush(self):return stream.flush()
   def fileno(self):return stream.fileno()
   def close(self):return stream.close()
  def open_file(p,*a,**kw):return Wrapper() if p==path else original(p,*a,**kw)
  try:
   with patch.object(Path,'open',open_file),s.application_journal(path,lambda error:{'type':'KeyboardInterrupt'}):raise primary
  except KeyboardInterrupt as caught:self.assertIs(caught,primary);self.assertIn(fault,vars(caught)['ceta_status_application_secondary_errors'])
 def test_application_prior_progress_retained_on_failure(self):
  path=self.p/'ops.jsonl';primary=RuntimeError('PARTIAL')
  with self.assertRaises(RuntimeError):
   with s.application_journal(path,lambda error:{'type':'RuntimeError'}) as event:event('ONE_TARGET_APPLIED');raise primary
  rows=[json.loads(line) for line in path.read_text().splitlines()];self.assertEqual([row['kind'] for row in rows],['ONE_TARGET_APPLIED','APPLICATION_FAILURE']);self.assertTrue(rows[-1]['partial_bytes_preserved'])
 def hostile(self):
  class Original(KeyboardInterrupt):
   def __setattr__(self,name,value):raise RuntimeError('STATUS_HOSTILE_ATTRIBUTE_ASSIGNMENT_'+name)
  return Original('EXACT_ORIGINAL_INTERRUPTION')
 def test_application_hostile_original_automatic_propagation(self):
  primary=self.hostile();caught=None
  try:
   with s.application_journal(self.p/'ops.jsonl',lambda error:{'type':'Original'}):raise primary
  except BaseException as error:caught=error
  self.assertIs(caught,primary);storage=BaseException.__dict__['__dict__'].__get__(primary);self.assertIs(storage['ceta_status_application_primary_exc_info'][1],primary);self.assertIsNotNone(storage['ceta_status_application_primary_exc_info'][2]);self.assertEqual(storage['ceta_status_application_secondary_errors'],())
 def test_application_hostile_original_with_diagnostic_and_close_faults(self):
  primary=self.hostile();diagnostic=ValueError('DIAGNOSTIC_FAULT');close=OSError('CLOSE_FAULT');path=self.p/'ops.jsonl';stream=path.open('xb');original=Path.open;caught=None
  class Wrapper:
   def write(self,data):return stream.write(data)
   def flush(self):return stream.flush()
   def fileno(self):return stream.fileno()
   def close(self):stream.close();raise close
  def open_file(p,*a,**kw):return Wrapper() if p==path else original(p,*a,**kw)
  def describe(error):raise diagnostic
  with patch.object(Path,'open',open_file):
   try:
    with s.application_journal(path,describe):raise primary
   except BaseException as error:caught=error
  self.assertIs(caught,primary);storage=BaseException.__dict__['__dict__'].__get__(primary);self.assertEqual(storage['ceta_status_application_secondary_errors'],(diagnostic,close));self.assertTrue(stream.closed)
 def test_application_hostile_close_only_is_not_success(self):
  close=self.hostile();path=self.p/'ops.jsonl';stream=path.open('xb');original=Path.open;caught=None
  class Wrapper:
   def write(self,data):return stream.write(data)
   def flush(self):return stream.flush()
   def fileno(self):return stream.fileno()
   def close(self):stream.close();raise close
  def open_file(p,*a,**kw):return Wrapper() if p==path else original(p,*a,**kw)
  with patch.object(Path,'open',open_file):
   try:
    with s.application_journal(path,lambda error:{}):pass
   except BaseException as error:caught=error
  self.assertIs(caught,close);self.assertTrue(stream.closed)
 def test_hook_hostile_original_automatic_propagation(self):
  primary=self.hostile();original=stock._snapshot_workspace;caught=None;guard=self.hook_context();guard.__enter__()
  try:
   try:
    with s.qualified_runtime():raise primary
   except BaseException as error:caught=error
  finally:guard.__exit__(None,None,None)
  self.assertIs(caught,primary);self.assertIs(stock._snapshot_workspace,original);self.assertIsNotNone(BaseException.__dict__['__dict__'].__get__(primary)['ceta_status_snapshot_primary_exc_info'][2])
 def test_hook_hostile_original_and_tamper_both_retained(self):
  primary=self.hostile();original=stock._snapshot_workspace;caught=None;guard=self.hook_context();guard.__enter__()
  try:
   try:
    with s.qualified_runtime():stock._snapshot_workspace=lambda *args:{};raise primary
   except BaseException as error:caught=error
  finally:guard.__exit__(None,None,None)
  self.assertIs(caught,primary);self.assertIs(stock._snapshot_workspace,original);errors=BaseException.__dict__['__dict__'].__get__(primary)['ceta_status_snapshot_secondary_errors'];self.assertEqual(len(errors),1);self.assertIn('STATUS_SNAPSHOT_HOOK_CHANGED',str(errors[0]))
 def test_hook_hostile_setup_failure_keeps_original(self):
  primary=self.hostile();original=stock._snapshot_workspace;read=Path.read_bytes;caught=None
  def guarded(path):
   if path==s.W/'BINDING.json':raise primary
   return read(path)
  with patch.object(Path,'read_bytes',guarded):
   try:
    with s.qualified_runtime():self.fail('body must not run')
   except BaseException as error:caught=error
  self.assertIs(caught,primary);self.assertIs(stock._snapshot_workspace,original)
with (ROOT/'TESTS.log').open('x',encoding='utf-8') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
s.save(ROOT/'RESULT.json',dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped),successful=r.wasSuccessful(),scope='DISPOSABLE_QUALIFICATION_CONTROLS_ONLY',tested_core_sha256=s.sha(s.W/'status_core.py'),canonical_writes=False,full_product_acceptance=False))
print(json.dumps(dict(success=r.wasSuccessful(),tests=r.testsRun,failures=len(r.failures),errors=len(r.errors))))
raise SystemExit(0 if r.wasSuccessful() else 1)
