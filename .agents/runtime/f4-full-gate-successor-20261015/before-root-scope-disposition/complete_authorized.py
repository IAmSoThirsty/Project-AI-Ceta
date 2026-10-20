"""Dormant strict completion adapter; needs independent review/delivery/disposition."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys

import full_gate as gate
import run_authorized as runner

RUN = 'f4-full-gate-successor-20261015'
ISSUE_SHA = '255e3f14fd3ec91886948f0022a2ab61324fa6086fe19d6e8631f96f1fbf68b5'


def require_successor_review(s):
    runtime = runner.R/RUN
    local_path = runner.R/'independent-review/review.json'
    local = s.read(local_path)
    stored = s.read(runtime/'receipts/review.json')
    state = s.read(runtime/'state.json')
    envelope = s.read(runtime/'results/review.json')
    strict = s.STRICT
    gate.require(type(local) is dict and set(local) == strict and len(stored) == 16, 'STRICT_SUCCESSOR_REVIEW')
    gate.require(gate.exact_equal(local,{key:stored[key] for key in strict}), 'SUCCESSOR_REVIEW_PERSISTENCE')
    gate.require(local['run_id'] == RUN and local['node_id'] == 'review' and local['executor_id'] != '/root/history_preservation', 'DISTINCT_SUCCESSOR_REVIEWER')
    gate.require(local['decision'] == 'approved' and type(local['exit_status']) is int and local['exit_status'] == 0 and local['changed_files'] == [], 'SUCCESSOR_REVIEW_NOT_APPROVED')
    gate.require(state['nodes']['review']['state'] == 'SUCCEEDED' and state['nodes']['review']['receipt_hash'] == stored['receipt_hash'], 'ACTUAL_SUCCESSOR_REVIEW_REQUIRED')
    gate.require(set(envelope) == {'node_id','receipt_hash','result'} and envelope['node_id'] == 'review' and envelope['receipt_hash'] == stored['receipt_hash'] and
        gate.exact_equal(envelope['result'],local['result']), 'SUCCESSOR_RESULT_ENVELOPE')
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_persistence import sha256_json
    from taar.orchestration_receipts import validate_receipt
    gate.require(stored['receipt_hash'] == sha256_json({key:value for key,value in stored.items() if key != 'receipt_hash'}), 'SUCCESSOR_RECEIPT_FINGERPRINT')
    validate_receipt(local,run_id=RUN,node_id='review',executor_id=local['executor_id'],input_hash=local['input_hash'],claimed_at=local['started_at'],
        node=s.read(runtime/'graph.json')['graph']['nodes']['review'])
    manifest_path = runner.Q/'TRANSFER-MANIFEST.json'
    gate.require(local['result']['manifest_sha256'] == s.sha(manifest_path), 'SUCCESSOR_MANIFEST_REVIEW')
    expected = {name:s.sha(runner.Q/name) for name in ('full_gate.py','run_authorized.py','complete_authorized.py')}
    gate.require(local['result']['reviewed_successor_scripts'] == expected, 'EXACT_SUCCESSOR_SCRIPTS_REVIEWED')
    return s.reference(local_path)


def metadata_disposition(raw, expected, *, manifest_sha):
    gate.require(gate.digest(raw) == expected, 'METADATA_DISPOSITION_PIN')
    value = gate.decode_record(raw)
    gate.require(set(value) == {'schema_version','issue_sha256','F4_manifest_sha256','source','human_reply','decision',
        'whole_fixture_preservation_accepted','metadata_issue_waived'}, 'METADATA_DISPOSITION_KEYS')
    gate.require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['issue_sha256'] == ISSUE_SHA and
        value['F4_manifest_sha256'] == manifest_sha, 'EXACT_METADATA_ISSUE_REQUIRED')
    gate.require(value['source'] == 'actual_current_human_reply' and type(value['human_reply']) is str and 0 < len(value['human_reply'].strip()) <= 4096,
        'ACTUAL_METADATA_DECISION_REQUIRED')
    gate.require(value['decision'] == 'allow_library_source_completion_with_unresolved_fixture_metadata' and
        value['whole_fixture_preservation_accepted'] is False and value['metadata_issue_waived'] is False, 'NO_IMPLICIT_METADATA_WAIVER')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-nonce',required=True)
    parser.add_argument('--delivery-path',type=Path,required=True)
    parser.add_argument('--delivery-sha256',required=True)
    parser.add_argument('--metadata-disposition-path',type=Path,required=True)
    parser.add_argument('--metadata-disposition-sha256',required=True)
    args = parser.parse_args(argv)
    gate.require(type(args.run_nonce) is str and gate.re.fullmatch('[0-9a-f]{32}',args.run_nonce) is not None, 'RUN_NONCE')
    s = runner.support()
    review = require_successor_review(s)
    output = runner.R/'runs'/args.run_nonce
    full_path = output/'RESULT.json'
    full = s.read(full_path)
    required = s.read(runner.PARENT/'REQUIRED-SOURCE-TESTS.json')['required_ids']
    provenance = full['operator_gate_provenance']
    gate.require(provenance['run_nonce'] == args.run_nonce and provenance['subject']['mode'] == 'destination' and
        provenance['subject']['source_root'] == str(runner.F), 'ACTUAL_DESTINATION_RUN_REQUIRED')
    gate.require(provenance['runner_sha256'] == s.sha(runner.Q/'run_authorized.py') and provenance['gate_sha256'] == s.sha(runner.Q/'full_gate.py') and
        provenance['parent_runner_sha256'] == gate.PARENT_RUNNER, 'CURRENT_RUNNER_PIN_REQUIRED')
    gate.require(provenance['subject'] == runner.context(s,'destination',args.run_nonce), 'CURRENT_COMPLETE_SOURCE_ENVIRONMENT')
    gate.require(provenance['amended_runner_sha256'] == gate.digest(gate.amend_runner(s.fs.read_bytes(runner.PARENT/'run_joined.py')).encode()), 'AMENDED_RUNNER_PIN')
    gate.require(len(provenance['actual_argv']) >= 12 and provenance['actual_argv'][:5] == [str(runner.PY),'-B','-X','utf8',str(runner.Q/'run_authorized.py')], 'ACTUAL_SUCCESSOR_COMMAND_REQUIRED')
    expected_tail = ['--mode','destination','--run-nonce',args.run_nonce,'--approval-path',provenance['approval_path'],
        '--approval-sha256',provenance['authorization_sha256']]
    # Runner argument order is deliberately canonical for actual completion.
    gate.require(provenance['actual_argv'][5:] == expected_tail, 'CANONICAL_ACTUAL_SUCCESSOR_ARGV')
    gate.require(type(full['raw']) is dict and s.sha(s.safe_proof(full['raw'])) == full['raw']['sha256'], 'FULL_RAW_OUTPUT_PIN')
    gate.require(full['root'] == str(runner.F) and full['mode'] == 'destination', 'ACTUAL_SOURCE_ROOT')
    gate.require(full['native_execution_authorization']['sha256'] == provenance['authorization_sha256'], 'APPROVAL_PROOF_BINDING')
    gate.require(s.read(runner.R/'consumed-authorizations'/(provenance['authorization_sha256']+'.json'))['subject'] == provenance['subject'] and
        s.read(runner.R/'consumed-nonces'/(args.run_nonce+'.json'))['authorization_sha256'] == provenance['authorization_sha256'], 'CONSUMED_ATTEMPT_PROOF')
    gate.require_full_result(full,required,provenance)
    with ExitStack() as stack:
        delivery_capture = runner.capture_approval(s,stack,args.delivery_path,args.delivery_sha256,limit=16*1024*1024)
        delivery = gate.decode_document(delivery_capture.raw,16*1024*1024)
        gate.require(Path(args.delivery_path).is_relative_to(runner.R/'independent-review') and delivery['decision'] == 'approved' and
            delivery['executor_id'] not in {'/root/pressure_writer','/root','/root/history_preservation'}, 'DISTINCT_DELIVERED_REVIEW_REQUIRED')
        disposition_capture = runner.capture_approval(s,stack,args.metadata_disposition_path,args.metadata_disposition_sha256)
        disposition = metadata_disposition(disposition_capture.raw,args.metadata_disposition_sha256,manifest_sha=gate.PARENT_MANIFEST)
        bindings = {'successor_review':review,'actual_argv':provenance['actual_argv'],'full_result':s.reference(full_path),
            'approval_sha256':provenance['authorization_sha256'],'metadata_disposition':s.reference(args.metadata_disposition_path),
            'metadata_decision':disposition,'whole_fixture_preservation_accepted':False,'metadata_issue_waived':False}
        code = gate.amend_completion(s.fs.read_bytes(runner.PARENT/'complete_source.py'))
        namespace = {'__name__':'__main__','__file__':str(runner.PARENT/'complete_source.py'),
            '__successor_delivery_verified':True,
            '__require_successor_result':lambda value:gate.require_full_result(value,required,provenance),
            '__successor_full_path':full_path,'__successor_delivery_path':args.delivery_path,
            '__successor_actual_command':subprocess.list2cmdline(provenance['actual_argv']),
            '__completion_runtime':runner.R,'__successor_gate_bindings':bindings}
        # Replace only the output writer imported by the original module; all
        # old source/native/review/ledger checks and actual integrate remain.
        code = code.replace('from foundation_support import *',
            'from foundation_support import *\nwrite_new=__successor_output_writer',1)
        namespace['__successor_output_writer'] = lambda p,v:runner.write_new(s,p,v)
        exec(compile(code,str(runner.PARENT/'complete_source.py')+'#authorized-successor','exec'),namespace)
    return 0


if __name__ == '__main__':
    sys.exit(main())
