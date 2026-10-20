"""Read genuine released180 results and physical custody before any decision."""
from pathlib import Path
import argparse
import json
from review_support import F,R,Q,V,ACTOR,PIN,j,s,preparation,require_delivery_release,helper_pins,verify_method_asts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    release=require_delivery_release(args.release_path,args.release_sha256);p=preparation();m=j.manifest()
    output=V/'delivered-r1';result_path=output/'RESULT.json';raw_path=output/'RAW.txt'
    proof=j.current_json(result_path);launch=j.current_json(V/'LAUNCH-RESULT.json')
    custody=j.current_json(output/'CUSTODY.json');native=j.current_json(output/'NATIVE-OWNERS.json')
    native7=j.current_json(output/'NATIVE-SEVEN-CUSTODY.json');receipts=j.current_json(output/'NATIVE-ADMISSION-RECEIPTS.json')
    assert type(launch['exit_status']) is int and launch['exit_status']==0 and launch['primary_error'] is None
    assert launch['release']==j.exact_ref(args.release_path) and launch['application']==release['application']
    record=launch['record'];assert type(record['child_exit']) is int and record['child_exit']==0
    assert record['primary_error'] is None and record['retirement_error'] is None
    assert record['automatic_cleanup_retry'] is False and record['child_result']==j.exact_ref(result_path)
    assert set(record['native_owner_after'])=={'closed','process_closed','thread_closed','job_closed','startup_handles_closed'}
    assert all(value is True for value in record['native_owner_after'].values())
    assert proof['reviewer']==ACTOR and proof['manifest_sha256']==PIN
    assert proof['application']==release['application'] and proof['destination_full']==release['destination_full']
    assert proof['destination_full_launch']==release['destination_full_launch']
    assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']==p['required_ids']==m['required_independent_ids']
    assert type(proof['tests_run']) is int and proof['tests_run']==180
    assert all(type(proof[key]) is int and proof[key]==0 for key in ('failures','errors','skips','exit_status'))
    assert proof['remaining_threads']==proof['remaining_resources']==[] and proof['owned_resources_closed'] is True
    assert proof['before_hashes']==proof['after_hashes']==proof['expected_payload_hashes']==m['expected_payload_hashes']
    for key,name in (('raw','RAW.txt'),('custody','CUSTODY.json'),('native_owners_proof','NATIVE-OWNERS.json'),
        ('native_cpu_custody','NATIVE-SEVEN-CUSTODY.json'),('native_admission_receipts','NATIVE-ADMISSION-RECEIPTS.json'),('lifetimes','LIFETIMES.jsonl')):
        assert proof[key]==j.exact_ref(output/name)
    assert proof['Source_publication'] is False and proof['Source_accepted'] is False and proof['full_suite'] is False
    assert proof['no_profile_or_Hello'] is True and proof['forbidden_calls']==[]
    assert type(proof['commands']) is list and proof['commands']
    assert all(type(row) is dict and type(row['command']) is str and row['command'] and
        type(row['exit_status']) is int and row['exit_status']==0 for row in proof['commands'])
    assert custody['remaining_resources']==[] and custody['owned_resources_closed'] is True
    assert all(row['physical_closed_probe'] is True for row in custody['sqlite'])
    assert all(row['closed'] is True and row['fileno_denied'] is True for row in custody['streams'])
    assert all(row['closed'] is True for row in custody['os_descriptors'])
    selected_native=[name for name in p['required_ids'] if name.startswith('test_shutdown_lifecycle.NativeShutdownTests.')]
    shutdown=custody['native_owners'];assert len(selected_native)==2 and len(shutdown)==4
    for identifier in selected_native:
        rows=[row for row in shutdown if row['test_id']==identifier]
        assert len(rows)==2 and {row['slot'] for row in rows}=={'_client','_service'}
        for row in rows:
            assert row['retired'] is True and all(value is True for value in row['closed_native_designations'].values())
            assert type(row['pid']) is int and row['pid']>0 and type(row['creation_time']) is int and row['creation_time']>0
    junctions=[row for row in custody['launcher_native_file_observations'] if row['kind']=='owned-native-junction']
    assert len(junctions)==3 and custody['junction_creation_handles_closed'] is True
    assert all(row['creation_handle_closed'] is True and row['post_close_GetHandleInformation_error']==6 for row in junctions)
    assert native['owned_resources_closed'] is True and native['journal_logical_flags_are_observations_only'] is True
    assert native['obligations'] and all(value is True for value in native['obligations'].values())
    assert native7['owned_resources_closed'] is True
    assert len(native7['owners'])==len(native7['journals'])==len(native7['clocks'])==len(native7['registrations'])==8
    assert native7['remaining_handles']==native7['remaining_registrations']==[] and native7['exact_observation_errors_retained']==0
    assert all(row['exact_native_retirement'] is True and row['logical_closed'] is True and not row['residual_startup_handles'] for row in native7['owners'])
    assert all(row['exact_connection_closed_getter'] is True for row in native7['journals'])
    assert all(row['native_registration_and_unregister_observed'] is True and row['state']=='CLOSED' and
        row['registration_current'] is None and row['sampler_alive'] is False and row['callbacks_active']==0 for row in native7['clocks'])
    assert all(row['closed_at'] is not None for row in native7['handles'])
    assert all(row['unregistered_at'] is not None for row in native7['registrations'])
    assert all(row['alive'] is False and row['joins'] and row['joins'][-1]['alive_after'] is False for row in native7['threads'])
    assert len(receipts)==8
    assert {row['test_id'] for row in native7['owners']}==set(p['native_cpu_ids'])
    fixture=Path(p['fixture_root']);assert proof['fixture_root']==str(fixture)
    assert all(Path(path).is_relative_to(fixture) for path in proof['fixture_paths'])
    fixture_now=s.fs.file_identity(s.fs.lstat(fixture))
    assert all(fixture_now[key]==proof['fixture_identity'][key] for key in ('device','inode'))
    for filename in ('PREFLIGHT.json','IMPORTS-AFTER.json'):
        imports=j.current_json(output/filename)
        assert all(Path(row['path']).is_relative_to(F/'src') for row in imports['ceta_imports'].values())
        assert all(Path(row['path']).is_relative_to(F/'tests/contract') for row in imports['test_imports'].values())
        for row in (*imports['ceta_imports'].values(),*imports['test_imports'].values()):
            assert row['sha256']==m['expected_payload_hashes'][Path(row['path']).relative_to(F).as_posix()]
    verify_method_asts(p['required_ids'],p['test_method_AST_hashes']);j.verify(source='after')
    helper_path,helper=j.proof(release['completion_helper_review'])
    assert helper['reviewer']==ACTOR and helper['decision']=='approved' and type(helper['exit_status']) is int and helper['exit_status']==0
    assert helper['completion_script_sha256']==s.sha(R/'complete_source.py') and helper['manifest_sha256']==PIN
    value=dict(schema_version=1,at=s.utc(),decision='approved',exit_status=0,reviewer=ACTOR,
        manifest_sha256=PIN,source_root=str(F),expected_payload_hashes=m['expected_payload_hashes'],
        application=release['application'],destination_full=release['destination_full'],destination_full_launch=release['destination_full_launch'],
        candidate_readiness=release['candidate_readiness'],candidate_full_status='FAILED_PRESERVED',
        independent_source_proof=j.exact_ref(result_path),independent_raw_proof=j.exact_ref(raw_path),
        independent_launch_proof=j.exact_ref(V/'LAUNCH-RESULT.json'),custody=j.exact_ref(output/'CUSTODY.json'),
        native_cpu_custody=j.exact_ref(output/'NATIVE-SEVEN-CUSTODY.json'),native_owners_proof=j.exact_ref(output/'NATIVE-OWNERS.json'),
        release=j.exact_ref(args.release_path),completion_helper_review=j.exact_ref(helper_path),reviewed_helpers=helper_pins(),
        tests_run=180,failures=0,errors=0,skips=0,actual_native_outer=record['native_owner'],actual_native_outer_after=record['native_owner_after'],
        actual_native_shutdown_owners=shutdown,actual_native_cpu_owners=native7['owners'],
        physical_resource_counts=dict(sqlite=len(custody['sqlite']),streams=len(custody['streams']),descriptors=len(custody['os_descriptors']),
            shutdown_processes=len(shutdown),CPU_processes=len(native7['owners']),CPU_clocks=len(native7['clocks']),
            CPU_registrations=len(native7['registrations']),junction_creation_handles=len(junctions)),
        remaining_threads=[],remaining_resources=[],owned_resources_closed=True,fixture_root=str(fixture),
        unchanged_original_method_ASTs=True,all_imports_live_Source=True,Source_publication=False,Source_accepted=False,
        limits=[
            'Exact180 delivered Source review only; full2334 and installed integrate completion/baseline remain separate Root gates.',
            'Positive owner authority, capacity and settlement in the original native7 are controlled fixtures; real ordinary process/clock/job CPU effects are measured separately.',
            'Two native shutdown services/four client-service owners have exact returned-owner channel closure observations. No historical PID adoption or generic removed/replaced-service completeness claim.',
            'Parent-returned SQLite/stream/descriptors and three junction creation handles are measured; child-internal handles are bounded by retained native process exit/empty job, not individually instrumented.',
            'Native7 captures exact eight process/job lifetimes, eight SQLite/clock lifetimes and eight suspend registrations with native call pairings; observer overhead is not removed from original timing bounds.',
            'No profile creation/deletion, restricted launch, genuine Hello or active application profile is authorized by this result.',
            'Prior failed full/fixture/custody evidence remains unchanged; this decision qualifies only the received released cut.'
        ],reader_script=j.exact_ref(Path(__file__)))
    s.write_new(V/'DELIVERED-REVIEW.json',value)
    paths=[V/'DELIVERED-REVIEW.json',V/'LAUNCH-ATTEMPT.json',V/'LAUNCH-OWNER.json',V/'LAUNCH-RESULT.json',
        result_path,raw_path,output/'PREFLIGHT.json',output/'IMPORTS-AFTER.json',output/'CUSTODY.json',output/'NATIVE-OWNERS.json',
        output/'NATIVE-SEVEN-CUSTODY.json',output/'NATIVE-ADMISSION-RECEIPTS.json',output/'LIFETIMES.jsonl',output/'ATTEMPT.json',
        args.release_path,helper_path,Path(__file__)]
    members={path.relative_to(F).as_posix():s.ordinary(path) for path in paths}
    s.write_new(V/'ACTUAL-DELIVERY-REVIEW-SEAL.json',dict(at=s.utc(),reviewer=ACTOR,members=members,
        decision='approved',tests_run=180,Source_publication=False,Source_accepted=False))
    assert all(s.ordinary(F/name)==row for name,row in members.items())
    print(json.dumps(dict(decision='approved',tests_run=180,review=j.exact_ref(V/'DELIVERED-REVIEW.json'),
        seal=j.exact_ref(V/'ACTUAL-DELIVERY-REVIEW-SEAL.json'),physical_resources=value['physical_resource_counts'])))


if __name__=='__main__':main()
