"""Draft/view use case over an injected owned-service port, with no authority."""
import json

from ceta.contracts.kernel_transactions import require
from ceta.contracts.local_ipc import SubmissionUncertain
from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, RecordCodec


class OperatorSession:
    def __init__(self, service, codec):
        require(type(codec) is RecordCodec, "OPERATOR_CODEC_REQUIRED")
        self._service, self._codec = service, codec
        self._view, self._view_generation, self._drafts = "view:default", 0, {"view:default": ""}
        self._attempt, self._attempt_view, self._handled = None, None, None
        self.status, self.detail, self.result_text = "STARTING", "Inspecting service state.", ""

    def resource_diagnostics(self, envelope, *, maximum_age_ns=1_000_000_000,
                             sample_interval_ns=100_000_000, cancelled=None):
        """Explicit read-only runtime observation; task drafts are unaffected."""
        observed = self._service.snapshot()
        require(observed.get("state") == "READY", "OPERATOR_DIAGNOSTICS_OWNER_UNAVAILABLE")
        return self._service.resource_diagnostics(expected_generation=observed.get("generation"),
            envelope=envelope, maximum_age_ns=maximum_age_ns,
            sample_interval_ns=sample_interval_ns, cancelled=cancelled)

    @property
    def draft(self): return self._drafts[self._view]

    def set_draft(self, text):
        require(type(text) is str, "OPERATOR_DRAFT_SIZE")
        try:
            size = len(text.encode("utf8"))
        except UnicodeError as error:
            raise ContractError("OPERATOR_DRAFT_ENCODING") from error
        require(size <= MAX_WIRE_BYTES, "OPERATOR_DRAFT_SIZE")
        self._drafts[self._view] = text

    def select_view(self, view_ref):
        require(type(view_ref) is str and 1 <= len(view_ref) <= 160, "OPERATOR_VIEW_REQUIRED")
        self._view, self._view_generation = view_ref, self._view_generation + 1
        self._drafts.setdefault(view_ref, "")
        self.result_text = ""

    def submit(self, operation):
        # Parsing a user's development record preserves its draft and cannot
        # bypass the captured kernel owners or grant positive authority.
        record = self._codec.decode(self.draft.encode("utf8"))
        view = (self._view, self._view_generation)
        try:
            attempt = self._service.begin_call(record.original_wire, operation,
                reason_ref="reason:operator-revoke" if operation == "kernel.revoke" else None)
        except SubmissionUncertain as error:
            self._attempt, self._attempt_view = error.attempt, view
            self.status, self.detail = "RECOVERING", "Dispatch uncertain; exact attempt and draft preserved."
            raise
        self._attempt, self._attempt_view = attempt, view
        self.status, self.detail = "ACTIVE", "Request submitted; completion is not established."
        return self._attempt

    def stop(self):
        observation = self._service.request_stop()
        self.status, self.detail = observation["state"], observation["detail"]
        return observation

    def poll(self):
        observation = self._service.poll()
        self.status, self.detail = observation["state"], observation["detail"]
        call = observation.get("call")
        if call is not None and call.get("attempt") == self._attempt:
            response = call.get("response")
            signature = (call["attempt"], call.get("kind"),
                         None if response is None else response.original_response)
            if signature == self._handled:
                return observation
            self._handled = signature
            if self._attempt_view == (self._view, self._view_generation):
                if response is not None:
                    self.result_text = response.original_response.decode("utf8")
                else:
                    self.result_text = json.dumps({k: v for k, v in call.items() if k != "response"}, indent=2)
        return observation
