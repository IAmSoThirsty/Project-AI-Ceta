"""Read-only verification of this exact construction; never native admission."""
from pathlib import Path
import ast
import hashlib
import json
import sys

W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True


def main():
    sys.path.insert(0,str(W))
    import capture_bridge as b
    frozen=b.strict_json(b.read_bytes(W/'FROZEN.json'))
    assert frozen['kind']=='CETA_CANONICAL_BRIDGE_CONSTRUCTION_FREEZE_V1'
    assert frozen['author']=='/root/review' and frozen['native_execution'] is False
    files=frozen['files']
    current={p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file() and p!=W/'FROZEN.json'}
    assert set(files)==current,('FREEZE_SCOPE_CHANGED',sorted(set(files)^current))
    for name,pin in files.items():
        assert b.file_sha(W/name)['sha256']==pin,('FROZEN_BYTES_CHANGED',name)
    for name,pin in frozen['python_hashes'].items():
        raw=(W/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        ast.parse(raw,filename=str(W/name))
    inputs=b.strict_json(b.read_bytes(W/'BRIDGE-INPUTS.json'))
    for name in ('packet','loader_freeze','loader_code_manifest','loader_inputs','source_review',
                 'symbol_supplement','symbol_review','signature_evidence','symbol_terminal_verification'):
        b.read_reference(inputs[name])
    for ref in inputs['accepted_dependency_records']:
        b.read_reference(ref)
    symbol=b.read_reference(inputs['symbol_supplement'])
    assert symbol['schema_version']==2 and symbol['kind']=='CETA_OWNED_LOADER_SYMBOL_INPUTS_V2'
    for pin in symbol['input_pins'].values():b.verify_file(pin)
    source=b.read_reference(inputs['loader_inputs'])
    for name,pin in source['ac7_payload_hashes'].items():
        assert b.file_sha(Path(source['ac7_candidate'])/name)['sha256']==pin
    assert len(source['ac7_payload_hashes'])==357
    for row in source['caller_contract'].values():assert b.file_sha(row['path'])['sha256']==row['sha256']
    assert frozen['trusted_owner_ingress_reference']==inputs['trusted_owner_ingress_reference']
    if inputs['trusted_owner_ingress_reference'] is None:
        try:b.trusted_anchor(inputs)
        except b.BridgeError as error:assert str(error)=='BRIDGE_TRUSTED_ROOT_INGRESS_NOT_BOUND_NO_EFFECTS'
        else:raise AssertionError('MISSING_INGRESS_DID_NOT_REFUSE')
    else:
        anchor=b.trusted_anchor(inputs)
        assert anchor['kind']=='CETA_ROOT_RECORDED_ACTION_INGRESS_V1' and anchor['recorded_by']=='/root'
    result=b.strict_json(b.read_bytes(W/frozen['final_control_receipt']))
    assert result['exit_status']==0 and not result['failures'] and not result['errors'] and not result['skips']
    assert not result['denied_calls'] and not result['remaining_threads'] and result['code_unchanged']
    assert result['after_hashes']==frozen['python_hashes']
    assert result['tests_run']==len(result['expected_ids'])==frozen['controlled_test_count']
    print(json.dumps(dict(disposition='FROZEN_CONSTRUCTION_VERIFIED_ONLY',files=len(files),
        controlled_tests=result['tests_run'],canonical_payloads=357,
        trusted_owner_ingress='ABSENT_REFUSES' if inputs['trusted_owner_ingress_reference'] is None else 'EXACT_REFERENCE_BOUND_NOT_ACTION_ADMISSION',
        native_execution=False,native_qualification=False,product_acceptance=False)))
    return 0


if __name__=='__main__':raise SystemExit(main())
