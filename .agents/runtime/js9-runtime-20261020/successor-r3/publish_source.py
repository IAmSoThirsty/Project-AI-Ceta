"""Dormant changed/new-only Source publication through the reviewed primitive.

Root must supply fresh review, successful exact candidate-full evidence and an
actual exclusive Source write claim. Every attempt and beforeimage is retained.
There is no automatic retry, rollback, cleanup or completion-status promotion.
"""
from pathlib import Path
import argparse,fnmatch,importlib.util,json,os,sys,traceback
import js9_support as j
from js9_support import s,F,Q,R
from bounded_custody import failure

PRIMITIVE=F/'.agents/runtime/rs2-20261014/apply_joined_source.py'
PRIMITIVE_SHA256='4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'

def require_source_claim(release,paths):
    binding=release['source_lease']
    _,claims=j.proof(binding['claims']);_,state=j.proof(binding['state'])
    node=binding['node_id'];claim=claims[node]
    assert claim['executor_id']=='/root' and claim['workspace']==str(F)
    assert claim['input_hash']==binding['input_hash'] and claim['claimed_at']==binding['claimed_at']
    assert state['run_id']==binding['run_id'] and state['nodes'][node]['state']=='RUNNING'
    assert state['nodes'][node]['executor_id']=='/root'
    assert state['nodes'][node]['claim']['input_hash']==claim['input_hash']
    scope=claim['effective_write_scope'];assert scope
    assert all(any(fnmatch.fnmatchcase(path,pattern) for pattern in scope) for path in paths)
    return claim

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args();release=j.require_release(args.release_path,args.release_sha256,'publish')
    j.verify(source='before');packet=j.packet();paths=packet['application_paths']
    assert paths and len(paths)==len(set(paths))
    j.require_full_result(release['candidate_full'],release['candidate_full_launch'],'candidate-full')
    claim=require_source_claim(release,paths)
    assert s.ordinary(PRIMITIVE)['sha256']==PRIMITIVE_SHA256
    spec=importlib.util.spec_from_file_location('js9_reviewed_publication_primitive',PRIMITIVE)
    primitive=importlib.util.module_from_spec(spec);sys.modules[spec.name]=primitive;spec.loader.exec_module(primitive)
    assert primitive.S==F
    _,before=j.proof(packet['Source_before']);expected=j.manifest()['expected_payload_hashes']
    output=R/'publication';output.mkdir(exist_ok=False)
    staged=[]
    for name in paths:
        assert name in expected
        original=before['targets'][name]
        assert (None if original is None else original['sha256'])!=expected[name]
        stage=output/'staged'/name
        native_backup=output/'native-backups'/(name+'.original')
        logical_backup=output/'before'/(name+'.source')
        for parent in (stage.parent,native_backup.parent,logical_backup.parent):
            s.fs.safe_components(parent,allow_missing=True);parent.mkdir(parents=True,exist_ok=True)
            s.fs.safe_components(parent)
        s.bytes_copy(Q/name,stage)
        if original is not None:s.bytes_copy(F/name,logical_backup,expected=original)
        staged.append(dict(path=name,before=original,candidate_sha256=expected[name],
            stage=str(stage),logical_backup=None if original is None else s.ordinary(logical_backup),
            native_backup=str(native_backup)))
    j.verify(source='before');require_source_claim(release,paths)
    s.write_new(output/'PREPARED.json',dict(at=s.utc(),packet=j.exact_ref(R/'PACKET.json'),
        release=j.exact_ref(args.release_path),claim=claim,staged=staged,
        primitive=dict(path=str(PRIMITIVE),sha256=PRIMITIVE_SHA256),automatic_retry=False))
    journal=dict(started_at=s.utc(),finished_at=None,executor='/root',claim_input_hash=claim['input_hash'],
        candidate_manifest=j.manifest_reference(),completed=[],current=None,
        status='PREPARED',Source_accepted=False,automatic_retry=False)
    events=(output/'EVENTS.jsonl').open('x',encoding='utf8',buffering=1)
    primary=None
    def event(kind,value):
        raw=json.dumps(dict(at=s.utc(),event=kind,**value),allow_nan=False)+'\n'
        assert events.write(raw)==len(raw),'PUBLICATION_EVENT_SHORT_WRITE'
        events.flush();os.fsync(events.fileno())
    try:
        for row in staged:
            name=row['path'];target=F/name;original=row['before']
            assert j.canonical(require_source_claim(release,paths))==j.canonical(claim)
            journal['current']=name;journal['status']='APPLYING'
            event('BEFORE',dict(path=name,before=original,candidate_sha256=expected[name]))
            if original is not None:assert s.ordinary(target)==original
            else:
                try:s.fs.lstat(target)
                except FileNotFoundError:pass
                else:raise AssertionError('CREATE_TARGET_EXISTS:'+name)
            s.fs.safe_components(target.parent,allow_missing=True)
            target.parent.mkdir(parents=True,exist_ok=True);s.fs.safe_components(target.parent)
            primitive.publish_prepared(Path(row['stage']),target,Path(row['native_backup']),
                None if original is None else original['sha256'],expected[name])
            after=s.ordinary(target);assert after['sha256']==expected[name]
            backup=None if original is None else s.ordinary(Path(row['native_backup']))
            if original is not None:assert backup['sha256']==original['sha256']
            event('AFTER',dict(path=name,destination=after,native_backup=backup))
            journal['completed'].append(dict(path=name,destination=after,native_backup=backup))
        j.verify(source='after')
        journal['current']=None;journal['status']='PUBLISHED_PENDING_DESTINATION_VERIFICATION'
    except BaseException as error:
        primary=error;journal['status']='FAILED_OR_UNCERTAIN_PRESERVED'
        journal['primary_error']=failure(error)
        data=BaseException.__dict__['__dict__'].__get__(error)
        dict.update(data,publication_attempt=output,publication_journal=journal,
            publication_beforeimages=staged,publication_automatic_retry=False)
    finally:
        try:j.close(events,primary,'publication-events-close')
        except BaseException as error:primary=error
        if primary is not None:
            journal['status']='FAILED_OR_UNCERTAIN_PRESERVED'
            journal['primary_error']=failure(primary)
        journal['finished_at']=s.utc();journal['exit_status']=0 if primary is None else 1
        try:s.write_new(output/'RESULT.json',journal)
        except BaseException as error:
            if primary is None:raise
            j.retain(primary,error,'publication-terminal-writer',journal)
    if primary is not None:raise primary
    print(json.dumps(dict(result=j.exact_ref(output/'RESULT.json'),changed_paths=len(paths))),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
