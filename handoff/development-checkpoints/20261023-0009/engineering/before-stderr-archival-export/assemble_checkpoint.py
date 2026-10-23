"""Assemble exact checkpoint9 inputs only after Root supplies its final closed evidence."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
from datetime import datetime,timezone
import argparse,difflib,hashlib,json,platform,subprocess,sys
import checkpoint_core as c

def blob_oid(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def evidence_locations(value,final_pin):
    """Locate only Root's explicit exports without rewriting source references."""
    entries=[]
    for row in value['exports']:
        source=c.local(row['source']).relative_to(c.F).as_posix()
        review=c.local(row['review_reference']['path']).relative_to(c.F).as_posix()
        destination=c.relative(row['destination'])
        assert destination.startswith(c.PREFIX) and len(destination)>len(c.PREFIX)
        entries.append(dict(original_repository_relative_path=source,published_destination=destination,sha256=row['sha256'],kind=row['kind'],review_reference=dict(original_repository_relative_path=review,sha256=row['review_reference']['sha256'])))
    return dict(schema_version=1,classification='EVIDENCE_LOCATOR_DATA_ONLY',purpose='Resolve explicitly exported original source references to public checkpoint locations; this mapping does not grant review or product acceptance.',final_input_sha256=final_pin,source_manifest_sha256=value['source_manifest']['sha256'],exports=entries,full_product_acceptance=False)

def delta(module,parent,manifest):
    rows=[]
    for name,pin in sorted(manifest['payload_hashes'].items()):
        raw,_=c.stable(c.F/name);oid=blob_oid(raw);old=parent.get(name)
        if old and old[2]==oid:continue
        previous=module.batch_blobs(c.F,[old[2]],{})[0] if old else b''
        row=dict(path=name,before_oid=old[2] if old else None,after_oid=oid,before_sha256=c.sha(previous),after_sha256=pin)
        try:
            a=previous.decode('utf-8').splitlines();b=raw.decode('utf-8').splitlines();ops=difflib.SequenceMatcher(a=a,b=b).get_opcodes()
            row.update(text=True,added=sum(l-k for op,i,j,k,l in ops if op in ('replace','insert')),removed=sum(j-i for op,i,j,k,l in ops if op in ('replace','delete')))
        except UnicodeDecodeError:row['text']=False
        rows.append(row)
    return dict(paths=rows,source=[x for x in rows if x['path'].startswith('src/')],tests=[x for x in rows if x['path'].startswith('tests/')],new_product_code_authored_during_checkpoint=False,archived_tools_are_not_product_LOC=True)

