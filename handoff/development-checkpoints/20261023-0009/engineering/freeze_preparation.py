"""Freeze current private checkpoint preparation only; never publish or move refs."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
import argparse,json
import checkpoint_core as c
from verify_prepared import audit,files

def freeze(final_pin):
    c.preparation_claim();c.load_final(final_pin);assert not (c.W/'WORK-FREEZE.json').exists(),'no refreeze'
    outcome=audit(final_pin,require_freeze=False);observed=files(c.W)
    c.save(c.W/'WORK-FREEZE.json',dict(schema_version=1,run_id=c.RUN,final_input_sha256=final_pin,prepared_sha256=c.sha((c.W/'prepared-0002/PREPARED.json').read_bytes()),files=observed,author='/root/status_packet_review',independent_review='PENDING_EXACT_FROZEN_PREPARATION',actual_audit=outcome,canonical_Git_writes=False,publication=False,full_product_acceptance=False))
    print(json.dumps(dict(frozen=True,files=len(observed),work_freeze_sha256=c.sha((c.W/'WORK-FREEZE.json').read_bytes()),full_product_acceptance=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--final-sha256',required=True);freeze(p.parse_args().final_sha256)
