from pathlib import Path
from datetime import datetime,timezone
import json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';C=S/'control';R=C/'independent-handle-composition-r1'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(W))
import status_core as s,run_status as r
pin='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32';mp='8fcea3348cb3d539384eaebdf061505a0b33e4f41048ceb9b745b736f419dbf4';ap='590689f9e333e0989a46cb2684e914483a22a240ec6249c15e33aac778ee89b8'
assert s.sha(R/'MANIFEST.json')==mp and s.sha(C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json')==ap
m=json.loads((R/'MANIFEST.json').read_bytes());a=json.loads((C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json').read_bytes())
assert m['decision']==a['decision']=='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION'
assert a['prepared_manifest_sha256']==pin and a['reviewer']=='/root/status_packet_review'
for key,name in [('amendment_sha256','HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'),('runner_sha256','run_handle_qualified.py'),('launcher_sha256','execute_handle_qualified_once.py')]:assert s.sha(C/name)==m[key]==a[key],('composition drift',name)
assert s.sha(R/'REVIEW.json')==m['review_sha256']==a['review_reference']['sha256']=='c3175f175087593b2ada3e6912ed877f2963bd3f36e00376dfd111d3539abe6f'
full=s.snapshot(R,F,ignored=frozenset());current={Path(n).relative_to(R.relative_to(F)).as_posix():v for n,v in full['files'].items()}
assert full['excluded_symlinks']=={} and set(current)==set(m['files'])|{'MANIFEST.json'}
for n,h in m['files'].items():assert current[n]['sha256']==h and current[n]==m['file_native'][n],('review physical leaf drift',n)
assert set(full['directories'])==set(m['directory_identity'])
for n,v in m['directory_identity'].items():assert all(full['directories'][n][k]==x for k,x in v.items()),('review directory identity drift',n)
for n,h in m['external_pins'].items():assert s.sha(Path(n))==h,('external support drift',n)
b,q=r.load_prepared(pin);assert q.source_observation(b)==b['source_before']
for n,v in m['authorized_mutation_inputs'].items():
 path=Path(n);rel=path.relative_to(F);assert s.sha(path)==v['before_sha256'] and s.sha(W/'candidate'/rel)==v['candidate_sha256']
 assert not path.with_name(path.name+'.oq23-st-r2.tmp').exists()
state=json.loads((C/s.RUN/'state.json').read_bytes());claims=json.loads((C/s.RUN/'claims.json').read_bytes())
assert state['graph_fingerprint']==b['graph_fingerprint'] and claims=={}
assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['validate']['state']=='SUCCEEDED'
assert state['nodes']['integrate']['state']=='READY' and state['nodes']['evidence']['state']=='READY'
assert not (C/'EXECUTION-INTENT.json').exists() and not any((S/'delivery').iterdir())
result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),recorded_by='/root',decision='PASS_EXACT_HANDLE_COMPOSITION',prepared_manifest_sha256=pin,approval_sha256=ap,composition_manifest_sha256=mp,physical_review_leaves=len(m['files']),physical_review_files_including_manifest=len(current),external_pins_reread=len(m['external_pins']),all_native_file_and_directory_identities_match=True,canonical_source562_and_Git_index_unchanged=True,canonical_writes=False,live_coordinator_API_called=False,claims=claims,states={n:v['state'] for n,v in state['nodes'].items()},full_product_acceptance=False)
s.save(C/'ROOT-HANDLE-COMPOSITION-PREFLIGHT.json',result);print(json.dumps(result))