def assemble(final_pin):
    c.preparation_claim();value,manifest,pins,canonical=c.load_final(final_pin);module=c.engine()
    assert not (c.W/'CHECKPOINT-INPUTS-0002.json').exists() and not (c.W/'public-0002').exists(),'no assembly replay'
    state=module.checkout_state(c.F);assert state['head']==c.HEAD and state['branch']==c.BRANCH and state['remote_fetch']==state['remote_push']==c.ORIGIN
    assert Path(state['root'])==c.F
    refs={line.split(' ',1)[0]:line.split(' ',1)[1] for line in module.git(c.F,['for-each-ref','--format=%(refname) %(objectname)']).decode().splitlines()}
    assert refs[c.REF]==refs['refs/remotes/origin/development/checkpoints']==c.PARENT
    assert module.git(c.F,['ls-remote','--refs','origin',c.REF]).decode().splitlines()==[c.PARENT+'\t'+c.REF]
    module.git(c.F,['merge-base','--is-ancestor',c.HEAD,c.PARENT])
    parent=c.tree(module,c.PARENT);assert c.IMMUTABLE_FIXTURES|c.PDF_PATHS<=set(parent)
    all_names=set(manifest['payload_hashes'])|set(value['status_pins'])|{x['destination'] for x in value['exports']}
    assert all(parent[name][0]=='100644' for name in all_names if name in parent),'reviewed utility emits100644; preserving a different parent mode requires a separately reviewed repair'
    material={}
    for name in set(manifest['payload_hashes'])|set(value['status_pins']):
        raw,_=c.stable(c.F/name);material[name]=blob_oid(raw)
    for row in value['exports']:material[row['destination']]=blob_oid(c.stable(row['source'])[0])
    assert any(name not in parent or parent[name][2]!=oid for name,oid in material.items()),'NO_ELIGIBLE_CONTENT_CHANGE; no checkpoint disclosure-only commit'
    source_delta=delta(module,parent,manifest)
    before=dict(final_input_sha256=final_pin,checkout=state,canonical_pins=canonical,normal_index_native=c.stable(c.F/'.git/index')[1],HEAD_native=c.stable(c.F/'.git/HEAD')[1],refs=refs,parent_tree=parent,external_pins=pins)
    c.save(c.W/'CANONICAL-BEFORE-0002.json',before)
    c.save(c.W/'SOURCE-MANIFEST-0002.json',dict(candidate=str(c.F),payload_count=560,payload_hashes=manifest['payload_hashes'],source_manifest=value['source_manifest'],full_product_acceptance=False))
    public=c.W/'public-0002';public.mkdir()
    progress=json.loads(c.stable(c.F/'build/progress.json')[0]);status=progress[value['current_status_key']]
    c.check_canonical_status(value,status)
    c.save(public/'SOURCE-TEST-DELTA.json',source_delta)
    c.save(public/'EVIDENCE-LOCATIONS.json',evidence_locations(value,final_pin))
    c.save(public/'STATUS.json',dict(checkpoint_sequence=9,parent=c.PARENT,prepared_at=datetime.now(timezone.utc).isoformat(),publication='NOT_EXECUTED; REQUIRES_SEPARATE_REVIEW_GATE_EXACT_GIT_CLAIM',canonical_payloads=560,status_register_exports=2,current_repository_execution=status,current_source_test_delta=source_delta,preserved_registry_fixtures=sorted(c.IMMUTABLE_FIXTURES),preserved_parent_pdf_exports=sorted(c.PDF_PATHS),historical_C1_integration_state='FAILED',historical_C1_failed_receipt_sha256=c.HISTORICAL_C1_FAILED_RECEIPT_SHA,closed_prerequisites=value['closed_prerequisites'],current_broader=value['current_broader'],preserved_broader_attempts=value['preserved_broader_attempts'],full_product_acceptance=False,completion_percentage=None))
    md='Project-AI: CETA development checkpoint9\n\nCanonical integration and evidence consistency have progressed. No defensible overall completion percentage is established.\n\nThe retained status register contains the actual closed journal, timing, broader successor and status-application outcomes. BR1 remains failed despite510 completed test bodies with no test failures: required post-execution observation failed and no success seal exists. BR2 preparation was independently rejected before canonical execution: zero test bodies and no execution intent. Historical halt, failed reviews and the consumed AC7 native attempt remain preserved.\n\nReliable admission timing, genuine attributable authorization-to-native-effect, remaining application/model requirements, installed, offline, migration, endurance and human/hardware acceptance remain open.\n\nPreparation uses an isolated index and private objects. Actual publication requires its own fresh exact Git scope and ordinary pre-push hook. This disclosure is development evidence and does not establish full-product acceptance.\n'
    raw_md=md.encode()
    with (public/'STATUS.md').open('xb') as stream:
        written=stream.write(raw_md)
        if written!=len(raw_md):raise OSError('short checkpoint status Markdown write')
        stream.flush();__import__('os').fsync(stream.fileno())
    selected={}
    for rel in manifest['payload_hashes']:
        raw,pin=c.stable(c.F/rel);selected[rel]=dict(input_path=str(c.F/rel),input_pin=pin)
    extras=[dict(source=str(c.F/rel),destination=rel,sha256=pin) for rel,pin in value['status_pins'].items()]+[{k:row[k] for k in ('source','destination','sha256')} for row in value['exports']]
    engineering=('checkpoint_core.py','assemble_checkpoint.py','run_prepare.py','verify_prepared.py','verify_publication.py','freeze_preparation.py','exact_git_scope.py','publish_checkpoint.py','test_checkpoint_controls.py','run_controls.py','README.md','SELF-REVIEW.json','FINAL-INPUT-CONTRACT.json','CONTROLS-RESULT.json','CONTROLS.stdout','CONTROLS.stderr','CONTROLS-PROCESS.json','SOURCE-MANIFEST-0002.json')
    engineering+=('INTERPRETER-PACK-INDEPENDENT-FINDINGS.json','INTERPRETER-PACK-REVIEW-RESPONSE.json','INTERPRETER-PACK-SOURCE-DELTA.patch','INTERPRETER-PACK-PATCH-SETUP-FAILURE-R1.json','INTERPRETER-PACK-ENVIRONMENT-FAILURE-R8.json','INTERPRETER-PACK-IMPORT-ENVIRONMENT-DIAGNOSIS-R1.json','INTERPRETER-PACK-CLAIM-ENVIRONMENT-DIAGNOSIS-R1.json','INTERPRETER-PACK-POPEN-ENVIRONMENT-DIAGNOSIS-R1.json','INTERPRETER-PACK-POWERSHELL-NULL-ENVIRONMENT-DIAGNOSIS-R1.json','CONTROL-ENVIRONMENT-RELEASE-R9.json','SYNTAX-CHECK-INTERPRETER-PACK-R2.json','POST-INTERPRETER-PACK-CONTROLS-PRESERVATION.json','ROOT-INTERPRETER-INPUT-LINEAGE.json',*[f'controls-r{attempt}/{name}' for attempt in (7,8,9) for name in ('START.json','RESULT.json','TESTS.log')],*[f'CONTROLS-ATTEMPT{attempt}{suffix}' for attempt in (7,8,9) for suffix in ('-PROCESS.json','.stdout','.stderr')],*[f'root-interpreter-inputs/{name}' for name in ('ROOT-CLOSE-PREPARATION.py','ROOT-PUBLICATION.py','SETUP-PUBLICATION.py','ROOT-INTERPRETER-GUARD-AMENDMENT.json','test_root_interpreter_guards.py','ROOT-INTERPRETER-CONTROLS.json','ROOT-INTERPRETER-CONTROLS-PROCESS.json','ROOT-INTERPRETER-CONTROLS.stdout','ROOT-INTERPRETER-CONTROLS.stderr')])
    engineering+=('FINAL-INPUT-R2-CONSUMER-RESPONSE.json','FINAL-INPUT-R2-SOURCE-DELTA.patch','ASSEMBLY-PROCESS.json','ASSEMBLY.stdout','ASSEMBLY.stderr','ASSEMBLY-FINAL-REFERENCE-FAILURE-R1.json','ROOT-INTERPRETER-INPUT-LINEAGE-R2.json','CONTROL-ENVIRONMENT-RELEASE-R10.json','SYNTAX-CHECK-FINAL-INPUT-R2.json','POST-FINAL-INPUT-R2-CONTROLS-PRESERVATION.json',*[f'controls-r10/{name}' for name in ('START.json','RESULT.json','TESTS.log')],*[f'CONTROLS-ATTEMPT10{suffix}' for suffix in ('-PROCESS.json','.stdout','.stderr')],*[f'root-interpreter-inputs-r2/{name}' for name in ('ROOT-CLOSE-PREPARATION.py','ROOT-PUBLICATION.py','SETUP-PUBLICATION.py','ROOT-FINAL-REFERENCE-AMENDMENT.json','test_root_interpreter_guards_r2.py','ROOT-INTERPRETER-CONTROLS-R2.json','ROOT-INTERPRETER-CONTROLS-R2-PROCESS.json','ROOT-INTERPRETER-CONTROLS-R2.stdout','ROOT-INTERPRETER-CONTROLS-R2.stderr','FINAL-INPUT-REFERENCE-SUCCESSOR.json','ROOT-REFERENCE-SUCCESSOR-PROCESS.json','ROOT-REFERENCE-SUCCESSOR.stdout','ROOT-REFERENCE-SUCCESSOR.stderr','FINAL-CANONICAL-INPUTS.json','FINAL-CANONICAL-INPUTS-R2.json')])
    engineering+=('prepare_checkpoint_successor.py','ARCHIVAL-WHITESPACE-POLICY.json','ARCHIVAL-SUCCESSOR-RESPONSE.json','ARCHIVAL-SUCCESSOR-SOURCE-DELTA.json','ARCHIVAL-LITERAL-PATHSPEC-QUALIFICATION.json','PRIVATE-PREPARATION-FAILURE-DIAGNOSIS.json','PRIVATE-PREPARATION-PROCESS.json','PRIVATE-PREPARATION.stdout','PRIVATE-PREPARATION.stderr','PREPARATION-COMMANDS.jsonl','SOURCE-MANIFEST.json','CHECKPOINT-INPUTS.json','ASSEMBLY-RESULT.json','ASSEMBLY-R2-PROCESS.json','ASSEMBLY-R2.stdout','ASSEMBLY-R2.stderr','SYNTAX-CHECK-ARCHIVAL-SUCCESSOR.json','POST-ARCHIVAL-CONTROLS-PRESERVATION.json','CONTROL-ENVIRONMENT-RELEASE-R11.json',*[f'controls-r11/{name}' for name in ('START.json','RESULT.json','TESTS.log')],*[f'CONTROLS-ATTEMPT11{suffix}' for suffix in ('-PROCESS.json','.stdout','.stderr')])
    engineering+=('SYNTAX-CHECK-ARCHIVAL-SUCCESSOR-R2.json','SYNTAX-CHECK-ARCHIVAL-SUCCESSOR-REPORTER-FAILURE-R1.json','ROOT-PREPARED-R2-INPUT-LINEAGE.json',*[f'root-prepared-r2-inputs/{name}' for name in ('ROOT-CLOSE-PREPARATION.py','SETUP-PUBLICATION.py','ROOT-PUBLICATION.py','ROOT-PREPARED-R2-AMENDMENT.json','test_root_interpreter_guards_r3.py','ROOT-INTERPRETER-CONTROLS-R3.json','ROOT-INTERPRETER-CONTROLS-R3-PROCESS.json','ROOT-INTERPRETER-CONTROLS-R3.stdout','ROOT-INTERPRETER-CONTROLS-R3.stderr')])
    for name in engineering:
        path=c.W/name;extras.append(dict(source=str(path),destination=c.PREFIX+'engineering/'+name,sha256=c.stable(path)[1]['sha256']))
    extras.append(dict(source=str(c.UTILITY),destination=c.PREFIX+'engineering/prepare_checkpoint_engine.py',sha256=c.UTILITY_SHA))
    extras.extend(dict(source=str(path),destination={'STATUS.json':'DEVELOPMENT-CHECKPOINT.json','STATUS.md':'DEVELOPMENT-CHECKPOINT.md'}.get(path.name,c.PREFIX+path.name),sha256=c.stable(path)[1]['sha256']) for path in sorted(public.iterdir()))
    for row in extras:
        assert row['destination'].casefold() not in {x.casefold() for x in selected},'duplicate export'
        raw,pin=c.stable(row['source']);selected[row['destination']]=dict(input_path=row['source'],input_pin=pin)
    scan=module.scan_exports(selected);c.save(public/'RAW-SECRET-SCAN.json',scan);assert not scan['findings']
    extras.append(dict(source=str(public/'RAW-SECRET-SCAN.json'),destination=c.PREFIX+'RAW-SECRET-SCAN.json',sha256=c.stable(public/'RAW-SECRET-SCAN.json')[1]['sha256']))
    spec=dict(root=str(c.F),output=str(c.W/'prepared-0002'),expected_head=c.HEAD,expected_branch=c.BRANCH,expected_status_sha256=state['status_sha256'],origin=c.ORIGIN,ref=c.REF,parent=c.PARENT,archival_whitespace_policy_sha256=c.ARCHIVAL_POLICY_SHA,manifest=str(c.W/'SOURCE-MANIFEST-0002.json'),manifest_sha256=c.stable(c.W/'SOURCE-MANIFEST-0002.json')[1]['sha256'],extra_exports=extras,message=value['message'])
    c.save(c.W/'CHECKPOINT-INPUTS-0002.json',spec);c.save(c.W/'ASSEMBLY-RESULT-0002.json',dict(final_input_sha256=final_pin,source_payloads=560,status_exports=2,explicit_exports=len(extras),toolchain=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),Git=module.git(c.F,['--version']).decode().strip()),source_test_delta=source_delta,canonical_Git_writes=False,full_product_acceptance=False))
    assert module.checkout_state(c.F)==state and c.stable(c.F/'.git/index')[1]==before['normal_index_native']
    print(json.dumps(dict(assembled=True,exports=len(extras),canonical_payloads=560,canonical_Git_writes=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--final-sha256',required=True);assemble(p.parse_args().final_sha256)
