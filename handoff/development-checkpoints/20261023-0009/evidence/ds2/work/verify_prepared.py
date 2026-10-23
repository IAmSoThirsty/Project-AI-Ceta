"""Exact read-only DS2 gate without replaying the full physical snapshot."""
from pathlib import Path
import json,sys
import directory_snapshot as d,conservation
W=Path(__file__).resolve().parent;OLD=W.parent.parent/'ds1'
def sha(p):return d.legacy.sha(p)
def prior():
    p=json.loads((W/'PRIOR-DS1-CONSERVATION.json').read_bytes())
    for rel,pin in p['files'].items():
        path=OLD/rel;assert sha(path)==pin['sha256'] and path.stat().st_size==pin['bytes'] and path.stat().st_mtime_ns==pin['mtime_ns'],rel
    closed=json.loads((W/'PRIOR-DS1-CLOSED.json').read_bytes())
    for path,pin in closed['pins'].items():assert sha(Path(path))==pin,path
def main():
    assert sys.flags.optimize==0
    m=json.loads((W/'MANIFEST.json').read_bytes());assert m['run_id']=='ceta-ds23-r2' and not m['independent_approval']
    for rel,pin in m['files'].items():
        path=W/rel;assert path.resolve().is_relative_to(W.resolve()) and d.legacy.stable(path)==pin,rel
    actual={p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file()}
    assert actual-set(m['files'])-set(m['permitted_postfreeze_outputs'])=={'MANIFEST.json'}
    for path,pin in m['external_pins'].items():assert sha(Path(path))==pin,path
    c=json.loads((W/'CONTROLS-R2.json').read_bytes());q=json.loads((W/'FULL-F-QUALIFICATION.json').read_bytes())
    assert c['successful'] and c['tests_run']==m['controls']==50 and c['selected']==c['started']==c['stopped']
    assert not any(c[key] for key in ('failures','errors','skips'))
    old=json.loads((OLD/'work/CONTROLS-R2.json').read_bytes())
    assert [name for name in c['selected'] if name in old['selected']]==old['selected'] and len(old['selected'])==41
    assert c['module_sha256']==q['provider_sha256']==sha(W/'directory_snapshot.py')
    assert q['qualified'] and q['canonical_Git_ST2_and_original_evidence_conserved'] and q['canonical_count']==562
    assert q['snapshot_sha256']==sha(W/'FULL-F-SNAPSHOT.json') and q['access_policy_sha256']==d.POLICY_SHA
    for label in ('PRIOR-BIND','CONTROLS-R2','FULL-F-QUALIFICATION-R2'):
        assert json.loads((W/(label+'-PROCESS.json')).read_bytes())['exit_status']==0
    prior();conservation.observe()
    print(json.dumps(dict(allowed=True,manifest_sha256=sha(W/'MANIFEST.json'),files=len(m['files']),controls=50,
        retained_ordered_controls=41,full_F_files=q['files'],full_F_directories=q['directories'],
        canonical_inputs_conserved=562,rejected_DS1_preserved=True,no_snapshot_replay=True,independent_approval=False)))
if __name__=='__main__':main()
