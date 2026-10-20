"""Record Root's source publication preflight without accepting the failed full run."""
from pathlib import Path
import argparse
import json
import sys
import amendment_support as j
from candidate_readiness import check_prior_failed_candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-path', type=Path, required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args()
    j.require_release(args.release_path, args.release_sha256, 'publication-preflight')
    v = j.verify(source='before')
    state = j.current_json(j.PARENT / j.RUN / 'state.json')
    node = state['nodes']['validate']
    assert node['state'] == 'RUNNING' and node['claim']['executor_id'] == '/root'
    assert Path(node['claim']['workspace']) == j.parent.Q
    value = check_prior_failed_candidate()
    value.update(at=j.s.utc(), executor='/root', argv=list(sys.orig_argv),
        manifest_sha256=j.s.sha(j.Q / 'TRANSFER-MANIFEST.json'), amendment=j.exact_ref(j.R / 'AMENDMENT.json'),
        reviewed_scripts=j.scripts(), release=j.exact_ref(args.release_path),
        claim_input_hash=node['claim']['input_hash'], claim_started_at=node['claim']['claimed_at'],
        expected_payload_hashes=j.manifest()['expected_payload_hashes'],
        Source_before_map_sha256=j.manifest()['Source_before_map_sha256'],
        interpreter=j.interpreter_observation(v), current_source_phase='before',
        Source_publication=False, exit_status=0)
    path = j.R / 'SOURCE-PUBLICATION-PREFLIGHT.json'
    j.write_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + '\n').encode())
    print(json.dumps({'source_publication_preflight': j.exact_ref(path),
        'candidate_full_status': 'FAILED', 'final_acceptance': 'PENDING', 'exit_status': 0}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
