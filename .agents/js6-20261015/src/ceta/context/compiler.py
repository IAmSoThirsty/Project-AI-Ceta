"""One injected request compiler; exact previews only, no inference dispatch.

Ports must be bounded and observe the supplied cancellation/deadline control.
Surrounding checks reject late work; they cannot forcibly terminate a callback
which ignores its control. The application must retain that worker's custody.
Actual production owners, semantic evaluation and native/model qualification
are separate obligations. No fallback renderer, tokenizer, state or clock exists.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from threading import Lock
from typing import Callable

from ceta.contracts.read_sets import require_current_preparation
from ceta.contracts.request_compiler import (
    REQUEST_PROFILE, PROFILES, RAW_SOURCE_IDS, MAX_ITEMS, MAX_MODEL_PARTS,
    ClarificationQuestion, CompilationResult, ExactQuotation, Interpretation,
    MeaningField, ModelPart, Omission, PreparationState, PreparedRequest,
    RuntimeBinding, SelectedContext, TaskInput, Tokenization, byte_commitment,
    integer, metadata_commitment, need, raw_bytes, resolve_quotation,
    token_commitment, typed_tuple,
)
from ceta.contracts.temporal import ClockSample, require_deadline_current
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes

MAX_LIVE_PREVIEWS = 64


@dataclass(frozen=True)
class CompilerPorts:
    codec: RecordCodec
    select: Callable
    interpret: Callable
    render: Callable
    tokenize: Callable
    current: Callable
    clock: Callable

    def __post_init__(self):
        need(type(self.codec) is RecordCodec, "COMPILER_CODEC_REQUIRED")
        for port in (self.select, self.interpret, self.render,
                     self.tokenize, self.current, self.clock):
            need(callable(port), "COMPILER_OWNER_UNAVAILABLE")


def _cancel_key(cancelled):
    owner = getattr(cancelled, "__self__", None)
    function = getattr(cancelled, "__func__", None)
    if owner is not None and function is not None:
        return owner, function
    if not callable(cancelled) and callable(getattr(cancelled, "is_set", None)):
        method = cancelled.is_set
        return cancelled, getattr(method, "__func__", method)
    need(callable(cancelled), "COMPILER_CANCELLATION_REQUIRED")
    return cancelled, None


def _cancelled(cancelled):
    check = cancelled if callable(cancelled) else getattr(cancelled, "is_set", None)
    need(callable(check), "COMPILER_CANCELLATION_REQUIRED")
    value = check()
    need(type(value) is bool, "COMPILER_CANCELLATION_VALUE")
    return value


class _WorkControl:
    """The same Stop signal plus trusted expiry, usable as predicate or Event seam."""
    def __init__(self, cancelled, deadline, clock, previous):
        self.cancelled, self.deadline = cancelled, deadline
        self.clock, self.previous = clock, previous

    def __call__(self):
        if _cancelled(self.cancelled):
            return True
        current = self.clock()
        require_deadline_current(self.deadline, self.previous, current)
        self.previous = current
        return False

    def is_set(self):
        return self()


class RequestCompiler:
    def __init__(self, ports):
        need(type(ports) is CompilerPorts, "COMPILER_OWNER_UNAVAILABLE")
        self._ports = ports
        self._active = {}
        self._lock = Lock()

    def _retire_cancelled(self):
        """Release cancelled preview custody without invoking owners under a lock.

        At most MAX_LIVE_PREVIEWS original predicates are sampled. An unavailable
        predicate is not evidence of cancellation. Identity checks protect an
        entry concurrently replaced or revalidated after this bounded snapshot.
        Previously returned immutable values remain readable, never revivable.
        """
        with self._lock:
            retained = tuple(self._active.items())
        for key, registered in retained:
            try:
                cancelled = _cancelled(registered[3])
            except Exception:
                continue
            if cancelled:
                with self._lock:
                    if self._active.get(key) is registered:
                        del self._active[key]

    def _stage(self, expected, previous, cancelled):
        need(not _cancelled(cancelled), "COMPILER_CANCELLED")
        first = self._ports.clock()
        need(type(first) is ClockSample, "COMPILER_CLOCK_UNAVAILABLE")
        require_deadline_current(expected.deadline, previous or first, first)
        current = self._ports.current(expected)
        need(type(current) is PreparationState, "COMPILER_STATE_UNAVAILABLE")
        require_current_preparation(expected.read_set, current.read_set,
                                    expected.required_resource_ids)
        # ReadSet accepts extra unrelated current resources. Do not compare its
        # whole snapshot, or a global journal/telemetry change, as task staleness.
        for field in fields(PreparationState):
            if field.name == "read_set":
                continue
            need(getattr(expected, field.name) == getattr(current, field.name),
                 "COMPILER_BINDING_CHANGED_" + field.name.upper())
        need(not _cancelled(cancelled), "COMPILER_CANCELLED")
        last = self._ports.clock()
        need(type(last) is ClockSample, "COMPILER_CLOCK_UNAVAILABLE")
        require_deadline_current(expected.deadline, first, last)
        return last

    @staticmethod
    def _validate_selection(task, selected, profile, output_tokens):
        need(type(selected) is SelectedContext, "COMPILER_SELECTION_REQUIRED")
        state = selected.state
        for field in ("scope_id", "task_id", "principal_id", "owner_binding",
                      "task_revision", "objective_revision", "objective_generation"):
            need(getattr(state, field) == getattr(task, field), "COMPILER_TASK_BASIS")
        need(state.profile == profile and state.reserved_output_tokens == output_tokens,
             "COMPILER_REQUEST_SELECTION_BINDING")
        require_current_preparation(state.read_set, state.read_set,
                                    state.required_resource_ids)

    @staticmethod
    def _validate_interpretation(task, selected, interpreted):
        need(type(interpreted) is Interpretation
             and interpreted.basis_commitment == selected.basis_commitment(task),
             "COMPILER_INTERPRETATION_BINDING")
        sources = {source.source_id: source for source in selected.sources}
        available = set(sources) | set(RAW_SOURCE_IDS)
        for field in interpreted.fields:
            need(set(field.source_ids) <= available, "COMPILER_MEANING_SOURCE_UNAVAILABLE")
            if field.status == "USER_STATED":
                need(set(field.source_ids) <= set(RAW_SOURCE_IDS),
                     "COMPILER_USER_STATEMENT_SOURCE")
                originals = {"user.original": task.original, "user.latest": task.latest}
                need(field.value is not None
                     and any(field.value == originals[source_id] for source_id in field.source_ids),
                     "COMPILER_USER_STATEMENT_BYTES")
            if field.status == "RECORD_OBSERVED":
                need(all(source_id in sources
                         and sources[source_id].partition == "VERIFIED_RECORD"
                         for source_id in field.source_ids), "COMPILER_RECORD_SOURCE")
                need(field.value is not None
                     and any(field.value == sources[source_id].content for source_id in field.source_ids),
                     "COMPILER_RECORD_OBSERVATION_BYTES")
            if field.name in {"objective", "constraints", "exclusions"}:
                need(field.mandatory, "COMPILER_REQUIRED_MEANING")
        for question in interpreted.questions:
            need(set(question.source_ids) <= available, "COMPILER_QUESTION_SOURCE_UNAVAILABLE")

    @staticmethod
    def _clarification(task, selected, interpreted, text, reason, omissions=()):
        return CompilationResult("CLARIFICATION", task, selection=selected,
            interpretation=interpreted, sources=selected.sources, question=text,
            reason_code=reason, omissions=omissions)

    def compile_loaded_task(self, snapshot_wire, profile, output_tokens, cancelled):
        """Compile one saved native load observation; never persist a user turn."""
        task = TaskInput.from_snapshot(snapshot_wire)
        selected = interpreted = None
        omissions = ()
        payload = tokens = None
        try:
            need(type(profile) is str and profile in PROFILES, "COMPILER_PROFILE")
            integer(output_tokens, 1)
            _cancel_key(cancelled)
            need(not _cancelled(cancelled), "COMPILER_CANCELLED")
            self._retire_cancelled()
            selected = self._ports.select(task, profile, output_tokens, cancelled)
            self._validate_selection(task, selected, profile, output_tokens)
            clock = self._stage(selected.state, None, cancelled)
            control = _WorkControl(cancelled, selected.state.deadline, self._ports.clock, clock)
            interpreted = self._ports.interpret(task, selected, control)
            clock = self._stage(selected.state, control.previous, cancelled)
            control.previous = clock
            self._validate_interpretation(task, selected, interpreted)
            omissions = selected.omissions
            for question in interpreted.questions:
                if question.material and question.dependent_task_id == task.task_id:
                    return self._clarification(task, selected, interpreted, question.text,
                                               "COMPILER_MATERIAL_" + question.reason, omissions)
            if any(item.material for item in omissions):
                return self._clarification(task, selected, interpreted,
                    b"Which task-changing omission should be resolved before this request?",
                    "COMPILER_MATERIAL_OMISSION", omissions)
            objective = next(field for field in interpreted.fields if field.name == "objective")
            need(objective.value is not None and bool(objective.value),
                 "COMPILER_OBJECTIVE_UNAVAILABLE")

            # Mandatory derived fields and quotations require their selected
            # sources to survive token reduction. Optional derived parts occur
            # later in assembly, and are omitted before any optional source.
            required_sources = {source_id for field in interpreted.fields
                                if field.mandatory and field.value is not None
                                for source_id in field.source_ids}
            required_sources.update(quote.source_id for quote in selected.quotes
                                    if quote.mandatory)

            # A tuple here carries a private omission witness beside the public
            # model part. The witness never becomes prompt text or a prompt role.
            assembly = [
                (ModelPart("ORIGINAL_INPUT", task.original, "RAW_USER_INPUT"), True, None, False),
                (ModelPart("LATEST_INPUT", task.latest, "RAW_USER_INPUT"), True, None, False),
            ]
            included_sources = set()
            for source in selected.sources:
                excluded = source.audit_only or (profile == "conversation" and source.coding_only)
                if excluded:
                    need(not source.mandatory, "COMPILER_PROFILE_REQUIRED_SOURCE")
                    omissions += (Omission(source.source_id, source.revision,
                        "AUDIT_ONLY" if source.audit_only else "CODING_ONLY_PROFILE",
                        source.omission_changes_task),)
                    if source.omission_changes_task:
                        return self._clarification(task, selected, interpreted,
                            b"Which task-changing profile omission should be resolved?",
                            "COMPILER_PROFILE_OMISSION_CHANGES_TASK", omissions)
                    continue
                included_sources.add(source.source_id)
                assembly.append((ModelPart(source.partition, source.content, "SOURCE_SELECTED"),
                    source.mandatory or source.source_id in required_sources,
                    Omission(source.source_id, source.revision, "TOKEN_CAPACITY",
                        source.omission_changes_task),
                    source.omission_changes_task))
            for quote in selected.quotes:
                # Reject a bounded assembly conflict before allocating repeated
                # large quote slices. Raw selected sources and quote requests
                # remain in the immutable result; no token estimate is claimed.
                selected_source = next((source for source in selected.sources
                                        if source.source_id == quote.source_id), None)
                available = (selected_source is not None
                             and selected_source.revision == quote.revision
                             and quote.end <= len(selected_source.content)
                             and quote.source_id in included_sources)
                # Unavailable ranges are not allocated input. Resolve their
                # status before capacity accounting, without making a slice.
                resolved = None
                if available:
                    if sum(len(row[0].content) for row in assembly) + quote.end - quote.start > 8 * 1024 * 1024:
                        return CompilationResult("OVERFLOW", task, selection=selected,
                            interpretation=interpreted, sources=selected.sources,
                            omissions=omissions, reason_code="COMPILER_ASSEMBLY_BYTE_BOUND")
                    resolved = resolve_quotation(selected.sources, quote)
                if type(resolved) is not ExactQuotation or quote.source_id not in included_sources:
                    if quote.mandatory:
                        return self._clarification(task, selected, interpreted,
                            b"Which original record should supply the requested exact quotation?",
                            "COMPILER_QUOTATION_UNRESOLVED", omissions)
                    omissions += (Omission(quote.source_id, quote.revision, "QUOTE_UNRESOLVED"),)
                    continue
                assembly.append((ModelPart("QUOTATION", resolved.content, "SOURCE_SELECTED"),
                    quote.mandatory, Omission(quote.source_id, quote.revision, "QUOTE_TOKEN_CAPACITY"),
                    False))
            for field in interpreted.fields:
                if field.value is None:
                    continue
                if not set(field.source_ids) <= included_sources | set(RAW_SOURCE_IDS):
                    need(not field.mandatory, "COMPILER_PROFILE_REQUIRED_MEANING")
                    omissions += (Omission("interpretation." + field.name,
                        interpreted.basis_commitment, "PROFILE_SOURCE_EXCLUDED"),)
                    continue
                public = (field.name + " [" + field.status + "]\n").encode("ascii") + field.value
                assembly.append((ModelPart("MODEL_PROPOSAL", public, field.status),
                    field.mandatory, Omission("interpretation." + field.name,
                        interpreted.basis_commitment, "INTERPRETATION_TOKEN_CAPACITY"), False))

            need(len(assembly) <= MAX_MODEL_PARTS, "COMPILER_ASSEMBLY_SIZE")
            if sum(len(row[0].content) for row in assembly) > 8 * 1024 * 1024:
                return CompilationResult("OVERFLOW", task, selection=selected,
                    interpretation=interpreted, sources=selected.sources,
                    omissions=omissions, reason_code="COMPILER_ASSEMBLY_BYTE_BOUND")
            while True:
                parts = tuple(row[0] for row in assembly)
                clock = self._stage(selected.state, control.previous, cancelled)
                control.previous = clock
                payload = self._ports.render(selected.state.runtime, parts, control)
                raw_bytes(payload)
                clock = self._stage(selected.state, control.previous, cancelled)
                control.previous = clock
                tokens = self._ports.tokenize(selected.state.runtime, payload, control)
                need(type(tokens) is Tokenization
                     and tokens.runtime == selected.state.runtime
                     and tokens.payload_commitment == byte_commitment(payload),
                     "COMPILER_TOKENIZATION_BINDING")
                need(tokens.exact and tokens.includes_special_tokens,
                     "COMPILER_EXACT_TOKENIZER_UNAVAILABLE")
                clock = self._stage(selected.state, control.previous, cancelled)
                control.previous = clock
                total = len(tokens.token_ids) + output_tokens
                if total <= selected.state.runtime.context_tokens:
                    break
                optional = next((index for index in range(len(assembly)-1, -1, -1)
                                 if not assembly[index][1]), None)
                if optional is None:
                    return CompilationResult("OVERFLOW", task, selection=selected,
                        interpretation=interpreted, sources=selected.sources,
                        rendered_payload=payload, input_tokens=len(tokens.token_ids),
                        omissions=omissions, reason_code="COMPILER_MANDATORY_CONTEXT_OVERFLOW")
                row = assembly[optional]
                if row[3]:
                    return self._clarification(task, selected, interpreted,
                        b"Which optional material may be omitted without changing this task?",
                        "COMPILER_TASK_CHANGING_TOKEN_OMISSION", omissions + (row[2],))
                omissions += (row[2],)
                del assembly[optional]
                # Render/count again; per-part estimates never substitute for
                # actual full-template and special-token accounting.

            envelope = self._envelope(task, selected, interpreted, payload, tokens, omissions)
            binding = self._binding(task, selected, interpreted, envelope, parts,
                                    payload, tokens, omissions, clock)
            prepared = PreparedRequest(task, selected, interpreted, envelope, parts,
                                       payload, tokens, omissions, clock, binding)
            # The public value must survive the same owner/cancel/time checks
            # before becoming a preview; registration is not effect authority.
            self._retire_cancelled()
            clock = self._stage(selected.state, clock, cancelled)
            with self._lock:
                need(selected.state.request_id not in self._active, "COMPILER_REQUEST_ID_REUSED")
                need(len(self._active) < MAX_LIVE_PREVIEWS, "COMPILER_PREVIEW_CAPACITY")
                self._active[selected.state.request_id] = (prepared, _cancel_key(cancelled),
                                                           clock, cancelled)
            return CompilationResult("PREVIEW", task, selection=selected,
                interpretation=interpreted, prepared=prepared, sources=selected.sources,
                rendered_payload=payload, input_tokens=len(tokens.token_ids), omissions=omissions,
                reason_code="UNACCEPTED_REQUEST_PREVIEW")
        except Exception as error:
            owner_code = error.code if isinstance(error, ContractError) else None
            code = (owner_code if type(owner_code) is str and 1 <= len(owner_code) <= 160
                    and owner_code[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in owner_code)
                    else "COMPILER_OWNER_FAILURE")
            return CompilationResult("DENIED", task,
                selection=selected if type(selected) is SelectedContext else None,
                interpretation=interpreted if type(interpreted) is Interpretation else None,
                sources=selected.sources if type(selected) is SelectedContext else (),
                omissions=omissions, reason_code=code)

    def _envelope(self, task, selected, interpreted, payload, tokens, omissions):
        state = selected.state
        value = {
            "record_type": "ContextEnvelope", "schema_version": "1",
            "record_id": state.request_id, "scope_id": state.scope_id,
            "causation_ref": task.task_id, "task_id": task.task_id,
            "objective_revision": task.objective_revision, "principal_id": state.principal_id,
            "companion_id": state.companion_id,
            "model_configuration_id": state.runtime.model_configuration_id,
            "policy_refs": list(state.policy_refs), "authority_refs": list(state.authority_refs),
            "snapshot_commitment": state.read_set.commitment(),
            "read_set": [{"resource_id": item.resource_id, "revision": item.revision,
                          "access": "READ", "scope_id": state.scope_id}
                         for item in sorted(state.read_set.resources, key=lambda row: row.resource_id)],
            "observation_refs": list(state.observation_refs), "memory_refs": list(state.memory_refs),
            # The exact question bytes remain in the wrapper. ASCII hex in the
            # closed wire field preserves non-NFC questions instead of normalizing.
            "open_questions": ["utf8-hex:" + question.text.hex()
                               for question in interpreted.questions],
            "contradiction_refs": list(state.contradiction_refs),
            "omissions": [item.source_id + ":" + item.reason_code for item in omissions],
            "template_commitment": state.runtime.template_commitment,
            "tokenizer_commitment": state.runtime.tokenizer_commitment,
            "payload_commitment": byte_commitment(payload), "input_tokens": len(tokens.token_ids),
            "reserved_output_tokens": state.reserved_output_tokens,
            "expires_at": state.expires_at,
            "revalidation_triggers": ["TASK_CELL", "OBJECTIVE", "SOURCES", "RELEVANT_READ_SET",
                "MODEL", "RUNTIME_WORKER", "TEMPLATE", "TOKENIZER", "POLICY", "AUTHORITY_FENCE",
                "RESERVATION", "DEADLINE_CLOCK_EPOCH", "SHARED_CANCELLATION"],
        }
        return self._ports.codec.decode(canonical_bytes(value))

    @staticmethod
    def _binding(task, selected, interpreted, envelope, parts, payload, tokens, omissions, clock):
        value = {
            "profile": REQUEST_PROFILE, "version": "1", "status": "UNACCEPTED_PREVIEW",
            "snapshot": byte_commitment(task.snapshot_wire),
            "original": byte_commitment(task.original), "latest": byte_commitment(task.latest),
            "task_revision": task.task_revision, "objective_revision": task.objective_revision,
            "selection": selected.basis_commitment(task),
            "interpretation": metadata_commitment(interpreted),
            "context": envelope.commitment, "payload": byte_commitment(payload),
            "parts": metadata_commitment(tuple((part.partition, byte_commitment(part.content),
                                                 part.status) for part in parts)),
            "tokens": token_commitment(tokens.token_ids), "input_tokens": len(tokens.token_ids),
            "output_tokens": selected.state.reserved_output_tokens,
            "omissions": metadata_commitment(omissions),
            "clock": metadata_commitment(clock),
        }
        return canonical_bytes(value)

    def revalidate(self, prepared, cancelled):
        """Recheck an existing preview without renewing or dispatching it."""
        need(type(prepared) is PreparedRequest, "COMPILER_PREVIEW_REQUIRED")
        key = prepared.selection.state.request_id
        with self._lock:
            registered = self._active.get(key)
        need(registered is not None and registered[0] is prepared,
             "COMPILER_PREVIEW_NOT_OWNED")
        received = _cancel_key(cancelled)
        need(all(left is right for left, right in zip(registered[1], received)),
             "COMPILER_CANCELLATION_REPLACED")
        clock = self._stage(prepared.selection.state, registered[2], cancelled)
        need(self._binding(prepared.task, prepared.selection, prepared.interpretation,
                           prepared.context, prepared.parts, prepared.payload,
                           prepared.tokenization, prepared.omissions, prepared.prepared_clock)
             == prepared.binding_wire, "COMPILER_PREVIEW_SUBSTITUTION")
        clock = self._stage(prepared.selection.state, clock, cancelled)
        need(not _cancelled(cancelled), "COMPILER_CANCELLED")
        with self._lock:
            need(self._active.get(key) is registered, "COMPILER_PREVIEW_REPLACED")
            self._active[key] = (prepared, registered[1], clock, registered[3])
        return prepared

    def retire(self, prepared):
        """Forget compiler custody; never accept, renew or consume authority."""
        need(type(prepared) is PreparedRequest, "COMPILER_PREVIEW_REQUIRED")
        with self._lock:
            key = prepared.selection.state.request_id
            registered = self._active.get(key)
            need(registered is not None and registered[0] is prepared,
                 "COMPILER_PREVIEW_NOT_OWNED")
            del self._active[key]
