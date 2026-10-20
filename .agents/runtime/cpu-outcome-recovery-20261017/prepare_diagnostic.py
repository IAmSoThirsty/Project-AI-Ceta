from pathlib import Path
R = Path(__file__).resolve().parent
value = (R/'run_regression.py').read_text(encoding='utf8')
value = value.replace("D.name.startswith('regression-')", "D.name.startswith('diagnostic-')")
start = value.index('for cls in (')
end = value.index('expected = [', start)
value = value[:start] + "suite.addTest(admission.CpuExecutionAdmissionTests('test_operation_wall_budget_bounds_total_admission_separately_from_native_duration'))\n" + value[end:]
value = value.replace('before = inputs()', '''from ceta.kernel import cpu_execution as module
elapsed_trace = []
original_elapsed = module._CpuExecutionCoordinator.elapsed
def observed_elapsed(owner):
    sampled = module.time.perf_counter_ns()
    row = dict(before_highwater=owner.elapsed_highwater, sampled_counter=sampled)
    try:
        result = original_elapsed(owner)
        row['returned_counter'] = result
        return result
    except BaseException as error:
        row['error'] = str(error)
        raise
    finally:
        row['after_highwater'] = owner.elapsed_highwater
        if owner.active is not None:
            row['admission_started'] = owner.active._admission_started
            row['maximum_duration_ns'] = owner.active._request.maximum_duration_ns
        elapsed_trace.append(row)
module._CpuExecutionCoordinator.elapsed = observed_elapsed
before = inputs()''')
value = value.replace('record = dict(frozen_manifest=', 'record = dict(elapsed_trace=elapsed_trace, frozen_manifest=')
with (R/'diagnose_regression.py').open('x', encoding='utf8') as stream: stream.write(value)
