"""Read-only byte/control verification; never native or human-action admission."""
from pathlib import Path
import ast
import hashlib
import json
import sys

W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True


def main():
    sys.path.insert(0,str(W))
    import supervisor as s
    frozen=s.strict(s.read(W/'FROZEN.json'))
    assert frozen['kind']=='CETA_LOADER_BRIDGE_SUPERVISOR_FREEZE_V1'
    assert frozen['author']=='/root/review' and frozen['native_execution'] is False
    files=frozen['files']
    current={p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file() and p!=W/'FROZEN.json'}
    assert set(files)==current,('FREEZE_SCOPE_CHANGED',sorted(set(files)^current))
    for name,pin in files.items():assert s.digest(s.read(W/name))==pin,('FROZEN_BYTES_CHANGED',name)
    python={p.name:s.digest(s.read(p)) for p in W.glob('*.py')}
    assert python==frozen['python_hashes']
    for name in python:ast.parse(s.read(W/name),filename=str(W/name))
    inputs=s.strict(s.read(W/'INPUTS.json'))
    assert inputs['code_hashes']=={n:python[n] for n in ('supervisor.py','child_entry.py','owned_interpreter.py')}
    assert inputs['native_execution'] is False and inputs['product_acceptance'] is False
    for name in ('packet','bridge_base_freeze','bridge_review','bridge_terminal_verification',
                 'interpreter_identity_observation','volume_observation'):
        s.read_ref(inputs[name])
    for record in inputs['bridge_acceptance_records']:s.read_ref(record)
    for name in ('existing_custody_primitive','guarded_runner_reused_from'):
        record=inputs[name]
        assert s.digest(s.read(s.ref_path(record)))==record['sha256']
    base=s.read_ref(inputs['bridge_base_freeze']);review=s.read_ref(inputs['bridge_review'])
    assert review['decision']=='approved' and review['exit_status']==0 and review['executor_id']!='/root/review'
    assert review['result']['source_freeze']['sha256']==inputs['bridge_base_freeze']['sha256']
    assert review['result']['exact_python_hashes']==base['python_hashes']
    bridge_root=s.ref_path(inputs['bridge_base_freeze']).parent
    for name,pin in base['files'].items():
        assert s.digest(s.read(bridge_root/name))==pin,('ACCEPTED_BRIDGE_BYTES_CHANGED',name)
    terminal=s.read_ref(inputs['bridge_terminal_verification'])['response']
    assert terminal['receipts_valid'] is True and terminal['terminal_success'] is True
    assert set(terminal['states'])=={'discover','plan','implement','review','validate','integrate'}
    assert all(v=='SUCCEEDED' for v in terminal['states'].values())
    s.verify_base_python(inputs['base_python_pin'])
    b=s.load_exact('capture_bridge',bridge_root/'capture_bridge.py',base['python_hashes']['capture_bridge.py'])
    bridge_inputs=b.strict_json(b.read_bytes(bridge_root/'BRIDGE-INPUTS.json'))
    assert bridge_inputs['trusted_owner_ingress_reference'] is None
    try:b.trusted_anchor(bridge_inputs)
    except b.BridgeError as error:assert str(error)=='BRIDGE_TRUSTED_ROOT_INGRESS_NOT_BOUND_NO_EFFECTS'
    else:raise AssertionError('MISSING_INGRESS_DID_NOT_REFUSE')
    result=s.strict(s.read(W/frozen['final_control_receipt']))
    assert result['exit_status']==0 and not result['failures'] and not result['errors'] and not result['skips']
    assert not result['denied_calls'] and not result['remaining_threads'] and result['code_unchanged']
    assert result['before_hashes']==result['after_hashes']==python
    assert result['tests_run']==len(result['expected_ids'])==frozen['controlled_test_count']
    observation=s.read_ref(inputs['volume_observation'])
    assert observation['classification']=='environment/dependency issue' and observation['repair_performed'] is False
    print(json.dumps(dict(disposition='FROZEN_SUPERVISOR_CONSTRUCTION_VERIFIED_ONLY',files=len(files),
        controlled_tests=result['tests_run'],accepted_bridge_source_preserved=True,
        trusted_owner_ingress='ABSENT_REFUSES_BEFORE_OUTER_CHILD',
        interpreter_native_qualification='NOT_RUN',volume_observation=inputs['volume_observation'],
        native_execution=False,native_qualification=False,product_acceptance=False)))
    return 0


if __name__=='__main__':raise SystemExit(main())
