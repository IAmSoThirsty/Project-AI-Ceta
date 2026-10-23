"""Read-only canonical, Git and ST2 state conservation from the frozen baseline."""
from pathlib import Path
import hashlib,json,subprocess
import directory_snapshot as d
F=d.F;W=Path(__file__).resolve().parent
def observe():
    before=json.loads((W/'INPUT-CONSERVATION-BEFORE.json').read_bytes());files={}
    for name,pin in before['canonical_files'].items():
        actual=d.legacy.stable(Path(name));assert actual==pin,('canonical changed',name);files[name]=actual
    def git(*args):
        p=subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=F,capture_output=True)
        assert p.returncode==0;return p.stdout
    Git=dict(root=git('rev-parse','--show-toplevel').decode(),branch=git('symbolic-ref','HEAD').decode(),
        head=git('rev-parse','HEAD').decode(),origin=git('remote','get-url','origin').decode(),
        dirty_all_untracked_sha256=hashlib.sha256(git('status','--porcelain=v1','--untracked-files=all')).hexdigest(),
        index=d.legacy.stable(F/'.git/index'))
    assert Git==before['Git'],'Git/index changed'
    run=F/'.agents/runtime/oq23/st2/control/ceta-st23-r2'
    state={name:d.legacy.stable(run/name) for name in before['ST2_run_files']}
    assert state==before['ST2_run_files'],'ST2 coordinator changed'
    assert not any((F/'.agents/runtime/oq23/st2/delivery').iterdir()),'ST2 delivery changed'
    for path,pin in before['input_pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin,path
    return dict(canonical_files=files,canonical_count=len(files),Git=Git,ST2_run_files=state,
        ST2_delivery_entries=[],canonical_Git_ST2_and_original_evidence_conserved=True)
