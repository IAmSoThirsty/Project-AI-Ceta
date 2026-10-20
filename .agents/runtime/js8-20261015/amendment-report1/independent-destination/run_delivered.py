"""Dormant exact180 actual-Source review; the Root release precedes imports."""
from pathlib import Path
import argparse
import importlib
import json
import os
import sys
import threading
import unittest
from review_support import (F,R,Q,V,ACTOR,PIN,PY,j,s,preparation,require_delivery_release,
    route_fixture_globals,verify_method_asts,deny_profile_and_restricted_operations,NativeSevenWitness)
from resource_observer import Observer


def module_observations():
    product={name:s.ordinary(Path(module.__file__)) for name,module in sys.modules.items()
        if (name=='ceta' or name.startswith('ceta.')) and getattr(module,'__file__',None)}
    tests={name:s.ordinary(Path(module.__file__)) for name,module in sys.modules.items()
        if name.startswith('test_') and getattr(module,'__file__',None)}
    assert all(Path(row['path']).is_relative_to(F/'src') for row in product.values())
    assert all(Path(row['path']).is_relative_to(F/'tests/contract') for row in tests.values())
    expected=j.manifest()['expected_payload_hashes']
    for row in (*product.values(),*tests.values()):
        name=Path(row['path']).relative_to(F).as_posix()
        assert row['sha256']==expected[name]
    return dict(ceta_imports=product,test_imports=tests)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    release=require_delivery_release(args.release_path,args.release_sha256);p=preparation();m=j.manifest()
    assert not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules)
    fixture=Path(p['fixture_root']);s.fs.safe_components(fixture,allow_missing=True);assert not fixture.exists()
    before={name:s.ordinary(F/name)['sha256'] for name in m['expected_payload_hashes']}
    assert before==m['expected_payload_hashes'];verify_method_asts(p['required_ids'],p['test_method_AST_hashes'])
    output=V/'delivered-r1';output.mkdir(exist_ok=False);temporary=output/'temporary';temporary.mkdir()
    j.write_bytes(output/'ATTEMPT.json',(json.dumps(dict(release=j.exact_ref(args.release_path),
        manifest_sha256=PIN,application=release['application'],automatic_retry=False))+'\n').encode())
    fixture.mkdir(exist_ok=False);fixture_identity=s.fs.file_identity(s.fs.lstat(fixture))
    os.environ.update(QT_QPA_PLATFORM='offscreen',TEMP=str(temporary),TMP=str(temporary))
    sys.path[:0]=[str(F/'src'),str(F/'tools'),str(F/'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
    sqlite=load_sqlite();sqlite_identity=runtime_identity()
    for name in sorted({value.split('.')[0] for value in p['required_ids']}):importlib.import_module(name)
    routes,mappers=route_fixture_globals(fixture)
    loader=unittest.TestLoader();suite=loader.loadTestsFromNames(p['required_ids'])
    expected=list(j.ids(suite));assert not loader.errors and expected==p['required_ids']
    assert len(expected)==180 and not any('_FailedTest' in value for value in expected)
    assert expected[-7:]==p['native_cpu_ids']
    preflight=dict(at=s.utc(),manifest_sha256=PIN,expected_ids=expected,**module_observations(),
        fixture_root=str(fixture),fixture_identity=fixture_identity,fixture_global_routes=routes,
        sqlite_runtime=sqlite_identity,assertion_or_deadline_changes=False)
    j.write_bytes(output/'PREFLIGHT.json',(json.dumps(preflight,indent=2)+'\n').encode())
    from fixture_runtime import NativeObservations
    native=NativeObservations();physical=Observer(sqlite);active=[None]
    threads=set(threading.enumerate());executed=[];stopped=[];result=primary=None
    raw=lifetimes=witness=None;forbidden=[];restriction_restore=None
    class Result(unittest.TextTestResult):
        def startTest(self,test):
            active[0]=native.active_case=test.id()
            if test.id()==p['native_cpu_ids'][0]:
                assert len(executed)==173 and executed==expected[:173]
                witness.install()
            executed.append(test.id());super().startTest(test)
        def stopTest(self,test):
            try:physical.observe_case(test)
            finally:
                stopped.append(test.id());super().stopTest(test)
                native.active_case=active[0]=None
    started=s.utc()
    try:
        native.install();forbidden,restriction_restore=deny_profile_and_restricted_operations();physical.install()
        raw=(output/'RAW.txt').open('x',encoding='utf8',buffering=1)
        lifetimes=(output/'LIFETIMES.jsonl').open('x',encoding='utf8',buffering=1)
        witness=NativeSevenWitness(fixture,active,lifetimes)
        result=unittest.TextTestRunner(stream=raw,verbosity=2,resultclass=Result).run(suite)
    except BaseException as error:primary=error
    finally:
        # Restore observations; never retry an uncertain inner native cleanup.
        operations=[]
        if witness is not None:operations.append((witness.uninstall,'native7-observer-uninstall'))
        if restriction_restore is not None:
            cls,original=restriction_restore
            operations.append((lambda:setattr(cls,'__init__',original),'restricted-denial-uninstall'))
        operations.extend(((native.uninstall,'native-observer-uninstall'),(physical.uninstall,'physical-observer-uninstall')))
        for operation,label in operations:
            try:operation()
            except BaseException as error:
                if primary is None:primary=error
                else:j.retain(primary,error,label)
        for stream,label in ((lifetimes,'lifetimes-close'),(raw,'delivered-raw-close')):
            if stream is not None:
                try:j.close(stream,primary,label)
                except BaseException as error:
                    if primary is None:primary=error
                    else:j.retain(primary,error,label,stream)
    try:
        custody=physical.finish();native_proof=native.finish()
        native7=witness.finish() if witness is not None else dict(owned_resources_closed=False,not_installed=True)
        receipts=list(sys.modules['test_cpu_execution_admission'].NATIVE_ADMISSION_RECEIPTS)
        assert len(receipts)==8
        custody['launcher_native_file_observations']=list(sys.modules['test_launcher_custody_paths'].NATIVE_FILE_OBSERVATIONS)
        junctions=[row for row in custody['launcher_native_file_observations'] if row['kind']=='owned-native-junction']
        junctions_closed=(len(junctions)==3 and all(row['creation_handle_closed'] is True
            and row['post_close_GetHandleInformation_error']==6 for row in junctions))
        custody['junction_creation_handles_closed']=junctions_closed
        if not junctions_closed:custody['remaining_resources'].append(dict(kind='unverified-junction-creation-closure',expected=3,observed=len(junctions)))
        if not native_proof['owned_resources_closed']:custody['remaining_resources'].append(dict(kind='unverified-captured-native-owners'))
        if not native7['owned_resources_closed']:custody['remaining_resources'].append(dict(kind='unverified-native-seven-custody'))
        custody['owned_resources_closed']=custody['owned_resources_closed'] and not custody['remaining_resources']
        remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
        after={name:s.ordinary(F/name)['sha256'] for name in m['expected_payload_hashes']};j.verify(source='after')
        current_fixture=s.fs.file_identity(s.fs.lstat(fixture))
        assert all(current_fixture[key]==fixture_identity[key] for key in ('device','inode'))
        assert all(Path(path).is_relative_to(fixture) for mapper in mappers for path in mapper.routes)
        imports=module_observations()
        counts=dict(tests_run=result.testsRun if result is not None else len(executed),
            failures=len(result.failures) if result is not None else 0,errors=len(result.errors) if result is not None else 0,
            skips=len(result.skipped) if result is not None else 0)
        success=(primary is None and result is not None and result.wasSuccessful() and not counts['skips']
            and expected==executed==stopped and before==after==m['expected_payload_hashes']
            and not remaining and not forbidden and custody['owned_resources_closed'])
        for name,value in (('CUSTODY.json',custody),('NATIVE-OWNERS.json',native_proof),('NATIVE-SEVEN-CUSTODY.json',native7),
            ('NATIVE-ADMISSION-RECEIPTS.json',receipts),('IMPORTS-AFTER.json',imports)):
            j.write_bytes(output/name,(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
        proof=dict(started_at=started,finished_at=s.utc(),reviewer=ACTOR,manifest_sha256=PIN,
            application=release['application'],destination_full=release['destination_full'],destination_full_launch=release['destination_full_launch'],
            expected_ids=expected,executed_ids=executed,stopped_ids=stopped,**counts,
            expected_payload_hashes=m['expected_payload_hashes'],before_hashes=before,after_hashes=after,
            remaining_threads=remaining,remaining_resources=custody['remaining_resources'],owned_resources_closed=custody['owned_resources_closed'],
            custody=j.exact_ref(output/'CUSTODY.json'),native_owners_proof=j.exact_ref(output/'NATIVE-OWNERS.json'),
            native_cpu_custody=j.exact_ref(output/'NATIVE-SEVEN-CUSTODY.json'),native_admission_receipts=j.exact_ref(output/'NATIVE-ADMISSION-RECEIPTS.json'),
            fixture_root=str(fixture),fixture_identity=fixture_identity,fixture_paths=[path for mapper in mappers for path in mapper.routes],
            commands=[dict(command=s.subprocess.list2cmdline(list(sys.orig_argv)),exit_status=0 if success else 1)],
            failure_details=[(test.id(),detail) for test,detail in result.failures+result.errors] if result is not None else [],
            primary_error=type(primary).__name__ if primary is not None else None,forbidden_calls=forbidden,
            raw=j.exact_ref(output/'RAW.txt'),lifetimes=j.exact_ref(output/'LIFETIMES.jsonl'),
            authority_capacity_settlement='CONTROLLED original provider fixtures; actual disposable ordinary worker/clock/class15 only',
            no_profile_or_Hello=True,Source_publication=False,Source_accepted=False,full_suite=False,exit_status=0 if success else 1)
        j.write_bytes(output/'RESULT.json',(json.dumps(proof,indent=2,allow_nan=False)+'\n').encode())
    except BaseException as secondary:
        if primary is None:raise
        j.retain(primary,secondary,'delivered-post-test-diagnostics');raise primary
    if primary is not None:raise primary
    return proof['exit_status']


if __name__=='__main__':sys.exit(main())
