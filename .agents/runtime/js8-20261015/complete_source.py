"""Dormant guarded integration completion after full delivered independent proof."""
from pathlib import Path
import argparse,json,sys
import js8_support as j
from js8_support import s,F,Q,R,RUN

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    release=j.require_release(args.release_path,args.release_sha256,'complete');m=j.manifest();j.verify(source='after')
    claim=j.require_current_claim()
    assert release['claim_input_hash']==claim['input_hash'] and release['claim_started_at']==claim['claimed_at']
    full_path,full=j.proof(release['destination_full']);launch_path,launch=j.proof(release['destination_full_launch'])
    assert full_path==R/'destination-full/RESULT.json' and launch_path==R/'destination-full-LAUNCH-RESULT.json'
    j.require_full(full,launch,'destination-full',release['destination_full'])
    application_path,application=j.proof(release['application'])
    assert application_path==R/'active-application/APPLIED.json'
    assert application['paths']==m['application_paths'] and application['Source_accepted'] is False
    v=j.inputs();assert set(application['source352'])==set(m['expected_payload_hashes'])
    for name,row in application['source352'].items():
        assert row['sha256']==m['expected_payload_hashes'][name] and s.ordinary(F/name)==row
    expected_backups={name for name in m['application_paths'] if name in v['Source295']}
    assert set(application['native_backups'])==expected_backups and len(expected_backups)==4
    for name in expected_backups:
        original=v['Source295'][name];native=s.ordinary(R/'active-application/native-backups'/name)
        assert native==application['native_backups'][name]
        assert native['sha256']==original['sha256'] and native['native_identity']==original['native_identity']
        assert s.ordinary(R/'active-application/before'/name)['sha256']==original['sha256']
    path,delivered=j.proof(release['delivered_review'])
    assert path.is_relative_to(R/'independent-destination')
    assert delivered['decision']=='approved' and type(delivered['exit_status']) is int and delivered['exit_status']==0
    j.distinct_reviewer(delivered['reviewer'])
    assert delivered['manifest_sha256']==s.sha(Q/'TRANSFER-MANIFEST.json')
    assert delivered['source_root']==str(F) and delivered['expected_payload_hashes']==m['expected_payload_hashes']
    assert delivered['application']==release['application'] and delivered['destination_full']==release['destination_full']
    assert delivered['destination_full_launch']==release['destination_full_launch']
    proof_path,independent=j.proof(delivered['independent_source_proof'])
    raw_path,_=j.proof_bytes(delivered['independent_raw_proof'])
    assert proof_path.is_relative_to(R/'independent-destination') and raw_path.is_relative_to(R/'independent-destination')
    assert independent['expected_payload_hashes']==independent['before_hashes']==independent['after_hashes']==m['expected_payload_hashes']
    assert type(independent['exit_status']) is int and independent['exit_status']==0
    assert independent['executed_ids']==independent['stopped_ids']==independent['expected_ids']==m['required_independent_ids']
    assert type(independent['tests_run']) is int and independent['tests_run']==len(m['required_independent_ids'])
    assert all(type(independent[key]) is int and independent[key]==0 for key in ('failures','errors','skips'))
    assert type(independent['remaining_threads']) is list and independent['remaining_threads']==[]
    assert type(independent['remaining_resources']) is list and independent['remaining_resources']==[]
    assert independent['owned_resources_closed'] is True
    helper_path,helper=j.proof(release['completion_helper_review'])
    assert helper_path.is_relative_to(R/'independent-destination') and helper['decision']=='approved'
    assert type(helper['exit_status']) is int and helper['exit_status']==0
    assert helper['completion_script_sha256']==s.sha(Path(__file__)) and helper['manifest_sha256']==s.sha(Q/'TRANSFER-MANIFEST.json')
    j.distinct_reviewer(helper['reviewer'])
    assert type(independent['commands']) is list and independent['commands']
    assert all(type(row) is dict and type(row['command']) is str and row['command'] and
        type(row['exit_status']) is int and row['exit_status']==0 for row in independent['commands'])
    s.ACTOR='/root';s.INTEGRATOR='/root'
    # Existing installed snapshot/diff/validator path; no self-issued status.
    s.complete('integrate',{'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'application':release['application'],
        'destination_full':release['destination_full'],'destination_full_launch':release['destination_full_launch'],
        'delivered_review':release['delivered_review'],'completion_helper_review':release['completion_helper_review'],
        'Source_payloads':352,'tests_run':m['expected_test_count'],'Source_accepted':True},
        [{'command':s.subprocess.list2cmdline(launch['argv']),'exit_status':0},*independent['commands']],
        [('exact295_Source/native_originals_E3_full_and_delivered_proofs',True)])
if __name__=='__main__':main()
