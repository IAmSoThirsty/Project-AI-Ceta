"""Postmortem-only owner timing observation; standard library, no clock reads.

Binding is supplied by trusted composition. This module neither imports CETA
nor executes a provider, test body, SQL statement, native helper or effect.
"""
from dataclasses import dataclass
import json
import types
import unittest

NOT_CAPTURED = 'NOT_CAPTURED'
_MISSING = object()
_LIMIT = (1 << 63) - 1
CLOCK_FIELDS = ('boot_id', 'durable_epoch', 'resume_generation', 'monotonic_ns',
                'wall_time_ns', 'uncertainty_ns', 'wall_trusted')
DEADLINE_FIELDS = ('boot_id', 'durable_epoch', 'resume_generation',
    'issued_monotonic_ns', 'expires_monotonic_ns', 'issued_earliest_wall_ns',
    'expires_wall_ns')


@dataclass(frozen=True)
class Binding:
    guard_code: types.CodeType
    commit_code: types.CodeType
    entry_codes: tuple
    owner_type: type
    kernel_type: type
    enrollment_type: type
    clock_type: type
    deadline_type: type
    request_type: type | None = None


def _primitive(value):
    typ = type(value)
    return typ is str or typ is int or typ is bool or typ is type(None)


def _raw(value, expected, name):
    """Read exact-type raw storage through builtin descriptors only."""
    if type(value) is not expected:
        return _MISSING
    # Bypass even metaclass properties. Binding supplies the trusted type.
    mro = type.__dict__['__mro__'].__get__(expected)
    mappings = [type.__dict__['__dict__'].__get__(base) for base in mro]
    for mapping in mappings:
        member = mapping.get(name, _MISSING)
        if type(member) is types.MemberDescriptorType:
            try:
                return types.MemberDescriptorType.__get__(member, value, expected)
            except AttributeError:
                return _MISSING
        if member is not _MISSING and not _primitive(member):
            return _MISSING  # Never invoke a property or user descriptor.
    for mapping in mappings:
        member = mapping.get('__dict__', _MISSING)
        if member is not _MISSING:
            if type(member) is not types.GetSetDescriptorType:
                return _MISSING
            data = types.GetSetDescriptorType.__get__(member, value, expected)
            return dict.get(data, name, _MISSING) if type(data) is dict else _MISSING
    return _MISSING


def _scalar(value, kind):
    if type(value) is not kind:
        return _MISSING
    if kind is int and not -_LIMIT-1 <= value <= _LIMIT:
        return _MISSING
    if kind is str and len(value) > 1024:
        return _MISSING
    return value


def _record(value, expected, names):
    fields, missing = {}, []
    for name in names:
        kind = str if name == 'boot_id' else bool if name == 'wall_trusted' else int
        found = _scalar(_raw(value, expected, name), kind)
        if found is _MISSING:
            missing.append(name)
        else:
            fields[name] = found
    return dict(status='CAPTURED' if not missing else NOT_CAPTURED,
                fields=fields, missing=missing)


def _error_code(error):
    data = BaseException.__dict__['__dict__'].__get__(error)
    value = _MISSING
    for index, (key, candidate) in enumerate(dict.items(data)):
        if index >= 64: break
        if type(key) is str and key == 'code':
            value = candidate
            break
    value = _scalar(value, str)
    return NOT_CAPTURED if value is _MISSING else value


def _type_name(error):
    member = type.__dict__['__name__']
    value = types.GetSetDescriptorType.__get__(member, type(error), type)
    return str.__getitem__(value, slice(0, 128)) if type(value) is str else NOT_CAPTURED


def _trace(tb):
    frames, seen = [], set()
    while tb is not None:
        if type(tb) is not types.TracebackType or id(tb) in seen or len(frames) >= 64:
            return frames, False
        seen.add(id(tb))
        frames.append((tb.tb_frame, tb.tb_lineno))
        tb = tb.tb_next
    return frames, True


