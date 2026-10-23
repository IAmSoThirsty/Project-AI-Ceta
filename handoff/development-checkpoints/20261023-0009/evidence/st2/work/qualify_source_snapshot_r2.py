from pathlib import Path
import json,time,os,traceback
import status_core as s
output=s.W/'source-snapshot-qualification-r2';output.mkdir(exist_ok=False)
s.save(output/'INTENT.json',dict(scope='READ_ONLY_FULL_SOURCE_UNDER_EXPLICIT_STOCK_POLICY',canonical_mutation=False,full_product_acceptance=False))
started=time.perf_counter_ns()
try:
 observation=s.snapshot(s.F,s.F);s.save(output/'OBSERVATION.json',observation)
 s.save(output/'RESULT.json',dict(successful=True,files=len(observation['files']),directories=len(observation['directories']),excluded_symlinks=len(observation['excluded_symlinks']),bytes=sum(x['bytes'] for x in observation['files'].values()),elapsed_ns=time.perf_counter_ns()-started,observation_sha256=s.sha(output/'OBSERVATION.json'),canonical_mutation=False,full_product_acceptance=False))
except BaseException:
 s.save(output/'RESULT.json',dict(successful=False,elapsed_ns=time.perf_counter_ns()-started,traceback=traceback.format_exc(),canonical_mutation=False,full_product_acceptance=False));raise
