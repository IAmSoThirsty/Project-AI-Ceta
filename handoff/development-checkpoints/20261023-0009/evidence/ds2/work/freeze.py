"""Fresh DS2 exact freeze, preserving the closed rejected predecessor."""
from pathlib import Path
from datetime import datetime,timezone
import ast,json
import directory_snapshot as d,conservation,verify_prepared as verify
W=Path(__file__).resolve().parent;B=W.parent;OLD=B.parent/'ds1'
sha=lambda p:d.legacy.sha(p)
def save(name,value):
    with (W/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
verify.prior();current=conservation.observe();save('FREEZE-CONSERVATION.json',current)
c=json.loads((W/'CONTROLS-R2.json').read_bytes());q=json.loads((W/'FULL-F-QUALIFICATION.json').read_bytes())
assert c['successful'] and c['tests_run']==50 and q['qualified'] and q['canonical_Git_ST2_and_original_evidence_conserved']
assert c['module_sha256']==q['provider_sha256']==sha(W/'directory_snapshot.py')
old=json.loads((OLD/'work/CONTROLS-R2.json').read_bytes());assert len(old['selected'])==41
assert [x for x in c['selected'] if x in old['selected']]==old['selected']
def functions(path):
    tree=ast.parse(path.read_text(encoding='utf8'));out={}
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):out[node.name]=ast.dump(node,include_attributes=False)
        if isinstance(node,ast.ClassDef):
            for child in node.body:
                if isinstance(child,ast.FunctionDef):out[node.name+'.'+child.name]=ast.dump(child,include_attributes=False)
    return out
a=functions(W/'seed-before/directory_snapshot.py');b=functions(W/'directory_snapshot.py')
changed=sorted(name for name in set(a)|set(b) if a.get(name)!=b.get(name))
assert changed==['Directory.checkpoint','WinProvider.query','custody']
parsed={p.name:sha(p) for p in W.glob('*.py') if ast.parse(p.read_text(encoding='utf8'),filename=str(p))}
save('AUTHOR-SELF-REVIEW.json',dict(run_id='ceta-ds23-r2',reviewer='/root/broader_successor_author',
    review_type='AUTHOR_SELF_REVIEW_ONLY',independent_approval=False,parsed_tools=parsed,changed_provider_functions=changed,
    controls=50,retained_ordered_control_ids=old['selected'],new_control_ids=[x for x in c['selected'] if x not in old['selected']],
    full_F_qualification_sha256=sha(W/'FULL-F-QUALIFICATION.json'),canonical_inputs_conserved=562,
    prior_DS1_review_stays_FAILED=True,prior_successful_41_controls_and_physical_scan_preserved=True,
    custody='First exact primary triple/innermost compatibility fields retained; append inner-to-outer boundary frames and all exact secondary triples',
    raw_provenance='Complete query appended before path read; partial Basic/Standard success retained on original exception and Directory.raw_handles before later-class failure escapes',
    root_candidate_closure_sha256=sha(W/'complete_candidate.py'),root_helper_executed=False,
    provider_predicates_and_unmodified_file_observer_unchanged=True,canonical_Git_installed_ST2_mutation=False,
    native_workers=False,AC7_replay=False,full_product_acceptance=False))
notes="""# DS2 directory observation boundary repair

Candidate authored and physically qualified; independent review pending. The rejected DS1 work, formal review/manifest, actual rejected receipt and all successful original41 controls/full-F measurements remain unchanged.

Only custody, WinProvider.query and Directory.checkpoint change in the provider. The first exact primary exc_info and innermost compatibility custodian remain intact. directory_snapshot_custody appends an inner-to-outer frame for each directory boundary, containing its exact primary/secondary exc_info, Directory observation, handle, closed state and close function. directory_snapshot_secondary_exc_info accumulates every exact secondary tuple; successful outer cleanup never clears an inner failed close. No cleanup retry or primary replacement is introduced.

Directory.checkpoint now records a complete successful handle sample before independently reading the path. WinProvider.query retains successful Basic/Standard results if a later class fails. The original exception holds exact failure tuples and native-query failure data. Directory.raw_handles exposes JSON-safe partial rows: stage, complete=false, metadata with successful class maps, completed_classes and failed_class. Complete rows retain stage and the original metadata map. Exact exception tuples remain in memory, never serialized or replaced; Root callers may project Directory.raw_paths/raw_handles and entered/closed from each custody frame.

All41 original ordered control IDs remain, with nine added nested/partial cases, for50 passes. The one fresh full-F qualification and562-source/Git/index/ST2 conservation are pinned separately. The original read-only access-time policy and all native identity/security/name/subtree/reparse/alias/file predicates are unchanged. The original file-native/hash observer remains a pinned read-only dependency. No canonical/installed/ST2 source, coordinator or snapshot hook was changed by this candidate.

The Root-only complete_candidate.py is frozen and unexecuted. It requires exact independent work/review/helper pins, runs the declared ordinary gate, claims only DS2 delivery, emits ACCEPTED-QUALIFICATION.json, and completes ordinary receipts. Later ST2 execution composition requires separate review. Original ST2 failure causes remain unknown. This sampled-tree qualification is not atomic filesystem/ACL/alternate-stream evidence, native-worker authorization, product acceptance or an overall completion percentage.
"""
with (W/'QUALIFICATION-NOTES.md').open('x',encoding='utf8',newline='\n') as stream:stream.write(notes)
inputs=json.loads((W/'INPUT-CONSERVATION-BEFORE.json').read_bytes());external=dict(inputs['input_pins'])
external.update(json.loads((W/'PRIOR-DS1-CLOSED.json').read_bytes())['pins'])
prior=json.loads((W/'PRIOR-DS1-CONSERVATION.json').read_bytes())
for rel,pin in prior['files'].items():external[str(OLD/rel)]=pin['sha256']
files={p.relative_to(W).as_posix():d.legacy.stable(p) for p in sorted(W.rglob('*')) if p.is_file()}
save('MANIFEST.json',dict(schema_version=1,run_id='ceta-ds23-r2',graph_fingerprint='b848fefb7c69a06d4ffc32f71bac48ac316edc03755773ec0c6103365d2b4c0b',
    recorded_at=datetime.now(timezone.utc).isoformat(),files=files,external_pins=external,controls=50,
    provider_sha256=sha(W/'directory_snapshot.py'),root_candidate_closure_sha256=sha(W/'complete_candidate.py'),
    independent_approval=False,full_product_acceptance=False,
    permitted_postfreeze_outputs=['FREEZE.stdout','FREEZE.stderr','FREEZE-PROCESS.json','PREPARED.stdout','PREPARED.stderr','PREPARED-PROCESS.json',
        'AUTHOR-COMPLETION-RECEIPT.json','AUTHOR-COMPLETE.stdout','AUTHOR-COMPLETE.stderr','AUTHOR-COMPLETE-PROCESS.json']))
print(json.dumps(dict(manifest_sha256=sha(W/'MANIFEST.json'),frozen_files=len(files),controls=50,
    provider_sha256=sha(W/'directory_snapshot.py'),root_candidate_closure_sha256=sha(W/'complete_candidate.py'))))