def _guard(frame, frames, binding):
    data = frame.f_locals
    owner, context = dict.get(data, 'self'), dict.get(data, 'context', _MISSING)
    enrollment = dict.get(data, 'enrollment', _MISSING)
    kernel = _raw(owner, binding.owner_type, 'k')
    commit = any(f.f_code is binding.commit_code
        and dict.get(f.f_locals, 'self') is owner
        and dict.get(f.f_locals, 'context', _MISSING) is context
        and dict.get(f.f_locals, 'enrollment', _MISSING) is enrollment
        for f, _ in frames)
    entry = any(any(f.f_code is code for code in binding.entry_codes)
        and dict.get(f.f_locals, 'self') is kernel
        and dict.get(f.f_locals, 'request_context', _MISSING) is context
        for f, _ in frames)
    if (type(owner) is not binding.owner_type or type(kernel) is not binding.kernel_type
            or type(enrollment) is not binding.enrollment_type
            or context is _MISSING or not commit or not entry):
        return dict(status=NOT_CAPTURED, reason='CONTEXT_BINDING_FAILED')
    result = dict(status='CAPTURED', context_bound=True, provider_spans='NOT_MEASURED',
                  derived_after_failure=True, bound_ns=50_000_000)
    missing = []
    for name in ('phase', 'started', 'finished', 'elapsed'):
        value = _scalar(dict.get(data, name, _MISSING), str if name == 'phase' else int)
        if value is _MISSING:
            missing.append(name)
        else:
            result[name] = value
    resolution = _scalar(_raw(owner, binding.owner_type, '_resolution_ns'), int)
    if resolution is _MISSING:
        missing.append('resolution_ns')
    else:
        result['resolution_ns'] = resolution
    for name in ('previous', 'sample', 'highwater'):
        result[name] = _record(dict.get(data, name, _MISSING), binding.clock_type, CLOCK_FIELDS)
    deadline = _raw(enrollment, binding.enrollment_type, 'deadline')
    result['enrollment_deadline'] = _record(deadline, binding.deadline_type, DEADLINE_FIELDS)
    request = dict.get(data, 'request')
    result['request_deadline'] = (dict(status='ABSENT') if request is None else
        _record(_raw(request, binding.request_type, 'deadline'), binding.deadline_type, DEADLINE_FIELDS))
    identity = _scalar(_raw(enrollment, binding.enrollment_type, 'request_id'), str)
    result['enrollment_id'] = NOT_CAPTURED if identity is _MISSING else identity
    if not missing:
        result['raw_delta_ns'] = result['finished'] - result['started']
        result['charge_matches'] = result['elapsed'] == result['raw_delta_ns'] + 2*resolution
        current, limit = result['sample'], result['enrollment_deadline']
        if current['status'] == limit['status'] == 'CAPTURED':
            clock, bound = current['fields'], limit['fields']
            monotonic = clock['monotonic_ns'] + result['elapsed']
            wall = clock['wall_time_ns'] + clock['uncertainty_ns'] + result['elapsed']
            result['derived'] = dict(monotonic_bound_ns=monotonic, wall_bound_ns=wall,
                monotonic_margin_ns=bound['expires_monotonic_ns']-monotonic,
                wall_margin_ns=bound['expires_wall_ns']-wall,
                deadline_domains_match=all(clock[n] == bound[n] for n in
                    ('boot_id', 'durable_epoch', 'resume_generation')))
    result['missing'] = missing
    if missing or result['sample']['status'] != 'CAPTURED' or result['enrollment_deadline']['status'] != 'CAPTURED':
        result['status'] = NOT_CAPTURED
    return result


def extract(err, binding):
    """Copy selected primitive evidence while preserving the original triple."""
    pending, seen, records, complete = [(err[1], err[2])], set(), [], True
    while pending:
        if len(seen) >= 8:
            complete = False
            break
        error, tb = pending.pop(0)
        if id(error) in seen:
            continue
        seen.add(id(error))
        frames, bounded = _trace(tb)
        complete = complete and bounded
        guards = [_guard(frame, frames, binding) for frame, _ in frames
                  if frame.f_code is binding.guard_code]
        records.append(dict(error_type=_type_name(error), code=_error_code(error),
            guard=guards, trace=[dict(file=f.f_code.co_filename,
                function=f.f_code.co_name, line=line) for f, line in frames]))
        for name in ('__cause__', '__context__'):
            other = BaseException.__dict__[name].__get__(error)
            if other is not None and id(other) not in seen:
                pending.append((other, BaseException.__dict__['__traceback__'].__get__(other)))
    return dict(records=records, chain_complete=complete,
                owner_guard='CAPTURED' if any(g['status'] == 'CAPTURED' for r in records for g in r['guard']) else NOT_CAPTURED)


