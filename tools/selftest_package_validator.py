"""Test the package checker with isolated mutations; never exercise the CETA runtime."""
from pathlib import Path
import argparse
import sys, json, importlib.util, tempfile, shutil, os, time
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--report',type=Path)
args=parser.parse_args()
root=args.root.resolve(strict=True)
if args.report and args.report.resolve().is_relative_to(root):
    parser.error('Report must be outside the immutable package.')
spec=importlib.util.spec_from_file_location('v',root/'tools/validate_package.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def cheap_copy(src,dst):
    try: os.link(src,dst)
    except OSError: shutil.copy2(src,dst)
    return dst

def replace(p,data):
    p.unlink(missing_ok=True);p.write_bytes(data)

results=[]
with tempfile.TemporaryDirectory(prefix='package-qa-',) as tmp:
    copy=Path(tmp)/'package';shutil.copytree(root,copy,copy_function=cheap_copy)
    initial=v.validate(copy,skip_manifest=True,with_jsonschema=True)
    assert initial['result']=='PASS',initial['errors']
    results.append({'id':'QA-01','test':'Intact package passes structural and full example-schema checks','result':'PASS'})
    cases=[
    ('README.md',lambda b:None,'Missing entry document'),
    ('requirements/requirements.json',lambda b: mut_json(b,lambda d:d['requirements'].append(d['requirements'][0].copy())),'Duplicate requirement ID'),
    ('requirements/requirements.json',lambda b: mut_json(b,lambda d:d['requirements'][0]['acceptance_ids'].append('B999')),'Dangling acceptance reference'),
    ('build/work_packages.json',lambda b: mut_json(b,lambda d:d['packages'][0]['depends_on'].append('WP-27')),'Cyclic build dependency'),
    ('acceptance/scenarios.json',lambda b: mut_json(b,lambda d:d['scenarios'][0].update(result='PASS')),'Fabricated runtime pass'),
    ('standards/lifecycle_coverage.json',lambda b: mut_json(b,lambda d:d['sections'].pop(0)),'Missing original lifecycle section'),
    ('sources/codex/canonical_text/03_SECTIONS/001_RESEARCH.txt',lambda b:b+b'\nunauthorized change\n','Changed preserved source bytes'),
    ('config/design_defaults.json',lambda b:b'{"same":1,"same":2}','Duplicate JSON keys'),
    ('config/design_defaults.json',lambda b:b'{"value":NaN}','Nonfinite JSON number'),
    ('policies/policy_registry.json',lambda b:mut_json(b,lambda d:d['policies'][0].update(path='../../outside.txt')),'Path traversal in registry'),
    ('contracts/examples/observation_shape_valid.json',lambda b:mut_json(b,lambda d:d['instance'].pop('record_id')),'Malformed expected-valid schema example'),
    ('policies/POL-01_authority_and_consent.md',lambda b:None,'Missing prewritten policy'),
    ('src/ceta/contracts/README.md',lambda b:b+b'\n[broken](./missing-file.md)\n','Broken authored file link'),
    ]
    def mut_json(b,fn):
        d=json.loads(b);fn(d);return json.dumps(d).encode()
    for i,(path,change,label) in enumerate(cases,2):
        p=copy/path;original=p.read_bytes();changed=change(original)
        if changed is None:p.unlink()
        else:replace(p,changed)
        res=v.validate(copy,skip_manifest=True,with_jsonschema=True)
        ok=res['result']=='FAIL'
        results.append({'id':f'QA-{i:02d}','test':label,'result':'PASS' if ok else 'FAIL','expected_validator_result':'FAIL','actual_validator_result':res['result'],'detection':res['errors']})
        replace(p,original)
        assert ok,(label,res)
    final=v.validate(copy,skip_manifest=True,with_jsonschema=True)
    assert final['result']=='PASS',final['errors']
    results.append({'id':'QA-15','test':'Restored package passes again after isolated mutation tests','result':'PASS'})
report={'scope':'AUTHOR_SELF_TEST_OF_PACKAGE_VALIDATION_TOOL_ONLY','runtime_tests_executed':False,'runtime_qualification':'NOT_RUN','results':results,'result':'PASS' if all(r['result']=='PASS' for r in results) else 'FAIL'}
text=json.dumps(report,indent=2)+'\n'
if args.report:
    with args.report.open('x',encoding='utf-8') as out:out.write(text)
print(text,end='')
