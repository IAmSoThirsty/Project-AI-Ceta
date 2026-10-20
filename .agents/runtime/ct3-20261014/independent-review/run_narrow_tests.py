"""Independent consumer and native metadata publication checks in reviewer-owned files."""
from ct3_support import *
import unittest,uuid,shutil
PUB=F/'.agents/runtime/rs2-20261014/apply_joined_source.py'
assert sha(PUB)=='4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
spec=importlib.util.spec_from_file_location('ct3_review_frozen_native_publisher',PUB);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
FIX=V/('native-review-'+uuid.uuid4().hex);fs.safe_components(FIX,allow_missing=True);FIX.mkdir(exist_ok=False)
owned=[]
def fresh(label):
 root=FIX/(label+'-'+uuid.uuid4().hex);root.mkdir(exist_ok=False);owned.append(str(root));return root
def put(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
def stage_pair(root,relative):
 target=root/'destination'/relative;stage=root/'staged'/relative;backup=root/'native-backups'/(relative+'.original');logical=root/'before'/(relative+'.source')
 before=(R/'before'/relative).read_bytes();after=(Q/relative).read_bytes()
 put(target,before);put(stage,after);put(logical,before);backup.parent.mkdir(parents=True,exist_ok=True)
 return target,stage,backup,logical,hashlib.sha256(before).hexdigest(),hashlib.sha256(after).hexdigest()
class NativeMetadataPublicationTests(unittest.TestCase):
 def test_two_native_json_replacements_retain_exact_original_bytes_and_identity(self):
  root=fresh('two-replacements')
  for relative in ('build/progress.json','handoff/continuity.json'):
   target,stage,backup,logical,before,candidate=stage_pair(root,relative);identity=ordinary(target)
   native.publish_prepared(stage,target,backup,before,candidate)
   self.assertEqual(ordinary(backup),identity);self.assertEqual(sha(backup),sha(logical));self.assertEqual(sha(target),candidate);self.assertFalse(stage.exists())
 def test_existing_target_drift_refuses_replacement_and_preserves_stage(self):
  root=fresh('target-drift');target,stage,backup,logical,before,candidate=stage_pair(root,'build/progress.json')
  with target.open('ab') as out:out.write(b'\n');out.flush();os.fsync(out.fileno())
  target_before=ordinary(target);stage_before=ordinary(stage)
  with self.assertRaisesRegex(AssertionError,'existing target drift'):native.publish_prepared(stage,target,backup,before,candidate)
  self.assertEqual(ordinary(target),target_before);self.assertEqual(ordinary(stage),stage_before);self.assertFalse(backup.exists());self.assertEqual(sha(logical),before)
 def test_staged_payload_drift_refuses_before_any_target_write(self):
  root=fresh('stage-drift');target,stage,backup,logical,before,candidate=stage_pair(root,'handoff/continuity.json')
  with stage.open('ab') as out:out.write(b'\n');out.flush();os.fsync(out.fileno())
  original=ordinary(target);altered=ordinary(stage)
  with self.assertRaisesRegex(AssertionError,'staged payload drift'):native.publish_prepared(stage,target,backup,before,candidate)
  self.assertEqual(ordinary(target),original);self.assertEqual(ordinary(stage),altered);self.assertFalse(backup.exists())
 def test_existing_native_backup_is_never_overwritten(self):
  root=fresh('backup-collision');target,stage,backup,logical,before,candidate=stage_pair(root,'build/progress.json');put(backup,b'existing owned recovery file\n')
  original=ordinary(target);preserved=ordinary(backup);pending=ordinary(stage)
  with self.assertRaisesRegex(AssertionError,'native backup already exists'):native.publish_prepared(stage,target,backup,before,candidate)
  self.assertEqual(ordinary(backup),preserved);self.assertEqual(ordinary(target),original);self.assertEqual(ordinary(stage),pending)
 def test_second_path_refusal_preserves_exact_first_publication_and_all_before_images(self):
  root=fresh('partial-transaction');first=stage_pair(root,'build/progress.json');second=stage_pair(root,'handoff/continuity.json');i1=ordinary(first[0]);i2=ordinary(second[0])
  native.publish_prepared(first[1],first[0],first[2],first[4],first[5])
  with second[0].open('ab') as out:out.write(b'\n');out.flush();os.fsync(out.fileno())
  changed_second=ordinary(second[0]);stage_second=ordinary(second[1])
  with self.assertRaisesRegex(AssertionError,'existing target drift'):native.publish_prepared(second[1],second[0],second[2],second[4],second[5])
  self.assertEqual(sha(first[0]),first[5]);self.assertEqual(ordinary(first[2]),i1);self.assertEqual(sha(first[3]),first[4])
  self.assertEqual(ordinary(second[0]),changed_second);self.assertEqual(ordinary(second[1]),stage_second);self.assertFalse(second[2].exists());self.assertEqual(sha(second[3]),i2['sha256'])

def flatten(suite):
 if isinstance(suite,unittest.TestSuite):
  for child in suite:yield from flatten(child)
 else:yield suite.id()
if __name__=='__main__':
 start=utc();m=Q/'TRANSFER-MANIFEST.json';assert sha(m)=='2773d204475a35934f3f0b80ef110126761b66fb74e9a6065c51f40e4c19de7e'
 manifest=read(m);source=read(F/manifest['source_suite']['repository_relative_path'])['after_hashes'];pre={k:ordinary(F/k) for k in source};qpre={i['relative_path']:ordinary(Q/i['relative_path']) for i in manifest['payloads']}
 fpre={i['relative_path']:ordinary(F/i['relative_path']) for i in manifest['payloads']}
 sys.path[:0]=[str(F/'src'),str(F/'tools'),str(F/'tests/contract')]
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromName('test_build_measurements'),unittest.defaultTestLoader.loadTestsFromTestCase(NativeMetadataPublicationTests)])
 expected=list(flatten(suite));executed=[];assert len(expected)==len(set(expected))==8
 class Result(unittest.TextTestResult):
  def startTest(self,test):executed.append(test.id());super().startTest(test)
 with (V/'consumer-native-tests.txt').open('x',encoding='utf-8',newline='\n') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
 post={k:ordinary(F/k) for k in source};qpost={i['relative_path']:ordinary(Q/i['relative_path']) for i in manifest['payloads']};fpost={i['relative_path']:ordinary(F/i['relative_path']) for i in manifest['payloads']}
 assert pre==post and qpre==qpost and fpre==fpost and sha(m)=='2773d204475a35934f3f0b80ef110126761b66fb74e9a6065c51f40e4c19de7e'
 proof={'executor':ACTOR,'started_at':start,'finished_at':utc(),'tests_run':result.testsRun,'expected_ids':expected,'executed_ids':executed,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'failed_details':[(t.id(),msg) for t,msg in result.failures+result.errors],'raw_output':ref(V/'consumer-native-tests.txt'),'native_primitive_sha256':sha(PUB),'fixture_root':str(FIX),'owned_fresh_children':owned,'fixture_files':[{'relative_path':p.relative_to(FIX).as_posix(),**ordinary(p)} for p in sorted(FIX.rglob('*')) if p.is_file()],'source286_native_before_after_equal':True,'candidate2_before_after_equal':True,'active_metadata2_before_after_equal':True,'owned_processes_launched':0,'owned_threads_launched':0,'qualification':'Three unchanged real Source consumer tests and five actual Windows native publication cases in own fixture tree; actual Root/F publication main not invoked; partial transaction intentionally retained with all before-images; no Source/E3/old fixture writes','exit_status':0 if result.wasSuccessful() and not result.skipped and executed==expected else 1}
 save(V/'consumer-native-tests.json',proof);print(json.dumps({'tests_run':result.testsRun,'exit_status':proof['exit_status'],'proof_sha256':sha(V/'consumer-native-tests.json')}));raise SystemExit(proof['exit_status'])
