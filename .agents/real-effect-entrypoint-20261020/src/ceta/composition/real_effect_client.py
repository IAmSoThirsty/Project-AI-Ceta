"""Concrete client of the selected native manual-profile pipe.

The trusted launcher supplies its measured server binding and registered actor.
The client never registers itself, chooses code, or sends an approval witness.
"""
import secrets
import time

from ceta.contracts.kernel_transactions import identifier, require
from ceta.contracts.local_ipc import encode_message
from ceta.contracts.manual_effect import OPERATIONS, command_wire
from ceta.contracts.wire import RecordCodec, strict_loads
from ceta.identity.windows_pipe import WindowsServerBinding, send_pipe_request


class ManualEffectClient:
    def __init__(self, codec, server_binding, pipe_name, *, run_id, scope_id,
                 actor_session, receiver_generation):
        require(type(codec) is RecordCodec and type(server_binding) is WindowsServerBinding,
            'MANUAL_CLIENT_SELECTED_SERVER_REQUIRED')
        for value in (run_id, scope_id, actor_session, receiver_generation):
            identifier(value)
        self._codec, self._server, self._pipe = codec, server_binding, pipe_name
        self.run_id, self.scope_id = run_id, scope_id
        self._actor, self._generation = actor_session, receiver_generation
        self._uncertain_effect = None
        self._in_flight = None

    def call(self, kind, *, cpu_rate=None, request_id=None, reason_ref=None):
        require(type(kind) is str and kind in OPERATIONS.values(), 'MANUAL_CLIENT_COMMAND_REQUIRED')
        require(self._in_flight is None, 'MANUAL_CLIENT_CALL_PENDING')
        require(kind not in ('RUN', 'RESTORE') or self._uncertain_effect is None,
            'MANUAL_CLIENT_EFFECT_RECONCILIATION_REQUIRED')
        operation = next(name for name, value in OPERATIONS.items() if value == kind)
        command_id = 'command:' + secrets.token_hex(16)
        body = command_wire(command_id, self.scope_id, self.run_id, kind,
            cpu_rate=cpu_rate, request_id=request_id, reason_ref=reason_ref)
        now = time.time_ns() // 1000000
        wire = encode_message(body, self._codec, message_id='message:' + secrets.token_hex(16),
            sender_session=self._actor, receiver_generation=self._generation,
            operation=operation, issued_at_ms=now, expires_at_ms=now + 30000)
        self._in_flight = wire  # Publish exact submitted bytes before native entry.
        try:
            response = send_pipe_request(self._pipe, wire, self._codec, 30.0,
                expected_server=self._server)
            require(response.manual_result_wire is not None, 'MANUAL_CLIENT_CORRELATED_RESULT_REQUIRED')
            value = strict_loads(response.manual_result_wire)
            if value['kind'] == 'DENIED_RECONCILE' and kind in ('RUN', 'RESTORE'):
                self._uncertain_effect = wire
            return value
        except BaseException as primary:
            if kind in ('RUN', 'RESTORE'):
                self._uncertain_effect = wire
            dict.update(BaseException.__dict__['__dict__'].__get__(primary),
                manual_effect_client=self, manual_effect_request_wire=wire)
            raise
        finally:
            self._in_flight = None
