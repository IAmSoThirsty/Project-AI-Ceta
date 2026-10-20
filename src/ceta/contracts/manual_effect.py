"""Additive manual-profile command data; no proof/configuration travels here."""
from dataclasses import dataclass

from .kernel_transactions import digest, identifier, require
from .wire import canonical_bytes, strict_loads

PROFILE = 'ceta-manual-effect-command-v1'
OPERATIONS = {'manual.run': 'RUN', 'manual.restore': 'RESTORE',
    'manual.inspect': 'INSPECT', 'manual.reconcile': 'RECONCILE', 'manual.stop': 'STOP'}
FIELDS = {'profile', 'record_type', 'command_id', 'scope_id', 'kind', 'run_id',
    'request_id', 'cpu_rate', 'reason_ref'}


@dataclass(frozen=True)
class ManualEffectCommand:
    original_wire: bytes

    def __post_init__(self):
        _value(self.original_wire)

    @property
    def record_type(self):
        return 'ManualEffectCommand'

    @property
    def record_id(self):
        return self.as_dict()['command_id']

    @property
    def commitment(self):
        return digest('manual-effect-command-v1', self.as_dict())

    def as_dict(self):
        return _value(self.original_wire)


def _value(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= 4096, 'MANUAL_COMMAND_SIZE')
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == FIELDS
        and value['profile'] == PROFILE and value['record_type'] == 'ManualEffectCommand'
        and canonical_bytes(value) == wire, 'MANUAL_COMMAND_FIELDS')
    for name in ('command_id', 'scope_id', 'run_id'):
        identifier(value[name])
    require(type(value['kind']) is str and value['kind'] in OPERATIONS.values(),
        'MANUAL_COMMAND_KIND')
    kind = value['kind']
    require((kind == 'RUN' and type(value['cpu_rate']) is int and 1 <= value['cpu_rate'] < 10000)
        or (kind != 'RUN' and value['cpu_rate'] is None), 'MANUAL_COMMAND_CPU_RATE')
    if kind in ('RESTORE', 'RECONCILE'):
        identifier(value['request_id'])
    else:
        require(value['request_id'] is None, 'MANUAL_COMMAND_UNEXPECTED_REQUEST')
    if kind == 'STOP':
        identifier(value['reason_ref'])
    else:
        require(value['reason_ref'] is None, 'MANUAL_COMMAND_UNEXPECTED_REASON')
    return value


def decode_command(wire):
    return ManualEffectCommand(wire)


def command_wire(command_id, scope_id, run_id, kind, *, request_id=None,
                 cpu_rate=None, reason_ref=None):
    wire = canonical_bytes(dict(profile=PROFILE, record_type='ManualEffectCommand',
        command_id=command_id, scope_id=scope_id, run_id=run_id, kind=kind,
        request_id=request_id, cpu_rate=cpu_rate, reason_ref=reason_ref))
    decode_command(wire)
    return wire


def encode_result(binding, result):
    from .wire import ContractError
    require(type(binding) is dict, 'MANUAL_RESULT_BINDING')
    if type(result) is ContractError:
        value = dict(profile='ceta-manual-effect-result-v1', version=1, **binding,
            kind='DENIED_RECONCILE', error_code=result.code, state=None)
    else:
        require(type(result) is dict, 'MANUAL_RESULT_STATE_REQUIRED')
        value = dict(profile='ceta-manual-effect-result-v1', version=1, **binding,
            kind='MANUAL_STATE', error_code=None, state=result)
    wire = canonical_bytes(value)
    decode_result(wire, binding)
    return wire


def decode_result(wire, binding):
    import re
    require(type(wire) is bytes and 1 <= len(wire) <= 262144, 'MANUAL_RESULT_SIZE')
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == set(binding) |
        {'profile', 'version', 'kind', 'error_code', 'state'}
        and value['profile'] == 'ceta-manual-effect-result-v1'
        and type(value['version']) is int and value['version'] == 1
        and canonical_bytes(value) == wire, 'MANUAL_RESULT_FIELDS')
    require(all(type(value[k]) is type(v) and value[k] == v for k,v in binding.items()),
        'MANUAL_RESULT_REQUEST_BINDING')
    if value['kind'] == 'DENIED_RECONCILE':
        require(type(value['error_code']) is str
            and re.fullmatch('[A-Z][A-Z0-9_]{0,79}', value['error_code'])
            and value['state'] is None, 'MANUAL_RESULT_DENIAL')
    else:
        require(value['kind'] == 'MANUAL_STATE' and value['error_code'] is None
            and type(value['state']) is dict, 'MANUAL_RESULT_STATE_REQUIRED')
    return value
