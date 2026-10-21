"""Explicit, ephemeral installation diagnostics over existing retained owners."""
from dataclasses import asdict, replace
import hashlib
import json
import time

from ceta.contracts.resource_management import require
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import (OwnedProcessTelemetrySampler, PerformanceDiagnostics,
    PerformanceEnvelope, ResourceTelemetryRecorder)
from ceta.store.journal import SqliteJournal


def _digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(value, separators=(",", ":")).encode("utf8")).hexdigest()


def collect_owned_diagnostics(service, *, expected_generation, envelope,
                              maximum_age_ns=1_000_000_000, sample_interval_ns=100_000_000,
                              cancelled=None, _clock=time.monotonic_ns, _wait=time.sleep):
    """Collect exactly two frames per fixed borrowed process, then discard them.

    This trusted controller operation grants no worker authority. It reads only
    the selected development Journal and retained handles, and never closes or
    terminates those handles. The result describes aggregate installation usage,
    not task attribution, causal explanations or qualified workload performance.
    """
    require(type(envelope) is PerformanceEnvelope, "DIAGNOSTICS_ENVELOPE_REQUIRED")
    envelope = replace(envelope)
    require(type(maximum_age_ns) is int and type(sample_interval_ns) is int
            and 1 <= sample_interval_ns <= 1_000_000_000
            and sample_interval_ns <= maximum_age_ns <= 30_000_000_000,
            "DIAGNOSTICS_SAMPLING_INVALID")
    require((cancelled is None or callable(cancelled)) and callable(_clock) and callable(_wait),
            "DIAGNOSTICS_CALLBACK_INVALID")
    snapshot = service._diagnostics_owner_snapshot(expected_generation)
    last_clock = -1
    def checkpoint():
        nonlocal last_clock
        if cancelled is not None:
            stop = cancelled()
            require(type(stop) is bool, "DIAGNOSTICS_CANCELLATION_INVALID")
            require(not stop, "DIAGNOSTICS_CANCELLED")
        now = _clock()
        require(type(now) is int and 0 <= now <= 2**63 - 1 and now >= last_clock,
                "DIAGNOSTICS_CLOCK_INVALID")
        last_clock = now
        require(service._diagnostics_owner_current(snapshot) is True, "DIAGNOSTICS_OWNER_CHANGED")
        return now

    started = checkpoint()
    require(started + maximum_age_ns + sample_interval_ns <= 2**63 - 1, "DIAGNOSTICS_CLOCK_INVALID")
    deadline = started + maximum_age_ns + sample_interval_ns
    scope = _digest(["ceta.installation.diagnostics.scope.v1", snapshot.installation_scope_id])
    journal = None
    primary = None
    try:
        journal = SqliteJournal(snapshot.profile_root, snapshot.codec, snapshot.scopes,
                                profile=STORE_PROFILE, read_only=True)
        state_before = journal.store_position()
        before = journal.position(snapshot.installation_scope_id)
        environment = _digest(["ceta.installation.diagnostics.environment.v1", snapshot.generation,
                               scope, before.next_sequence, before.head, asdict(state_before)])
        ports = (("service", snapshot.service_process), ("client", snapshot.client_process))
        samplers, recorders = {}, {}
        identities = {}
        for role, port in ports:
            checkpoint()
            identity = port.resource_identity
            identities[role] = identity
            require(port.resource_observation_current(identity) is True, "DIAGNOSTICS_PROCESS_UNAVAILABLE")
            samplers[role] = OwnedProcessTelemetrySampler(port, identity, scope_digest=scope,
                environment_digest=environment,
                workload_digest=_digest(["ceta.installation.runtime.aggregate.v1", snapshot.generation, role, identity.source_digest]),
                source_generation=0, clock=_clock, minimum_interval_ns=sample_interval_ns,
                maximum_age_ns=maximum_age_ns, maximum_probe_window_ns=min(maximum_age_ns, 1_000_000_000))
            recorders[role] = ResourceTelemetryRecorder(maximum_samples=2)
            samplers[role].collect(recorders[role])
        now = checkpoint()
        target = now + sample_interval_ns
        # A stalled/lying monotonic clock cannot create an unbounded wait loop.
        # Each wait is at most 50ms and the iteration count is bounded separately.
        for _ in range((sample_interval_ns + 49_999_999) // 50_000_000 + 2):
            now = checkpoint()
            require(now <= deadline, "DIAGNOSTICS_DEADLINE_EXCEEDED")
            if now >= target:
                break
            _wait(min(target - now, 50_000_000) / 1_000_000_000)
        else:
            raise ContractError("DIAGNOSTICS_CLOCK_NOT_ADVANCING")
        for role, port in ports:
            checkpoint()
            samplers[role].collect(recorders[role])
        now = checkpoint()
        require(now <= deadline, "DIAGNOSTICS_DEADLINE_EXCEEDED")
        after = journal.position(snapshot.installation_scope_id)
        require(after == before, "DIAGNOSTICS_JOURNAL_CHANGED")
        now = checkpoint()
        require(now <= deadline, "DIAGNOSTICS_DEADLINE_EXCEEDED")
        for role, port in ports:
            require(port.resource_identity == identities[role]
                    and port.resource_observation_current(identities[role]) is True,
                    "DIAGNOSTICS_PROCESS_UNAVAILABLE")
        now = checkpoint()
        analyses = {}
        for role, _ in ports:
            samples = recorders[role].recent(now_monotonic_ns=now, maximum_age_ns=maximum_age_ns, scope_digest=scope)
            analyses[role] = asdict(PerformanceDiagnostics().analyze_process_current(samples, envelope,
                now_monotonic_ns=now, maximum_age_ns=maximum_age_ns, scope_digest=scope,
                environment_digest=environment))
        finished = checkpoint()
        require(finished <= deadline and finished - now <= maximum_age_ns, "DIAGNOSTICS_DEADLINE_EXCEEDED")
        require(journal.store_position() == state_before
                and journal.position(snapshot.installation_scope_id) == before, "DIAGNOSTICS_JOURNAL_CHANGED")
        for role, port in ports:
            require(port.resource_identity == identities[role]
                    and port.resource_observation_current(identities[role]) is True,
                    "DIAGNOSTICS_PROCESS_UNAVAILABLE")
        require(journal.store_position() == state_before
                and journal.position(snapshot.installation_scope_id) == before, "DIAGNOSTICS_JOURNAL_CHANGED")
        published = checkpoint()
        require(published <= deadline, "DIAGNOSTICS_DEADLINE_EXCEEDED")
        for role, _ in ports:
            retained = recorders[role].recent(now_monotonic_ns=published, maximum_age_ns=maximum_age_ns, scope_digest=scope)
            require(len(retained) == 2 and all(published - x.process_usage.window_started_monotonic_ns <= maximum_age_ns
                    for x in retained if x.process_usage is not None), "DIAGNOSTICS_MEASUREMENTS_EXPIRED")
        complete = all(x["measurement_state"] == "MEASURED_PROCESS_USAGE" for x in analyses.values())
        return {"profile": "ceta.installation.process-diagnostics.v1",
                "state": "COMPLETE_PROCESS_USAGE" if complete else "UNAVAILABLE_PROCESS_USAGE",
                "generation": snapshot.generation, "scope_digest": scope, "environment_digest": environment,
                "store_position": asdict(state_before),
                "journal_position": {"next_sequence": before.next_sequence, "head": before.head},
                "sample_count_per_process": 2, "observed_monotonic_ns": now,
                "envelope": asdict(envelope), "envelope_status": "CALLER_DECLARED_UNQUALIFIED",
                "task_attribution": "UNAVAILABLE_SHARED_RUNTIME_PROCESSES",
                "latency": "UNOBSERVED", "causal_bottleneck": "NOT_ESTABLISHED",
                "qualification": "NOT_ESTABLISHED",
                "consistency": "SEPARATE_VALIDATED_OBSERVATION_BOUNDARIES_NOT_ATOMIC_LIVE_SNAPSHOT",
                "deadline": "CHECKED_BETWEEN_SYNCHRONOUS_SQLITE_AND_NATIVE_CALLS", "processes": analyses}
    except BaseException as error:
        primary = error
        raise
    finally:
        if journal is not None:
            try:
                journal.close()
            except BaseException as cleanup:
                retained = primary if primary is not None else cleanup
                try:
                    data = BaseException.__dict__["__dict__"].__get__(retained)
                    data["diagnostics_journal_cleanup_error"] = cleanup
                    data["diagnostics_journal_custody"] = journal
                except BaseException:
                    pass
                if primary is None:
                    raise
