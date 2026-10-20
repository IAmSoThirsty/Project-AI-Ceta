"""Finite EN3 independent acceptance and actual review completion."""
from review_support import *
import ast
setup=json.loads((D/'PREPARATION.json').read_text())
proof=json.loads((D/'direct-r1/RESULT.json').read_text())
replica_proof=json.loads((D/'qualification-r1/RESULT.json').read_text())
author=json.loads((R/'targeted-r2.json').read_text())
for result in (proof,replica_proof):
    assert result['tests_run']==111 and result['exit_status']==0
    assert not result['failures'] and not result['errors'] and not result['skips']
    assert result['expected_ids']==result['executed_ids']==result['stopped_ids']
    assert not result['forbidden_calls'] and not result['threads_remaining']
    assert result['original109_ids']==author['expected_ids'] and len(result['original109_ids'])==109
assert proof['all_ceta_imports_from_exact_Q'] and proof['leaf_guard_reads_actual_Q_contracts']
assert all(Path(path).is_relative_to(Q/'src') for path in proof['source_imports'].values())
assert {fact['cases'] for fact in proof['differential_facts']}=={580,331}
assert sum(fact['cases'] for fact in proof['differential_facts'])==911
manifest_path=Q/'TRANSFER-MANIFEST.json';manifest=json.loads(manifest_path.read_text())
assert sha(manifest_path)=='8772cd735ae0ff767108976fef15e004012718ffded50a1d888cc354fae329ec'
for name in ('parent_manifest','parent_review','qualification','qualification_raw','prior_failure','prior_failure_raw',
    'self_review','implementation_measures','source_inputs'):
    ref=manifest[name];assert sha(F/ref['repository_relative_path'])==ref['sha256'],name
