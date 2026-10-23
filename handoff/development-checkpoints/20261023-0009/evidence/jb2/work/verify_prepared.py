"""Read-only JB2 exact preparation gate, without executing candidate bodies."""
from pathlib import Path
import hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    m=json.loads((W/'MANIFEST.json').read_bytes());assert m['run_id']=='ceta-jb23-r2' and m['independent_approval'] is False
    for rel,pin in m['files'].items():
        p=W/rel;assert p.is_file() and not p.is_symlink() and p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],rel
    actual={p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file()}
    assert actual-set(m['files'])-set(m['permitted_postfreeze_outputs'])=={'MANIFEST.json'}
    for path,pin in m['external_pins'].items():assert sha(Path(path))==pin,path
    report=json.loads((W/'CONTROLS-FINAL.json').read_bytes());process=json.loads((W/'CONTROLS-FINAL-PROCESS.json').read_bytes())
    assert process['exit_status']==0 and report['successful']
    assert report['tests_run']==m['controls'] and report['selected']==report['started']==report['stopped']
    assert not any(report[n] for n in ('failures','errors','skips','expected_failures','unexpected_successes','forbidden_call_attempts'))
    for name,pin in report['candidate_origins'].items():
        p=(W/'candidate/src'/Path(*name.split('.')).with_suffix('.py')).resolve()
        assert pin['path']==str(p) and sha(p)==pin['sha256']
    witness=json.loads((W/'TRANSCRIPT-BUDGET-WITNESS-R2.json').read_bytes())
    assert witness['tests_run']==4 and witness['failures']==witness['errors']==witness['skips']==0
    assert witness['selected']==witness['started']==witness['stopped']
    assert witness['candidate_origins']==report['candidate_origins']
    amendment=W/'OWNER-CONSUMER-INPUT-AMENDMENT.json'
    assert sha(amendment)==m['additional_input_authority_sha256']=='6ea1f1e8384d2377ce27285c94dc7048a8b6ceb4f645eb45fe07aeadf541c920'
    assert m['candidate_inputs']==8 and len(report['candidate_origins'])==5
    print(json.dumps(dict(allowed=True,manifest_sha256=sha(W/'MANIFEST.json'),frozen_files=len(m['files']),
        controls=m['controls'],independent_four_case_witness_repaired=True,independent_approval=False,full_product_acceptance=False)))
if __name__=='__main__':main()
