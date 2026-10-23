"""Disposable standalone runner custody controls; standard library only."""
from pathlib import Path
import hashlib,json,sys,unittest
from unittest.mock import patch
import controls as c
import run_challenge as r

OUT=r.W/(sys.argv[1] if len(sys.argv)==2 else 'engine-controls-r2')

class Pure:
    @staticmethod
    def snapshot(path):
        return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    @staticmethod
    def preservation(before,after):
        assert all(after.get(k)==v for k,v in before.items()); return True
    @staticmethod
    def diagnostic(error):
        return None if error is None else dict(type=type.__dict__['__name__'].__get__(type(error)))

class CustodyControls(unittest.TestCase):
    def invoke(self,label,case,**kwargs):
        folder=OUT/label; folder.mkdir()
        with patch.object(r,'SELECTED',['disposable.engine.control']):
            return r.run_observed(unittest.TestSuite([case]),case,c.BINDING,folder,Pure,
                lambda:dict(source='same'),lambda:dict(integrate='pure',owner_authority='pure'),{},
                dict(disposable_control=True,canonical_test_bodies_executed=False),**kwargs)

    def test_success_is_one_body_not_a_positive_timing_measure(self):
        self.assertEqual(self.invoke('success',c.DisposableCase('success')),0)
        report=json.loads((OUT/'success/RESULT.json').read_bytes())
        self.assertEqual(report['tests_run'],1); self.assertTrue(report['test_cohort_passed'])
        self.assertEqual(report['observation']['reproduction'],'NOT_REPRODUCED')
        self.assertEqual(report['provider_spans'],'NOT_MEASURED')
        self.assertTrue((OUT/'success/REPORT-SEAL.json').is_file())

    def test_failure_preserves_counter_fields_and_failure_exit(self):
        self.assertEqual(self.invoke('failure',c.DisposableCase()),1)
        report=json.loads((OUT/'failure/RESULT.json').read_bytes())
        self.assertEqual(report['tests_run'],1); self.assertEqual(report['errors'],1)
        self.assertFalse(report['test_cohort_passed'])
        guard=report['observation']['observations'][0]['evidence']['records'][0]['guard'][0]
        self.assertEqual(guard['elapsed'],50_000_001)
        self.assertTrue((OUT/'failure/REPORT-SEAL.json').is_file())

    def test_result_storage_fault_keeps_original_baseexception(self):
        original=KeyboardInterrupt('disposable primary'); secondary=OSError('disposable storage')
        class Body(unittest.TestCase):
            def runTest(self): raise original
        actual=r.save
        def save(path,value):
            if path.name=='RESULT.json': raise secondary
            return actual(path,value)
        with patch.object(r,'save',save):
            try:self.invoke('storage',Body())
            except BaseException as caught:self.assertIs(caught,original)
            else:self.fail('original must propagate')
        attrs=BaseException.__dict__['__dict__'].__get__(original)
        self.assertIs(dict.get(attrs,'runner_primary_exc_info')[1],original)
        self.assertTrue(any(e is secondary for e in dict.get(attrs,'runner_secondary_errors')))
        self.assertFalse((OUT/'storage/REPORT-SEAL.json').exists())
        self.assertTrue((OUT/'storage/REPORT-ERROR.json').exists())

    def test_seal_storage_fault_keeps_captured_guard_failure(self):
        secondary=OSError('disposable seal'); case=c.DisposableCase(); held=[]
        original_method=case.runTest
        def body():
            try:original_method()
            except c.ControlError as error:held.append(error); raise
        case.runTest=body; actual=r.save
        def save(path,value):
            if path.name=='REPORT-SEAL.json':raise secondary
            return actual(path,value)
        with patch.object(r,'save',save):
            try:self.invoke('seal',case)
            except BaseException as caught:self.assertIs(caught,held[0])
            else:self.fail('original must propagate')
        self.assertFalse((OUT/'seal/REPORT-SEAL.json').exists())
        self.assertTrue((OUT/'seal/REPORT-ERROR.json').exists())

    def test_exact_independent_runtimeerror_message_is_persisted(self):
        marker='INDEPENDENT_STORAGE_BOUNDARY_8f9308: database read refused'
        class Body(unittest.TestCase):
            def runTest(self):raise RuntimeError(marker)
        self.assertEqual(self.invoke('unrelated-witness',Body()),1)
        folder=OUT/'unrelated-witness'
        for name in ('RESULT.json','TESTS.log'):
            self.assertIn(marker,(folder/name).read_text(encoding='utf-8'))
        report=json.loads((folder/'RESULT.json').read_bytes())
        self.assertEqual(report['errors'],1);self.assertFalse(report['test_cohort_passed'])
        self.assertEqual(report['observation']['observations'][0]['evidence']['owner_guard'],'NOT_CAPTURED')
        detail=report['formatted_outcomes']['errors'][0]
        self.assertEqual(detail['test_id'],'disposable.engine.control');self.assertIsNone(detail['subtest_ordinal'])
        self.assertEqual(detail['identity_status'],'KNOWN_CASE')

    def test_assertion_reason_and_cause_use_exact_existing_superclass_text(self):
        marker='TM2_ASSERTION_REASON_72a';cause='TM2_ASSERTION_CAUSE_b73';texts=[];calls=[]
        class Reason(AssertionError):
            def __str__(self):calls.append('standard-formatter');return marker
        class Body(unittest.TestCase):
            def runTest(self):
                try:raise RuntimeError(cause)
                except RuntimeError as primary:raise Reason() from primary
        # Preserve the existing explicit cause and reason without a second formatter.
        original=unittest.TestResult.addFailure
        def base(result,test,err):
            original(result,test,err);texts.append(result.failures[-1][1])
        with patch.object(unittest.TestResult,'addFailure',base):self.assertEqual(self.invoke('assertion-witness',Body()),1)
        report=json.loads((OUT/'assertion-witness/RESULT.json').read_bytes())
        detail=report['formatted_outcomes']['failures'][0]
        self.assertEqual(detail['formatted_text'],texts[0]);self.assertIn(marker,texts[0]);self.assertIn(cause,texts[0])
        self.assertEqual(calls,['standard-formatter'])
        self.assertIn(marker,(OUT/'assertion-witness/TESTS.log').read_text(encoding='utf-8'))
        self.assertEqual(detail['test_id'],'disposable.engine.control')

    def test_failing_subtest_texts_keep_known_case_and_original_ordinals(self):
        markers=['TM2_SUBTEST_REASON_1_bf9','TM2_SUBTEST_REASON_2_1de']
        class Body(unittest.TestCase):
            def runTest(self):
                for index,marker in enumerate(markers):
                    with self.subTest(index=index):raise AssertionError(marker)
        self.assertEqual(self.invoke('subtest-witness',Body()),1)
        folder=OUT/'subtest-witness';report=json.loads((folder/'RESULT.json').read_bytes())
        details=report['formatted_outcomes']['failures']
        self.assertEqual(report['failures'],2);self.assertEqual(report['errors'],0)
        self.assertEqual([d['subtest_ordinal'] for d in details],[1,2])
        self.assertEqual([d['test_id'] for d in details],['disposable.engine.control']*2)
        for index,marker in enumerate(markers):
            self.assertIn(marker,details[index]['formatted_text'])
            self.assertIn(marker,(folder/'TESTS.log').read_text(encoding='utf-8'))

    def test_report_fault_cannot_replace_captured_guard_failure(self):
        secondary=SystemExit('disposable report'); case=c.DisposableCase()
        original_method=case.runTest; held=[]
        def body():
            try:original_method()
            except c.ControlError as error:held.append(error); raise
        case.runTest=body
        with patch.object(r.observer.PostmortemResult,'report',side_effect=secondary):
            try:self.invoke('report',case)
            except BaseException as caught:self.assertIs(caught,held[0])
            else:self.fail('original must propagate')
        self.assertFalse((OUT/'report/REPORT-SEAL.json').exists())
        self.assertTrue((OUT/'report/REPORT-ERROR.json').exists())

if __name__=='__main__':
    OUT.mkdir(exist_ok=False)
    pins={n:r.sha(r.W/n) for n in ('run_challenge.py','owner_timing_observer.py','controls.py','engine_controls.py')}
    with (OUT/'TESTS.log').open('x',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CustodyControls))
    report=dict(successful=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        tested_source=pins,canonical_test_bodies_executed=False,canonical_fixture_writes=False,product_result=False)
    r.save(OUT/'RESULT.json',report)
    print(json.dumps(report,indent=2)); raise SystemExit(0 if result.wasSuccessful() else 1)