seal=json.loads((R/'AUTHOR-SEAL.json').read_text())
assert sha(R/'AUTHOR-SEAL.json')=='b458a9ad9a4ae71a86530be98311d048d9fd8e32bb372cdc24797628ca9e7e42'
for ref in seal['members'].values():assert sha(F/ref['repository_relative_path'])==ref['sha256']
def inventory(root):
    rows={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for name in dirs:assert not fs.reparse(fs.lstat(Path(base)/name))
        for name in files:
            path=Path(base)/name;rows[path.relative_to(root).as_posix()]=ordinary(path)
    return rows
assert inventory(Q)==setup['whole_Q']
assert {name:ordinary(Q/name) for name in setup['payloads']}==setup['payloads']
assert {name:ordinary(F/name) for name in setup['Source290']}==setup['Source290']
assert {name:ordinary(D/'replica'/name) for name in setup['replica']}==setup['replica']
assert {name:ordinary(F/'.agents/en2-20261014'/name) for name in setup['parent_payloads']}==setup['parent_payloads']
environment=inventory(PY.parent.parent);assert environment==setup['E3']
assert len(environment)==3601 and sum(row['bytes'] for row in environment.values())==231026067
git=[fs.text_git(F,'rev-parse','--show-toplevel','--git-common-dir','HEAD'),fs.text_git(F,'status','--porcelain=v1','--untracked-files=no')]
assert git==setup['git']
old_source=(F/'.agents/en2-20261014/src/ceta/contracts/owner_enrollment.py').read_text()
new_source=(Q/'src/ceta/contracts/owner_enrollment.py').read_text()
old_tree,new_tree=ast.parse(old_source),ast.parse(new_source)
def definitions(tree):
    return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
old_defs,new_defs=definitions(old_tree),definitions(new_tree)
assert set(old_defs)==set(new_defs)
assert {name for name in old_defs if old_defs[name]!=new_defs[name]}=={'_native_path','EnrollmentRequest'}
def signatures(tree):
    return {(n.name,ast.dump(n.args,include_attributes=False)) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
assert signatures(old_tree)==signatures(new_tree)
assert not any(isinstance(n,ast.Import) and any(alias.name=='uuid' for alias in n.names) for n in ast.walk(new_tree))
old_class=next(n for n in old_tree.body if isinstance(n,ast.ClassDef) and n.name=='EnrollmentRequest')
new_class=next(n for n in new_tree.body if isinstance(n,ast.ClassDef) and n.name=='EnrollmentRequest')
assert [(n.name,ast.dump(n,include_attributes=False)) for n in old_class.body if isinstance(n,ast.FunctionDef) and n.name!='__post_init__']==[(n.name,ast.dump(n,include_attributes=False)) for n in new_class.body if isinstance(n,ast.FunctionDef) and n.name!='__post_init__']
before=json.loads((R/'before-r1.json').read_text());assert before['tests_run']==109 and before['failures']==2 and before['errors']==0
assert sha(Q/'tests/contract/test_source_coverage.py')==sha(F/'tests/contract/test_source_coverage.py')
write(D/'CONSERVATION.json',{'at':utc(),'whole_Q':setup['whole_Q'],'candidate296_exact':True,
    'Source290':setup['Source290'],'E3':environment,'E3_count':3601,'E3_bytes':231026067,
    'replica_inputs_exact':True,'parent_EN2_payloads_retained':True,'Git':git,
    'author_prior_failure':ordinary(R/'before-r1.json'),'author_seal':ordinary(R/'AUTHOR-SEAL.json'),
    'reviewer_prior_setup_failure':ordinary(D/'PREPARATION-FAILURE-r1.json'),'Source_application':False})
source_lines=new_source.splitlines()
locations={'GUID_pattern':[i+1 for i,line in enumerate(source_lines) if line.startswith('_GUID =')],
    'volume_check':[i+1 for i,line in enumerate(source_lines) if 'if _GUID.fullmatch(match[1])' in line],
    'boot_check':[i+1 for i,line in enumerate(source_lines) if 'require(_GUID.fullmatch(boot[1])' in line]}
report={'at':utc(),'reviewer':ACTOR,'author':'/root','decision':'approved','exit_status':0,
    'manifest_sha256':sha(manifest_path),'candidate_root':str(Q),'source_root':str(F),
    'scope':'EN3 pure canonical GUID parser/import repair; three unpublished CREATE paths',
    'source_locations':locations,'eligible_application_paths':manifest['eligible_application_paths'],
    'actual_author_delta':{'source_added_LOC':5,'source_removed_LOC':9,'new_test_LOC':61,
        'new_methods':6,'reused_dependency_count':293,'copied_source_LOC_credit':0,'reviewer_product_LOC_credit':0},
    'tests':{'exact_author_ids':109,'original_contract_cases':85,'unchanged_leaf_cases':18,'new_EN3_methods':6,
        'extra_independent_methods':2,'unique_independent_method_ids':111,
        'direct_Q_executions':111,'prior_byte_exact_replica_executions':111,'total_executions':222,
        'failures':0,'errors':0,'skips':0,'actual_parent_parser_comparisons':911,
        'boot_comparisons':580,'volume_comparisons':331,'version_variant_combinations':256},
    'verified_findings':[
        'The production uuid import is removed; deterministic fixed-width lowercase ASCII hexadecimal GUID parsing is added using existing re only.',
        'Only _native_path and EnrollmentRequest.__post_init__ GUID checks change; every existing function signature and all other public definitions/method bodies stay exact.',
        'Volume GUID syntax still permits nil; boot witness still requires a nonzero canonical GUID and exact clock-session binding.',
        'Actual EN2 parser and EN3 agree on331 volume mutations/aliases and580 boot forms, including all256 version/variant combinations. Acceptance and ContractError.code match.',
        'All original38 enrollment methods and all other parent test files/ASTs remain exact; the unchanged18 leaf tests now pass without a widened import allowlist.',
        'Direct111 run imports every ceta module from frozen Q/src and tests actual Q contract leaf files; temporary output alone is redirected into reviewer runtime.',
        'First byte-exact replica111 run is retained independently of direct binding. No product source or test was edited for either run.',
        'All296 payloads/297 wholeQ files, Source290, E33601/231026067 bytes, parent dependencies and dirty Git identity remain exact.'],
    'prior_failures':{'author_before':{'path':str(R/'before-r1.json'),'tests':109,'failures':2,'errors':0,
        'classification':'Literal old uuid import failed original contract-core leaf and new direct enrollment-leaf guard; every other baseline case passed.'},
        'reviewer_setup':{'path':str(D/'PREPARATION-FAILURE-r1.json'),'raw_exit_status':1,
        'classification':'Reviewer assumed old manifest mapping; actual EN2 list rows were normalized in a fresh reader. Existing private replica retained/reverified, no product or lifecycle change.'}},
    'authorship_disclosure':setup['authorship'],
    'trust_limits':['Pure DATA_ONLY syntax and binding; no native filesystem identity, genuine boot identity, enrollment authority or effect is qualified.',
        'Test-only uuid/actual EN2 module oracle remains outside the production contract leaf.',
        'Same-host reviewer; Source publication and full joined qualification belong to Root.',
        'No profile/process/Hello/CPU operation executed; forbidden process/native exports remained uncalled.'],
    'remaining':[{'classification':'requires_separate_followup_work','issue':'Root guarded joined application/full destination checks remain required.'}],
    'Source_published':False,'runtime_activation':False,
    'evidence':{'preparation_sha256':sha(D/'PREPARATION.json'),'direct_binding_sha256':sha(D/'DIRECT-BINDING.json'),
        'direct_result_sha256':sha(D/'direct-r1/RESULT.json'),'direct_raw_sha256':sha(D/'direct-r1/tests.txt'),
        'replica_result_sha256':sha(D/'qualification-r1/RESULT.json'),'conservation_sha256':sha(D/'CONSERVATION.json')}}
write(D/'REPORT.json',report)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt,load_receipt
claim=json.loads((R/RUN/'claims.json').read_text())['review'];assert claim['executor_id']==ACTOR
graph=json.loads((R/RUN/'graph.json').read_text())['graph']
assert _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
command=lambda script:{'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(D/script)]),'exit_status':0}
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,
    'started_at':claim['claimed_at'],'finished_at':utc(),'input_hash':claim['input_hash'],'changed_files':[],
    'result':{'manifest_sha256':sha(manifest_path),'report':{'repository_relative_path':(D/'REPORT.json').relative_to(F).as_posix(),'sha256':sha(D/'REPORT.json')},
        'independent109_exact_Q_imports':True,'additional_methods':2,'parser_comparisons':911,
        'Source290_candidate296_conserved':True,'Source_application':False,
        'prior_failure':{'repository_relative_path':(D/'PREPARATION-FAILURE-r1.json').relative_to(F).as_posix(),'sha256':sha(D/'PREPARATION-FAILURE-r1.json'),'exit_status':1}},
    'commands':[command('prepare_review_r2.py'),command('run_tests.py'),command('prepare_direct.py'),command('run_direct.py')],
    'validations':[{'name':name,'passed':True} for name in [
        'Original109_and2independent_methods_pass0fail_error_skip_with_exact_Qimports',
        'Nil_volume_and_nonzero_boot_exact_canonical_grammar_preserved_against_actual_parent',
        'No_contract_leaf_guard_widening_all18unchanged_guard_cases_pass',
        'Original_tests_API_signatures_and293dependencies_preserved',
        'Source290_Q296_wholeQ297_E33601_Git_and_author_evidence_conserved',
        'Prior_failed_attempts_retained_no_native_authority_or_Source_publication_claim']],
    'exit_status':0,'decision':'approved'}
kwargs={'run_id':RUN,'node_id':'review','executor_id':ACTOR,'input_hash':claim['input_hash'],
    'claimed_at':claim['claimed_at'],'node':graph['nodes']['review']}
validate_receipt(receipt,**kwargs);write(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
invoke(['node','complete',RUN,'review',str(D/'review.json')],'review-complete')
print(json.dumps({'decision':'approved','review_sha256':sha(D/'review.json'),'report_sha256':sha(D/'REPORT.json'),
    'direct_methods':111,'parser_comparisons':911}),flush=True)
