"""Read-only corrected admission and exact frozen-source adoption verification."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/ds2';W=B/'work';C=B/'control-r2';R=B/'review-r2';OLD=B/'review';RUN='ceta-ds23-r2-gate-r2';PIN='736a2a3ef8639bf99acced85d0ce3950b74b01bf9f23d856148ca7a7061df2f6';GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed';HELPER='f17cd2b8214f9076cdcfa87683253a5a486bbd31c6d41d2f4887dd0cd9ccd858'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import directory_snapshot as d,conservation
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import OrchestrationRuntime
s=d.legacy;assert s.sha(W/'MANIFEST.json')==PIN and s.sha(C/'ROOT-CLOSE-QUALIFICATION-R2.py')==HELPER
m=json.loads((W/'MANIFEST.json').read_bytes());assert len(m['files'])==46
for rel,pin in m['files'].items():assert s.stable(W/rel)==pin
for path,pin in m['external_pins'].items():assert s.sha(Path(path))==pin
old=json.loads((OLD/'MANIFEST.json').read_bytes());assert s.sha(OLD/'MANIFEST.json')=='93b8e85d476c16e11ad434b9ac4df5e8483aa78dbfc571db9900d3a0c27f7fe0' and old['decision']=='rejected'
for rel,pin in old['files'].items():assert s.sha(OLD/rel)==pin
for path,pin in old['external_pins'].items():assert s.sha(Path(path))==pin
old_runtime=OrchestrationRuntime(B/'control');ov=old_runtime.verify('ceta-ds23-r2');assert ov['receipts_valid'] and ov['states']['review']=='FAILED' and ov['terminal_success'] is False
packet_path=B/'packet-r2/INPUTS.json';amend_path=B/'packet-r2/ROOT-CLOSURE-RELOCATION-AMENDMENT.json';packet=json.loads(packet_path.read_bytes());amend=json.loads(amend_path.read_bytes())
assert s.sha(packet_path)=='3d249901dc59431ffe30d25a44996a01400b7bcf3ab91415922a74b1813dccc7'
assert s.sha(amend_path)=='83713b152c26a24624ec6de6ef3243a58b8b1bd6303fa3a2092a1b369292a658'
for path,pin in packet['source_inputs'].items():assert s.sha(Path(path))==pin
assert amend['original_packet_sha256']==s.sha(packet_path) and amend['successor_helper']['sha256']==HELPER and Path(amend['successor_helper']['path'])==C/'ROOT-CLOSE-QUALIFICATION-R2.py'
assert amend['original_helper']['state']=='UNEXECUTED_NOT_APPROVED' and s.sha(Path(amend['original_helper']['path']))==amend['original_helper']['sha256']
assert s.sha(W/'complete_candidate.py')=='64f81f235284f4a1e6222c09c407e1ff4a25acc96412fee7b71d27bdf97703ad'
graph=compile_graph(Path('T:/'),C);assert graph.fingerprint==GRAPH and graph.nodes['implement']['access']=='read_only' and 'write_scope' not in graph.nodes['implement']
python=json.loads((F/'.agents/runtime/oq23/st2/packet/INPUTS.json').read_bytes())['python'];expected=subprocess.list2cmdline([python,'-E','-B','-X','utf8',str(W/'verify_prepared.py')]);assert graph.nodes['validate']['commands']==[expected] and packet['exact_gate_command']==expected
assert graph.nodes['review']['write_scope']==['00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/review-r2/**'] and graph.nodes['integrate']['write_scope']==['00-Active/Project-AI-CETA/.agents/runtime/oq23/ds2/delivery/**']
adoption=json.loads((C/'ADOPTION-RECEIPT.json').read_bytes());assert s.sha(C/'ADOPTION-RECEIPT.json')=='b3c2d6a7c2f79d1d822a127acd3acca691edb58c2458c03d1c52cd63d80c65d4';assert adoption['changed_files']==[] and adoption['run_id']==RUN
ar=adoption['result'];assert ar['manifest_sha256']==PIN and ar['provider_sha256']==m['provider_sha256'] and ar['controls']==50 and ar['controls_rerun'] is False and ar['full_F_snapshot_replayed'] is False
assert ar['root_closure_relocation_amendment_sha256']==s.sha(amend_path) and ar['successor_root_candidate_closure_sha256']==HELPER
for path,pin in ar['source_and_rejection_input_pins'].items():assert s.sha(Path(path))==pin
assert s.sha(Path(ar['preserved_author_pin_assertion_failure']['path']))==ar['preserved_author_pin_assertion_failure']['sha256']
persisted=json.loads((C/RUN/'receipts/implement.json').read_bytes());assert persisted['receipt_hash']=='3e6cb75417624e25a0fb4f731a01f2a0facd495fb5fedab322ce60c6d11aad1b'
assert s.sha(C/RUN/'receipts/implement.json')=='f808d74ff706578cb6d6cca9936da673ba60addc2349d475427f71a667426160'
assert s.same_json(persisted['result'],ar) and persisted['changed_files']==[]
rt=OrchestrationRuntime(C);v=rt.verify(RUN);assert v['receipts_valid'] and v['states']['implement']=='SUCCEEDED' and v['states']['review']=='RUNNING'
state=json.loads((C/RUN/'state.json').read_bytes());assert state['nodes']['implement']['claim'] is None
prior_controls=json.loads((OLD/'INDEPENDENT-REPAIR-CONTROLS.json').read_bytes());assert prior_controls['case_count']==6 and prior_controls['all_passed']
assert not any((B/'delivery').iterdir()) and not (C/'ROOT-QUALIFICATION-COMPLETION.json').exists()
# The relocation amendment changes only the exact import path and origin assertion.
original=(C/'ROOT-CLOSE-QUALIFICATION.py').read_text(encoding='utf8');successor=(C/'ROOT-CLOSE-QUALIFICATION-R2.py').read_text(encoding='utf8')
expected_successor=original.replace("    import verify_prepared\n","    sys.path.insert(0,str(W))\n    import verify_prepared\n    assert Path(verify_prepared.__file__).resolve()==(W/'verify_prepared.py').resolve()\n")
assert successor==expected_successor,'unrelated relocation helper edit'
# Run the exact import-origin statements only, without main or a verifier body call.
main=next(node for node in ast.parse(successor).body if isinstance(node,ast.FunctionDef) and node.name=='main')
start=next(index for index,node in enumerate(main.body) if isinstance(node,ast.Expr) and ast.unparse(node)=='sys.path.insert(0, str(W))')
ports=dict(sys=sys,W=W,Path=Path);exec(compile(ast.Module(body=main.body[start:start+3],type_ignores=[]),'exact relocated verifier import-origin statements','exec'),ports);assert Path(ports['verify_prepared'].__file__).resolve()==(W/'verify_prepared.py').resolve()
now=conservation.observe()
report=dict(classification='INDEPENDENT_CORRECTED_ADMISSION_READBACK_NO_REPLAY',candidate_manifest_sha256=PIN,graph_fingerprint=GRAPH,root_candidate_closure_sha256=HELPER,relocation_amendment_sha256=s.sha(amend_path),frozen_files_reread=46,external_pins_reread=len(m['external_pins']),old_review_files_reread=len(old['files']),old_review_external_pins_reread=len(old['external_pins']),old_DS2_actual_rejection_preserved=True,exact_current_DS2_gate_command=expected,adoption_actual_SUCCEEDED_closed=True,adoption_changed_files=[],old_six_independent_repair_cases_retained_not_replayed=True,source562_Git_index_ST2_and_DS1_conserved=True,relocation_delta_exact=True,exact_verifier_import_origin_verified=True,Root_helper_main_or_gate_or_native_or_full_F_or_controls_replay=False,full_product_acceptance=False)
s.save(R/'INDEPENDENT-ADMISSION-READBACK.json',report);print(json.dumps(report,indent=2))
