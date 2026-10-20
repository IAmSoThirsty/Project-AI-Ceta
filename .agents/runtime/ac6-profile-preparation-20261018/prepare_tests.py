"""Adapt the frozen prior reviewer controls; execute no tests here."""
from pathlib import Path
import hashlib
F=Path('T:/00-Active/Project-AI-CETA'); R=Path(__file__).resolve().parent
original=F/'.agents/runtime/ac5-profile-tool-review2-20261015/run_independent.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=original.read_text()
s=s.replace("R = F / '.agents/runtime/ac5-profile-tool-20261015'", "R = F / '.agents/runtime/ac6-profile-preparation-20261018'")
s=s.replace("D = Path(__file__).resolve().parent", "D = Path(__file__).resolve().parent / 'controlled-r1'\nD.mkdir(exist_ok=False)")
s=s.replace("assert D == F / '.agents/runtime/ac5-profile-tool-review2-20261015'", "assert D == R / 'controlled-r1'")
s=s.replace('530238cbb5d5601802e96864a085a4d4becb0d0d045e3bf13286b5718b7d9a6e',sha(R/'profile_qualification.py'))
s=s.replace('372a14a567ddecc4ccb67848669afe641d71ebc7b1d66aaad4dcaa0b5b709570',sha(R/'run_one_approved_attempt_v2.py'))
s=s.replace('PROFILE-CREATION-PROPOSAL-AC5.json','PROFILE-CREATION-PROPOSAL-AC6.json').replace('320b5dcc8bb807fad97b46a34faf8be25ed55423afa5d8e81d977947a02d4163',sha(R/'PROFILE-CREATION-PROPOSAL-AC6.json'))
s=s.replace("'CreateProcessAsUserW', 'CreateProcessWithTokenW', 'CreateProcessWithLogonW'", "'CreateProcessAsUserW', 'CreateProcessWithTokenW', 'CreateProcessWithLogonW', 'SetNamedSecurityInfoW', 'SetTokenInformation', 'AdjustTokenPrivileges'")
s=s.replace("    for base, directories, files in os.walk(root, followlinks=False):", "    for base, directories, files in os.walk(root, followlinks=False):\n        directories[:] = [name for name in directories if Path(base)/name != D]")
s=s.replace("module.Q / 'TRANSFER-MANIFEST.json'", 'module.SOURCE_BASELINE')
start=s.index('parent_tree = ast.parse('); end=s.index('# Test controls only:',start)
s=s[:start]+'''parent_tree = ast.parse((F / '.agents/runtime/ac5-profile-tool-20261015/profile_qualification.py').read_text())
tool_tree = ast.parse((R / 'profile_qualification.py').read_text())
dump = lambda node: ast.dump(node, include_attributes=False)
parent_funcs = {n.name: n for n in parent_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
tool_funcs = {n.name: n for n in tool_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
for name in ('validate_operator_record', 'assert_isolation', 'describe', 'inspect', 'folder', 'user_sid'):
    assert dump(parent_funcs[name]) == dump(tool_funcs[name]), name
old_methods = {n.name: n for n in parent_funcs['_QualificationRun'].body if isinstance(n, ast.FunctionDef)}
new_methods = {n.name: n for n in tool_funcs['_QualificationRun'].body if isinstance(n, ast.FunctionDef)}
changed_methods = [name for name in old_methods if dump(old_methods[name]) != dump(new_methods[name])]
assert changed_methods == ['snapshot']
assert dump(old_methods['snapshot']).replace('Source290_native_and_hash_conserved','Source352_native_and_hash_conserved').replace('candidate295_native_and_hash_conserved','execution_source352_native_and_hash_conserved') == dump(new_methods['snapshot'])
original_native_path = module._native_path
native_controls = []
def controlled_native_path(path, *, directory):
    native_controls.append({'path':str(path),'directory':directory,'classification':'CONTROLLED_PATH_NOT_NATIVE_OBSERVATION'})
    return r'\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\ac6' + ('' if directory else r'\\assets\\isolated_worker.exe')
def controlled_inspect():
    return {'name':module.NAME,'SID':module.SID,'user_sid':module.USER,'native_Create_or_Delete_executed':False,'activation_ready':False,
            'prior_folder':{'HRESULT':-2147024894,'path':None},'classification':'CONTROLLED_INSPECTION_NOT_HOST_OBSERVATION'}
''' + s[end:]
s=s.replace("negative_path = R / 'test_profile_qualification.py'", "negative_path = F / '.agents/runtime/ac5-profile-tool-20261015/test_profile_qualification.py'")
s=s.replace('source_count=290','source_count=352').replace('range(295)','range(352)').replace("profile-qualification-SYNTHETIC","q-SYNTHETIC")
# Preserve every prior method; only fixture data/counts/paths above change.
idx=s.index('families = [')
extra=r'''
class CurrentSourceAndPathTests(unittest.TestCase):
    def test_execution_view_is_canonical_source352(self):
        self.assertEqual(module.Q, F)
        self.assertEqual(len(module.FROZEN),352)
        self.assertEqual(module.source_cut(),module.candidate_cut())
        self.assertEqual(Path(module.module.__file__).resolve(),(F/'src/ceta/supervisor/isolated_worker.py').resolve())
    def test_source_identity_drift_is_rejected(self):
        original=module.capture
        def changed(path,*args):
            if Path(path)==F/'src/ceta/supervisor/isolated_worker.py':raise AssertionError('CONTROLLED_SOURCE_IDENTITY_DRIFT')
            return original(path,*args)
        with patch.object(module,'capture',changed):
            with self.assertRaisesRegex(AssertionError,'CONTROLLED_SOURCE_IDENTITY_DRIFT'):module.source_cut()
    def test_projected_overlength_denies_before_copy(self):
        path=D/('long-layout-'+uuid.uuid4().hex)
        with patch.object(module,'_native_path',lambda *a,**k:'X'*230),patch.object(module,'write_payload') as write:
            with self.assertRaisesRegex(AssertionError,'PROBE_NATIVE_PATH_TOO_LONG'):module.prepare_probe(path)
            write.assert_not_called()
    def test_actual_image_overlength_denies_receipt(self):
        path=D/('long-image-'+uuid.uuid4().hex);path.mkdir()
        with patch.object(module,'_native_path',side_effect=['X'*180,'X'*258]):
            with self.assertRaisesRegex(AssertionError,'PROBE_NATIVE_PATH_TOO_LONG'):module.check_launch_paths(path,path/'image.exe')
        self.assertFalse((path/'LAUNCH-PATHS.json').exists())
    def test_projected_and_actual_receipts_are_distinct(self):
        path=D/('path-rows-'+uuid.uuid4().hex);path.mkdir()
        projected=module.check_launch_paths(path)
        actual=module.check_launch_paths(path,path/'image.exe')
        self.assertTrue(projected['predicted_fixture_suffix']);self.assertFalse(actual['predicted_fixture_suffix'])
        self.assertLess(projected['native_image_length'],258)
        self.assertFalse(actual['qualification_claim']);self.assertFalse(actual['missing_profile_causality_claim'])
    def test_native_reader_primary_reaches_canonical_cleanup(self):
        path=D/('path-primary-'+uuid.uuid4().hex);path.mkdir()
        primary=RuntimeError('CONTROLLED_PATH_PRIMARY');queued=[];finished=[]
        api=types.SimpleNamespace(CreateFileW=lambda *a:4321,queue_handle=queued.append,native_volume_path=lambda h:(_ for _ in ()).throw(primary))
        with patch.object(module.module,'_IsolationAPI',lambda:api),patch.object(module.module,'_finish_cleanup',lambda a,p:finished.append((a,p))):
            with self.assertRaises(RuntimeError) as caught:original_native_path(path,directory=True)
        self.assertIs(caught.exception,primary);self.assertEqual(queued,[4321]);self.assertEqual(finished,[(api,primary)])
    def test_captured_driver_checks_paths_before_api_and_launch(self):
        directory=D/('driver-guard-'+uuid.uuid4().hex)
        helper=module.prepare_probe(directory)
        self.assertIs(helper.check_launch_paths,module.check_launch_paths)
        body=ast.parse((directory/'native_fixture_support.py').read_text())
        run=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='run_native_probe')
        statements=[ast.unparse(n) for n in run.body]
        self.assertTrue(statements[1].startswith('check_launch_paths(fixture, image)'))
        self.assertTrue(statements[2].startswith('control, api ='))
    def test_full_uuid_short_attempt_directory_and_unchanged_validator(self):
        function=tool_funcs['qualify']
        self.assertIn("'q-' + uuid.uuid4().hex",ast.unparse(function))
        self.assertEqual(dump(parent_funcs['validate_operator_record']),dump(tool_funcs['validate_operator_record']))

'''
s=s[:idx]+extra+s[idx:]
s=s.replace('AdditionalSerializationTests, WrapperNegativeTests]', 'AdditionalSerializationTests, WrapperNegativeTests, CurrentSourceAndPathTests]')
s=s.replace('== 49','== 57')
s=s.replace("if event in ('subprocess.Popen', 'os.system', 'os.startfile'):", "if event in ('subprocess.Popen', 'os.system', 'os.startfile', 'socket.connect', 'socket.bind'):")
s=s.replace("with patch.object(ctypes, 'WinDLL', guarded_dll), (D / 'independent-r1.txt').open('x', encoding='utf8') as output:", "with patch.object(ctypes, 'WinDLL', guarded_dll), patch.object(module,'_native_path',controlled_native_path), patch.object(module,'inspect',controlled_inspect), (D / 'independent-r1.txt').open('x', encoding='utf8') as output:")
s=s.replace("R.glob('profile-qualification-*')", "R.glob('q-*')")
s=s.replace("'source290_native_and_hash_exact': True", "'source352_native_and_hash_exact': True").replace("'candidate295_native_and_hash_exact': True", "'execution_source352_native_and_hash_exact': True")
s=s.replace("'at': utc(), 'tool_sha256': TOOL, 'wrapper_sha256': WRAPPER,", "'at': utc(), 'actor':'/root/native_denial_diagnosis', 'review_type':'AUTHOR_CONTROLLED_CHECKS_NOT_INDEPENDENT', 'new_source_path_methods':8, 'native_path_controls':native_controls, 'host_inspection':'CONTROLLED', 'tool_sha256': TOOL, 'wrapper_sha256': WRAPPER,")
s=s.replace("'Same-host independent actor, no external attestation'", "'Author controlled checks, no independent approval; prior methods retained with explicit synthetic profile/path fixtures'")
with (R/'test_ac6_controlled.py').open('x',encoding='utf8',newline='\n') as o:o.write(s)
print(sha(R/'test_ac6_controlled.py'))
