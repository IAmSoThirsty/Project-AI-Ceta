"""Checkpoint9 preparation boundaries; no mutation on import."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,stat,sys

F=Path('T:/00-Active/Project-AI-CETA');P=F/'.agents/runtime/oq23/cp9';W=P/'work';C=P/'control'
RUN='ceta-cp9-preparation-20261023';PUBLICATION_RUN='ceta-cp9-publication-20261023'
PARENT='2c8f73eb354915d0328e227121436259a9592446'
HEAD='d0ee29ce75f99fe974e10ec9baf38c5a516dd2df';BRANCH='refs/heads/candidate/societal-reasoning-v1'
ORIGIN='git@github.com:IAmSoThirsty/Project-AI-Ceta.git';REF='refs/heads/development/checkpoints'
PREFIX='handoff/development-checkpoints/20261023-0009/'
ORIGINAL_UTILITY=F/'.agents/runtime/development-checkpoint-20261020/checkpoint-0008/work/prepare_checkpoint.py'
ORIGINAL_UTILITY_SHA='758a9cdac6714b991b20ccb25bf0339b23949b678e8addbfd533429447dacf4e'
UTILITY=W/'prepare_checkpoint_successor.py'
UTILITY_SHA='05960a902986002e70e09b23796424fe9f1d0bab4a4ecc7c738dcc9a746278c7'
ARCHIVAL_POLICY_SHA='575fa929b27dfbac41540cd6b30b0aa9270b38f42153313845f7b5bfcceef6a6'
INPUT_SHA='1d93519f2f0a8f8d7fc90ad1e8694b33cd4798e9ac41a86b653e97144105e683'
PLAN_SHA='e33e56f4a1aaadad946fe2550594a67dda75e83f379b2629bda03a87487555a9'
GRAPH='806558ac40aa12529f8962b139fd60bfd00902a6ecb6752fe6e9010878f75f46'
IMMUTABLE_FIXTURES=frozenset('.local-build-cache/restoration-proof/'+x for x in ('acceptance/scenarios.json','architecture/components.json','build/gates.json','build/work_packages.json','requirements/requirements.json'))
PDF_PATHS=frozenset(('assets/reference-parts/Thirstys_Codex_Standards_Edition_Volume_01_Foundations_and_Governance.pdf.part01','assets/reference-parts/Thirstys_Codex_Standards_Edition_Volume_01_Foundations_and_Governance.pdf.part02','assets/reference-parts/codex-foundations.parts.json','tools/reassemble_codex_pdf.py','tests/publication/test_pdf_reassembly.py','handoff/PDF_REASSEMBLY.md'))
HISTORICAL_C1_FAILED_RECEIPT_SHA='a065e729ae9af3291764d5d931fa11bde344265646f38d8638ce8d1d1743514b'

class PendingFinalInput(RuntimeError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as stream:
        written=stream.write(raw)
        if written!=len(raw):raise OSError('short checkpoint JSON write')
        stream.flush();os.fsync(stream.fileno())

def engine():
    if any(name.casefold()=='pythonoptimize' for name in os.environ):raise RuntimeError('CP9_INHERITED_OPTIMIZATION_FORBIDDEN: scrub PYTHONOPTIMIZE before child commands')
    assert sha(UTILITY.read_bytes())==UTILITY_SHA,'reviewed preparation utility changed'
    spec=importlib.util.spec_from_file_location('_cp9_reviewed_preparation_utility',UTILITY)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def stable(path):return engine().stable_read(Path(path))
def local(path):
    path=Path(path);assert path.is_absolute() and path.is_relative_to(F) and '..' not in path.parts and not str(path).startswith('\\\\'),'input outside this normalized local project'
    relative(path.relative_to(F).as_posix())
    return path

def reference(item,pins):
    assert type(item) is dict and set(item)=={'path','sha256'}
    path=local(item['path']);raw,native=stable(path);assert native['sha256']==item['sha256'],'frozen reference drift'
    pins[str(path)]=native;return raw

def relative(value):
    assert type(value) is str and value and not any(c in value for c in '\\:\0\r\n\t')
    p=PurePosixPath(value);assert not p.is_absolute() and p.as_posix()==value and not any(x in ('..','.') for x in p.parts)
    assert not any(x.casefold()=='.git' or x.endswith(('.', ' ')) for x in p.parts)
    return value

def validate_exports(rows,source_names):
    assert type(rows) is list
    names={name.casefold() for name in source_names};result=[]
    kinds={'accepted_engineering','completed_candidate_source','historical_failure_evidence','accepted_review','accepted_validation_evidence'}
    for row in rows:
        assert set(row)=={'source','destination','sha256','kind','review_reference'}
        path=local(row['source']);rel=path.relative_to(F).as_posix();dest=relative(row['destination'])
        assert dest.startswith(PREFIX) and len(dest)>len(PREFIX),'extra export outside new checkpoint namespace'
        assert dest.casefold() not in names,'case-colliding export';names.add(dest.casefold())
        assert row['kind'] in kinds and re.fullmatch('[a-f0-9]{64}',row['sha256'])
        lowered=[x.casefold() for x in Path(rel).parts]
        assert not any(x in {'.git','.venv','venv','env','site-packages','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'} for x in lowered),'environment/generated/Git input'
        assert not any(x in {'state.json','claims.json'} for x in lowered),'coordinator state is not an export'
        assert not any(x=='.env' or x.startswith('.env.') for x in lowered),'environment input'
        assert not rel.startswith('.local-build-cache/'),'extra cache export is forbidden; exact five source fixtures remain in canonical manifest'
        assert path.suffix.casefold() not in {'.exe','.dll','.pyd','.pyc','.pyo','.gguf'},'native/environment/model executable export is not eligible'
        assert not (path.suffix.casefold()=='.pdf'),'original oversized PDF is excluded'
        if row['kind']=='historical_failure_evidence':
            assert path.suffix.casefold() in {'.json','.md','.txt','.log','.stdout','.stderr','.patch','.jsonl','.bin'},'rejected executable cannot be exported as failure evidence'
        result.append(row)
    return result

def validate_final_shape(value):
    assert type(value) is dict and value['schema_version']==1
    assert value['project']==str(F) and value['run_id']==RUN and value['parent']==PARENT
    assert set(value['status_pins'])=={'build/progress.json','handoff/continuity.json'}
    assert value['source_payload_count']==560 and value['current_status_key']=='current_repository_execution_20261023'
    assert value['full_product_acceptance'] is False
    assert type(value['message']) is str and value['message'].strip()
    assert len(value['closed_prerequisites'])==1 and value['closed_prerequisites'][0]['run_id']=='ceta-st23-r2'
    broader=value['current_broader'];assert type(broader) is dict
    root=local(broader['root']);control=local(broader['control'])
    # Current Root authority names this fresh source-identical successor explicitly.
    assert root==F/'.agents/runtime/oq23/br3' and control==root/'control' and broader['run_id']=='ceta-br23-r3'
    for name in ('closure','verification'):assert local(broader[name]['path']).parent==control
    histories=value['preserved_broader_attempts'];assert len(histories)==2 and {x['run_id'] for x in histories}=={'ceta-br23-r1','ceta-br23-r2'}
    for row in histories:
        assert type(row['canonical_test_bodies']) is int
        if row['run_id']=='ceta-br23-r1':
            assert row['stage']=='EXECUTION_FAILED_POSTCHECK' and row['canonical_test_bodies']==510 and row['actual_exit_status']==1 and row['success_seal_present'] is False
        else:
            assert row['stage']=='PREPARATION_REJECTED_BEFORE_CANONICAL_EXECUTION' and row['canonical_test_bodies']==0 and row['execution_intent_present'] is False
    return value

def check_canonical_status(value,status):
    assert status['completion_percentage'] is None and status['full_product_acceptance'] is False and status['full_product_complete'] is False
    failed=status['failed_broader_predecessor'];assert failed['run_id']=='ceta-br23-r1' and failed['test_cohort_passed'] is False and failed['actual_exit_status']==1
    assert status['journal_runtime']['tests_run']==33 and status['broader_regression']['run_id']==value['current_broader']['run_id']
    rejected=status['rejected_broader_preparation'];assert rejected['run_id']=='ceta-br23-r2' and type(rejected['canonical_test_bodies_executed']) is int and rejected['canonical_test_bodies_executed']==0 and rejected['execution_intent_present'] is False
    return status

def check_historical_closure(item,closure,verification):
    assert closure.get('actual_run',closure.get('run_id'))==item['run_id'] and verification['run_id']==item['run_id'] and verification['receipts_valid'] is True and verification['terminal_success'] is False
    assert not any(state=='RUNNING' for state in verification['states'].values()),'historical failed attempt still has an active stage'
    if item['run_id']=='ceta-br23-r2':
        assert closure['classification']=='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION' and closure['canonical_test_bodies_executed']==0 and type(closure['canonical_test_bodies_executed']) is int
        assert closure['execution_intent_present'] is False and closure['all_actual_claims_closed'] is True and verification['states']['review']=='FAILED'
    else:assert item['run_id']=='ceta-br23-r1' and closure['actual_exit_status']==1 and closure['execution_success'] is False

def load_final(expected_sha):
    path=C/'FINAL-CANONICAL-INPUTS-R2.json'
    if not path.is_file():raise PendingFinalInput('Root FINAL-CANONICAL-INPUTS-R2.json is absent; assembly/preparation/freeze not authorized')
    raw,pin=stable(path);assert pin['sha256']==expected_sha,'Root final input hash mismatch'
    value=validate_final_shape(json.loads(raw));pins={str(path):pin}
    manifest=json.loads(reference(value['source_manifest'],pins));assert len(manifest['payload_hashes'])==560
    assert set(x for x in manifest['payload_hashes'] if x.startswith('.local-build-cache/'))==IMMUTABLE_FIXTURES
    for item in [*value['closed_prerequisites'],value['current_broader']]:
        closure=json.loads(reference(item['closure'],pins));verification=json.loads(reference(item['verification'],pins))['response']
        assert verification['run_id']==item['run_id'] and verification['receipts_valid'] is True
        assert all(x in ('SUCCEEDED','FAILED','CANCELLED') for x in verification['states'].values()),'prerequisite claim remains live'
        assert closure.get('actual_run',closure.get('run_id'))==item['run_id']
        if item['run_id']=='ceta-st23-r2':assert closure['terminal_success'] is True and verification['terminal_success'] is True,'status application is not closed successfully'
        else:
            assert item['run_id']=='ceta-br23-r3' and closure['terminal_success'] is True and verification['terminal_success'] is True,'current broader execution is not closed successfully'
            assert all(state=='SUCCEEDED' for state in verification['states'].values()),'current broader execution contains a non-successful stage'
    for item in value['preserved_broader_attempts']:
        closure=json.loads(reference(item['closure'],pins));verification=json.loads(reference(item['verification'],pins))['response']
        check_historical_closure(item,closure,verification)
        if item['run_id']=='ceta-br23-r2':
            reference(item['review_reference'],pins);assert verification['states']['review']=='FAILED'
            root=F/'.agents/runtime/oq23/br2'
            assert not any((root/'delivery'/name).exists() for name in ('EXECUTION-INTENT.json','START.json','RESULT.json','REPORT-SEAL.json')),'BR2 preparation cannot be relabelled as a canonical execution'
            assert not (root/'control-r2/EXECUTION-PROCESS.json').exists()
    rows=validate_exports(value['exports'],manifest['payload_hashes'])
    for row in rows:
        raw,native=stable(row['source']);assert native['sha256']==row['sha256'];pins[str(local(row['source']))]=native
        reference(row['review_reference'],pins)
    canonical={}
    for rel,expected in dict(manifest['payload_hashes'],**value['status_pins']).items():
        relative(rel);raw,native=stable(F/rel);assert native['sha256']==expected,('canonical source drift',rel);canonical[rel]=native
    return value,manifest,pins,canonical

def tree(module,commit,env=None):
    out={}
    for entry in module.git(F,['ls-tree','-r','-z',commit],env=env).split(b'\0'):
        if entry:
            header,name=entry.split(b'\t',1);mode,kind,oid=header.decode().split();out[name.decode()]=[mode,kind,oid]
    return out

def conservation(parent,child,exports):
    assert set(parent)<=set(child),'parent path loss'
    assert all(parent[name][0]==child[name][0] for name in parent),'parent mode loss'
    changed={name for name in set(parent)|set(child) if parent.get(name)!=child.get(name)}
    assert changed and changed<=set(exports),'empty checkpoint or unexported change'
    assert all(parent[name]==child[name] for name in IMMUTABLE_FIXTURES|PDF_PATHS),'immutable source fixture or PDF transport changed'
    assert set(name for name in child if name.startswith('.local-build-cache/'))==IMMUTABLE_FIXTURES
    return sorted(changed)

def preparation_claim():
    assert sha((P/'packet/INPUTS.json').read_bytes())==INPUT_SHA and sha((P/'packet/PLAN.md').read_bytes())==PLAN_SHA
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_graph import compile_graph
    from taar.orchestration_runtime import OrchestrationRuntime
    graph=compile_graph(Path('T:/'),C);assert graph.fingerprint==GRAPH
    runtime=OrchestrationRuntime(C);response=runtime.verify(RUN);assert response['allowed'] and response['receipts_valid']
    state=json.loads((C/RUN/'state.json').read_bytes());claims=json.loads((C/RUN/'claims.json').read_bytes());claim=claims['implement']
    assert state['nodes']['implement']['state']=='RUNNING' and claim['executor_id']=='/root/status_packet_review' and Path(claim['workspace'])==W
    assert claim['effective_write_scope']==graph.nodes['implement']['write_scope'] and claim['input_hash']==runtime._input_hash(graph,state,'implement')
    return claim
