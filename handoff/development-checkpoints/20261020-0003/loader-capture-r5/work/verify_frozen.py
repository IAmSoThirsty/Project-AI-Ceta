"""Read-only freeze/evidence gate. No imports from native capture modules."""
from pathlib import Path
import ast
import hashlib
import json
import sys

W=Path(__file__).resolve().parent


def main():
    manifest=json.loads((W/'FROZEN.json').read_bytes())
    for name,pin in manifest['files'].items():
        path=W/name
        assert path.resolve().is_relative_to(W) and not path.is_symlink() and not path.is_junction()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==pin,name
    for name in manifest['successful_control_receipts']:
        result=json.loads((W/name).read_bytes())
        assert result['exit_status']==0 and result['code_unchanged'] and not result['denied_calls']
        assert not result['remaining_threads'] and result['actual_native_qualification'] is False
        assert result['before_hashes']==result['after_hashes']==manifest['python_hashes']
        if result['stage']=='tests':
            assert result['tests_run']==len(result['expected_ids']) and result['tests_run']>28
            assert not result['failures'] and not result['errors'] and not result['skips'] and not result['loader_errors']
    inputs=json.loads((W/'INPUTS.json').read_bytes())
    for name,pin in inputs['predecessor']['predecessor_files'].items():
        assert hashlib.sha256((Path(inputs['predecessor']['predecessor_source'])/name).read_bytes()).hexdigest()==pin
    for name,pin in inputs['ac7_payload_hashes'].items():
        assert hashlib.sha256((Path(inputs['ac7_candidate'])/name).read_bytes()).hexdigest()==pin
    for entry in inputs['caller_contract'].values():
        assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256']
    for name in ('ntdll','pdb'):
        entry=inputs['read_only_symbol_observations'][name]
        info=Path(entry['path']).stat()
        assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(entry['device'],entry['inode'],entry['bytes'],entry['mtime_ns'])
        assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256']
    r2=Path(inputs['predecessor']['rejected_predecessor']['root'])/'work'
    assert hashlib.sha256((r2/'FROZEN.json').read_bytes()).hexdigest()==inputs['r2_freeze']['sha256']
    for name,pin in json.loads((r2/'FROZEN.json').read_bytes())['files'].items():
        assert hashlib.sha256((r2/name).read_bytes()).hexdigest()==pin
    final=json.loads((W/manifest['final_test_receipt']).read_bytes())
    assert final['tests_run']==96
    old_runs=[json.loads((r2/name).read_bytes()) for name in json.loads((r2/'FROZEN.json').read_bytes())['successful_control_receipts']]
    old=next(value for value in old_runs if value['stage']=='tests')
    assert len(old['expected_ids'])==60 and set(old['expected_ids'])<=set(final['expected_ids'])
    def methods(path):
        tree=ast.parse(path.read_bytes())
        return {cls.name+'.'+method.name:ast.dump(method,include_attributes=False)
            for cls in tree.body if isinstance(cls,ast.ClassDef) for method in cls.body
            if isinstance(method,ast.FunctionDef) and method.name.startswith('test_')}
    original=methods(W/'originals/test_loader_capture.py.before');current=methods(W/'test_loader_capture.py')
    assert len(original)==28 and all(current.get(key)==value for key,value in original.items())
    r3=Path(inputs['r3_root'])
    assert hashlib.sha256((r3/'FROZEN.json').read_bytes()).hexdigest()==inputs['r3_freeze']['sha256']
    r3meta=json.loads((r3/'FROZEN.json').read_bytes())
    for name,pin in r3meta['files'].items():assert hashlib.sha256((r3/name).read_bytes()).hexdigest()==pin
    r3test=json.loads((r3/r3meta['final_test_receipt']).read_bytes())
    assert len(r3test['expected_ids'])==83 and set(r3test['expected_ids'])<=set(final['expected_ids'])
    for name in ('test_loader_capture.py','test_loader_snaps.py','test_loader_caller.py'):
        before=methods(W/'before-r3'/(name+'.before'));after=methods(W/name)
        assert all(after.get(key)==value for key,value in before.items())
    r4=Path(inputs['successor']['predecessor'])
    assert hashlib.sha256((r4/'FROZEN.json').read_bytes()).hexdigest()==inputs['r4_freeze']['sha256']
    r4meta=json.loads((r4/'FROZEN.json').read_bytes())
    for name,pin in r4meta['files'].items():assert hashlib.sha256((r4/name).read_bytes()).hexdigest()==pin
    r4test=json.loads((r4/r4meta['final_test_receipt']).read_bytes())
    assert len(r4test['expected_ids'])==88 and set(r4test['expected_ids'])<=set(final['expected_ids'])
    for name in ('test_loader_capture.py','test_loader_snaps.py','test_loader_caller.py'):
        before=methods(W/'before-r4'/(name+'.before'));after=methods(W/name)
        assert all(after.get(key)==value for key,value in before.items())
    reviews=json.loads((W/'PREDECESSOR-REVIEWS.json').read_bytes())
    assert {row['predecessor'] for row in reviews['reviews']}=={'r3','r4'}
    for row in reviews['reviews']:
        assert row['terminal'] and row['review_state']=='FAILED'
        for key in ('report','state_reference','claims_reference','submitted_receipt'):
            entry=row[key]
            assert hashlib.sha256((Path(inputs['repository'])/entry['repository_relative_path']).read_bytes()).hexdigest()==entry['sha256']
    assert not manifest['test_preservation']['changed_original_28_methods']
    assert inputs['protected_effects_authorized'] is False
    assert not (W/'NATIVE-RELEASE.json').exists(), 'This freeze admits data-only code, not a native release'
    print(json.dumps(dict(verified=True,files=len(manifest['files']),
        predecessor_unchanged=True,ac7_payloads_unchanged=len(inputs['ac7_payload_hashes']),
        native_execution=False,review_status='PENDING_INDEPENDENT_REVIEW',tests=final['tests_run'],
        symbol_supplement='V2_PENDING_DISTINCT_REVIEW_V1_STILL_DENIED')))
    return 0


if __name__=='__main__':raise SystemExit(main())
