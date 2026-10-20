"""Freeze the minimal pure GUID repair and actual unchanged leaf qualification."""
from en_support import *
import ast,difflib

inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
stage=json.loads((R/'STAGED-INPUTS.json').read_text())
parent=F/'.agents/en2-20261014'
scope=inputs['eligible_paths']
proof=json.loads((R/'targeted-r2.json').read_text())
assert proof['tests_run']==109 and proof['exit_status']==0
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']
assert not proof['skips'] and not proof['threads_remaining']
rows={name:ordinary(Q/name) for name in sorted(proof['candidate_after'])}
assert rows==proof['candidate_before']==proof['candidate_after'] and len(rows)==296
source={name:ordinary(F/name) for name in inputs['Source290']}
assert source==inputs['Source290'] and len(source)==290
changed=[]
for name,facts in stage['payloads'].items():
    assert ordinary(parent/name)['sha256']==facts['sha256']
    if ordinary(Q/name)['sha256']!=facts['sha256']:changed.append(name)
assert set(changed)=={scope[0],scope[2]}
def methods(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    return {cls.name+'.'+n.name:ast.dump(n,include_attributes=False) for cls in tree.body
        if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.FunctionDef)}
oldtests='tests/contract/test_owner_enrollment.py'
leaf='tests/contract/test_source_coverage.py'
assert sha(parent/oldtests)==sha(Q/oldtests) and sha(parent/leaf)==sha(Q/leaf)
assert methods(parent/oldtests)==methods(Q/oldtests)
tree=ast.parse((Q/scope[0]).read_text())
assert not any(isinstance(node,ast.Import) and any(a.name=='uuid' for a in node.names) for node in ast.walk(tree))
old=(parent/scope[0]).read_text().splitlines();new=(Q/scope[0]).read_text().splitlines()
meaningful=lambda lines:sum(bool(line.strip()) and not line.lstrip().startswith('#') for line in lines)
added=removed=0
for tag,a,b,c,d in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes():
    if tag in ('replace','delete'):removed+=meaningful(old[a:b])
    if tag in ('replace','insert'):added+=meaningful(new[c:d])
test_lines=(Q/scope[1]).read_text().splitlines()
measures={'at':utc(),'new_source_LOC':added,'source_removed':removed,'new_test_LOC':meaningful(test_lines),
    'new_test_methods':6,'inherited_runtime_document_evidence_LOC_credit':0,
    'basis':'Physical nonblank/noncomment changed source/test lines only.'}
write_new(R/'implementation-measures.json',measures)
for name in changed:
    with (R/(name.replace('/','__')+'.diff')).open('x',encoding='utf-8') as stream:
        stream.write(''.join(difflib.unified_diff((parent/name).read_text().splitlines(True),
            (Q/name).read_text().splitlines(True),fromfile='EN2/'+name,tofile='EN3/'+name)))
self_review={'at':utc(),'author':ACTOR,'self_review_only':True,
    'exact_old_test_file_and_leaf_guard_bytes':True,'original_enrollment_methods':38,
    'reused_dependency_payloads_exact':293,'Source290_native_bytes_exact':True,
    'verified':['Canonical lowercase8-4-4-4-12 language preserved; UUID alias acceptance remains rejected.',
        '256 deterministic canonical UUIDs cover arbitrary version/variant nibbles using original uuid.UUID as test-only oracle.',
        'Zero volume remains accepted and zero boot remains rejected; all path/clock/binding limits unchanged.',
        'Original85 contract cases plus18 unchanged leaf tests plus6new cases pass; no guard widening.',
        'Native discovery, registration, source admission, policies and authority remain separate.'],
    'qualification':reference(R/'targeted-r2.json'),'before_failure':reference(R/'before-r1.json'),
    'first_pass_before_document_append':reference(R/'targeted-r1.json')}
write_new(R/'SELF-REVIEW.json',self_review)
actions={}
for name in scope:
    try:fs.lstat(F/name)
    except FileNotFoundError:pass
    else:raise AssertionError('Occupied Source CREATE '+name)
    actions[name]={'action':'CREATE','before':None,'absence_observed_by_lstat':True,'candidate':rows[name]}
manifest={'schema_version':1,'cut':RUN,'frozen_at':utc(),'author':ACTOR,
    'source_root':str(F),'candidate_root':str(Q),'runtime_root':str(R),
    'eligible_application_paths':scope,'application_actions':actions,'payload_count':296,'payloads':rows,
    'parent_manifest':inputs['parent_manifest'],'parent_review':inputs['parent_review'],
    'changed_parent_payloads':changed,'parent_payloads_exact':293,
    'new_source_LOC':added,'source_removed':removed,'new_test_LOC':measures['new_test_LOC'],
    'inherited_source_dependencies_runtime_document_evidence_LOC_credit':0,
    'qualification':reference(R/'targeted-r2.json'),'qualification_raw':reference(R/'targeted-r2.txt'),
    'prior_failure':reference(R/'before-r1.json'),'prior_failure_raw':reference(R/'before-r1.txt'),
    'self_review':reference(R/'SELF-REVIEW.json'),'implementation_measures':reference(R/'implementation-measures.json'),
    'source_inputs':reference(R/'SOURCE-INPUTS.json'),
    'tests':{'methods':109,'original_contract_cases':85,'unchanged_leaf_cases':18,'new_methods':6,
        'failures':0,'errors':0,'skips':0,'native_operations':False},
    'status':'EXECUTABLE_PURE_GUID_REPAIR_AWAITING_DISTINCT_REVIEW','Source_published':False,
    'runtime_activation':False,'genuine_native_effect_invocation':False,
    'remaining':['Distinct review and joined acceptance pending.',
        'GUID syntax never proves native object, hardware boot, owner identity or authority.'],
    'review_support':{name:ordinary(R/name) for name in ('en_support.py','run_tests.py')},
    'reviewer_guidance':'Actual distinct review claim; preserve296 payloads and exact old tests/guard. Run109 exactIDs with all ceta imports fromQ. Independently compare canonical/invalid UUID grammar. No native/profile/Source/E3 changes.'}
write_new(Q/'TRANSFER-MANIFEST.json',manifest)
write_new(R/'HANDOFF.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'tests':manifest['tests'],
    'eligible_paths':scope,'measures':measures,'Source_application':False,'distinct_review_required':True})
command={'command':subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(R/'run_tests.py'),'targeted-r2']),'exit_status':0}
complete('implement',{'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'handoff':reference(R/'HANDOFF.json'),'qualification':manifest['qualification'],
    'Source_application':False,'new_source_LOC':added,'source_removed':removed,'new_test_LOC':measures['new_test_LOC']},
    [command],[('109exactIDs pass including85original/18unchangedleaf/6new with no failures/errors/skips',True),
        ('Pure canonical GUID language and nonzero boot constraint preserved without widening leaf guard',True),
        ('Source290/293reusedpayloads/oldtests/oldguard native bytes preserved and no native operation',True)])
print(json.dumps({'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'implement':reference(R/'implement.json'),
    'tests':109,'new_source_LOC':added,'source_removed':removed,'new_test_LOC':measures['new_test_LOC']}))
