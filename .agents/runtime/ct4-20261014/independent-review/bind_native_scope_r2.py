"""Bind actual retained native proof without expanding its stated census scope."""
from ct4_support import *
full_path=F/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json'
full=read(full_path)
prior=F/'.agents/runtime/perf1-20261014/independent-destination/source384-r1.json';native=read(prior)
assert full['tests_run']==1479 and full['native_census']['exit_status']==0 and full['native_census']['result']=={'clear':True,'children':[]}
assert native['tests_run']==384 and native['all_native_exit_empty_closed'] is True and len(native['native_lifetimes'])==17
assert len({(r['pid'],r['creation_time']) for r in native['native_lifetimes']})==17
save(V/'retained-native-proof-scope.json',{'executor':ACTOR,'recorded_at':utc(),'accepted_full_Source_suite':ref(full_path),
    'native_census':full['native_census'],'census_scope':'Actual Source client_process.py and service_process.py Python commands only; not a host-wide process/handle census.',
    'independent_PERF_delivered_Source_proof':ref(prior),'distinct_native_lifetimes':native['native_lifetimes'],'native_lifetimes_count':17,
    'all_native_exit_empty_closed':True,'qualification':'The 17 actual PID/creation tuples and cleanup evidence belong to the independently verified PERF delivered Source384 cut. They are retained evidence for the accepted 290-payload baseline, not new CT4 native process runs. CT4 performs native file replacements in owned fixtures and launches no workload.',
    'CT4_native_processes_launched':0,'exit_status':0})
print(json.dumps({'native_lifetimes':17,'proof_sha256':sha(V/'retained-native-proof-scope.json')}))