def _subtest_identity(test, subtest):
    """Preserve exact primitive parameter layers without invoking id/str/repr."""
    typ = unittest.case._SubTest
    if type(subtest) is not typ or _raw(subtest, typ, 'test_case') is not test:
        return dict(status=NOT_CAPTURED, reason='SUBTEST_OWNER_CHANGED')
    message = _raw(subtest, typ, '_message')
    absent = message is unittest.case._subtest_msg_sentinel
    if not absent and not _primitive(message):
        return dict(status=NOT_CAPTURED, reason='UNSUPPORTED_SUBTEST_MESSAGE')
    params = _raw(subtest, typ, 'params')
    maps = _raw(params, unittest.case._OrderedChainMap, 'maps')
    if type(maps) is not list or len(maps) > 8:
        return dict(status=NOT_CAPTURED, reason='UNSUPPORTED_SUBTEST_PARAMETERS')
    layers = []
    for mapping in maps:
        if type(mapping) is not dict or len(mapping) > 32:
            return dict(status=NOT_CAPTURED, reason='UNSUPPORTED_SUBTEST_PARAMETERS')
        layer = []
        for name, value in dict.items(mapping):
            if type(name) is not str or len(name) > 160 or not _primitive(value):
                return dict(status=NOT_CAPTURED, reason='UNSUPPORTED_SUBTEST_PARAMETER')
            if value is not None and _scalar(value, type(value)) is _MISSING:
                return dict(status=NOT_CAPTURED, reason='SUBTEST_PARAMETER_BOUND')
            layer.append([name, value])
        layers.append(layer)
    if not absent and message is not None and _scalar(message, type(message)) is _MISSING:
        return dict(status=NOT_CAPTURED, reason='SUBTEST_MESSAGE_BOUND')
    return dict(status='CAPTURED', message_absent=absent,
                message=None if absent else message, parameter_layers=layers)


class PostmortemResult(unittest.TestResult):
    """Observe before superclass; preserve original outcome through reporter faults."""
    def __init__(self, binding, test_bindings, sink=None):
        super().__init__()
        self.binding, self.test_bindings, self.sink = binding, tuple(test_bindings), sink
        self.observations, self.faults, self.originals, self.super_calls = [], [], [], []
        self.coverage_complete = True

    def _fault(self, stage, error):
        self.coverage_complete = False
        list.append(self.faults, (stage, error, BaseException.__dict__['__traceback__'].__get__(error)))

    def _observe(self, kind, test, subtest, err, parent):
        list.append(self.originals, (kind, test, subtest, err))
        bucket = self.failures if issubclass(err[0], AssertionError) else self.errors
        before = len(bucket)
        try:
            identity = next(name for value, name in self.test_bindings if value is test)
            record = dict(kind=kind, test_id=identity, subtest_ordinal=None,
                          evidence=extract(err, self.binding))
            if not record['evidence']['chain_complete'] or any(g['status'] != 'CAPTURED'
                    for r in record['evidence']['records'] for g in r['guard']):
                self.coverage_complete = False
            if subtest is not None:
                record['subtest_ordinal'] = 1 + sum(r['kind'] == 'subtest' and r['test_id'] == identity
                    for r in self.observations)
                record['subtest_identity'] = _subtest_identity(test, subtest)
                if record['subtest_identity']['status'] != 'CAPTURED': self.coverage_complete = False
            list.append(self.observations, record)
            if self.sink is not None:
                self.sink(record)
        except BaseException as error:
            self._fault('COLLECTOR_OR_STORAGE', error)
        finally:
            list.append(self.super_calls, kind)
            try:
                parent()
            except BaseException as error:
                self._fault('SUPERCLASS_FORMATTING', error)
                if len(bucket) == before:
                    list.append(bucket, (subtest if subtest is not None else test,
                        'Original exception triple retained; superclass formatting failed.'))

    def addError(self, test, err):
        self._observe('error', test, None, err, lambda: super(PostmortemResult, self).addError(test, err))

    def addFailure(self, test, err):
        self._observe('failure', test, None, err, lambda: super(PostmortemResult, self).addFailure(test, err))

    def addSubTest(self, test, subtest, err):
        if err is None:
            return super().addSubTest(test, subtest, err)
        self._observe('subtest', test, subtest, err,
            lambda: super(PostmortemResult, self).addSubTest(test, subtest, err))

    def report(self, encoder=json.dumps):
        captured = any(r['evidence']['owner_guard'] == 'CAPTURED' for r in self.observations)
        result = dict(coverage_complete=self.coverage_complete,
            functional_success=self.wasSuccessful(), observations=self.observations,
            reproduction=('OBSERVED_OWNER_GUARD_FAILURE' if captured else
                'NOT_REPRODUCED' if self.wasSuccessful() else NOT_CAPTURED),
            successful_guard_timings='NOT_MEASURED', provider_spans='NOT_MEASURED',
            faults=[dict(stage=stage, type=_type_name(error)) for stage, error, _ in self.faults])
        try:
            encoder(result, allow_nan=False)
        except BaseException as error:
            self._fault('REPORT_FORMATTING', error)
            return dict(coverage_complete=False, functional_success=self.wasSuccessful(),
                        status='DIAGNOSTIC_INCOMPLETE')
        return result
