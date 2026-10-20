"""Typed, side-effect-free resource-management contracts.

This module deliberately owns neither reservations nor canonical telemetry
storage.  Callers provide those services through the narrow ports below.
Measured zero is a valid value; unavailable is represented explicitly.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol

from .wire import ContractError


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
MAX_OBSERVATION_AGE_NS = 300_000_000_000


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def _identifier(value: str, code: str = "RESOURCE_IDENTIFIER_INVALID") -> None:
    require(type(value) is str and bool(_IDENTIFIER.fullmatch(value)), code)


def identifier(value: str, code: str = "RESOURCE_IDENTIFIER_INVALID") -> None:
    """Validate an externally supplied resource identity against the shared bound."""
    _identifier(value, code)


def digest(value: str, code: str = "RESOURCE_DIGEST_INVALID") -> None:
    require(type(value) is str and bool(_DIGEST.fullmatch(value)), code)


def _nonnegative(value: int, code: str = "RESOURCE_VALUE_INVALID") -> None:
    require(type(value) is int and 0 <= value <= 2**63 - 1, code)


class ObservationState(str, Enum):
    MEASURED = "MEASURED"
    UNAVAILABLE = "UNAVAILABLE"


class ResourceKind(str, Enum):
    CPU = "CPU"
    MEMORY = "MEMORY"
    STORAGE = "STORAGE"
    ACCELERATOR = "ACCELERATOR"


class PressureLevel(str, Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AdmissionState(str, Enum):
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class QuantityObservation:
    """One observation in a declared unit; unavailable never becomes zero."""
    state: ObservationState
    value: int | None
    observed_monotonic_ns: int
    method: str
    reason: str | None = None

    def __post_init__(self) -> None:
        require(type(self.state) is ObservationState, "RESOURCE_OBSERVATION_STATE_INVALID")
        _nonnegative(self.observed_monotonic_ns, "RESOURCE_OBSERVATION_TIME_INVALID")
        require(type(self.method) is str and 1 <= len(self.method) <= 160,
                "RESOURCE_OBSERVATION_METHOD_INVALID")
        if self.state is ObservationState.MEASURED:
            _nonnegative(self.value, "RESOURCE_MEASUREMENT_INVALID")
            require(self.reason is None, "RESOURCE_MEASUREMENT_REASON_INVALID")
        else:
            require(self.value is None and type(self.reason) is str and 1 <= len(self.reason) <= 240,
                    "RESOURCE_UNAVAILABLE_INVALID")

    @property
    def measured(self) -> bool:
        return self.state is ObservationState.MEASURED


@dataclass(frozen=True, slots=True)
class CapacitySnapshot:
    """Physical, free and safely reservable capacity are intentionally separate."""
    kind: ResourceKind
    total: QuantityObservation
    free: QuantityObservation
    reservable: QuantityObservation
    utilization_milli: QuantityObservation
    sequence: int

    def __post_init__(self) -> None:
        require(type(self.kind) is ResourceKind, "RESOURCE_KIND_INVALID")
        require(all(type(value) is QuantityObservation for value in
                    (self.total, self.free, self.reservable, self.utilization_milli)),
                "RESOURCE_CAPACITY_OBSERVATION_REQUIRED")
        _nonnegative(self.sequence, "RESOURCE_SEQUENCE_INVALID")
        if self.utilization_milli.measured:
            require(self.utilization_milli.value <= 1000, "RESOURCE_UTILIZATION_INVALID")
        if self.total.measured and self.free.measured:
            require(self.free.value <= self.total.value, "RESOURCE_FREE_EXCEEDS_TOTAL")
        if self.free.measured and self.reservable.measured:
            require(self.reservable.value <= self.free.value, "RESOURCE_RESERVABLE_EXCEEDS_FREE")

    def is_recent(self, now_monotonic_ns: int, maximum_age_ns: int = MAX_OBSERVATION_AGE_NS) -> bool:
        _nonnegative(now_monotonic_ns, "RESOURCE_CLOCK_INVALID")
        _nonnegative(maximum_age_ns, "RESOURCE_MAXIMUM_AGE_INVALID")
        # A snapshot is coherent only when every constituent observation is
        # contemporaneous.  Using its newest member would make a stale free or
        # reservation value appear current after an unrelated fresh sample.
        return all(now_monotonic_ns >= value.observed_monotonic_ns
                   and now_monotonic_ns - value.observed_monotonic_ns <= maximum_age_ns
                   for value in (self.total, self.free, self.reservable, self.utilization_milli))


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    profile_id: str
    cpu: CapacitySnapshot
    memory: CapacitySnapshot
    storage: CapacitySnapshot
    accelerators: tuple[CapacitySnapshot, ...]
    isolation_available: QuantityObservation
    measured_monotonic_ns: int
    platform: str

    def __post_init__(self) -> None:
        _identifier(self.profile_id)
        require(all(type(value) is CapacitySnapshot for value in (self.cpu, self.memory, self.storage)),
                "RESOURCE_PROFILE_CAPACITY_REQUIRED")
        require((self.cpu.kind, self.memory.kind, self.storage.kind)
                == (ResourceKind.CPU, ResourceKind.MEMORY, ResourceKind.STORAGE),
                "RESOURCE_PROFILE_CAPACITY_KIND_INVALID")
        require(type(self.accelerators) is tuple and len(self.accelerators) <= 16
                and all(type(value) is CapacitySnapshot and value.kind is ResourceKind.ACCELERATOR
                        for value in self.accelerators),
                "RESOURCE_ACCELERATOR_PROFILE_INVALID")
        require(type(self.isolation_available) is QuantityObservation, "RESOURCE_ISOLATION_OBSERVATION_REQUIRED")
        _nonnegative(self.measured_monotonic_ns, "RESOURCE_PROFILE_TIME_INVALID")
        require(type(self.platform) is str and 1 <= len(self.platform) <= 128, "RESOURCE_PLATFORM_INVALID")


@dataclass(frozen=True, slots=True)
class ResourceVector:
    cpu_milli: int
    memory_bytes: int
    storage_bytes: int
    wall_time_ms: int

    def __post_init__(self) -> None:
        for value in (self.cpu_milli, self.memory_bytes, self.storage_bytes, self.wall_time_ms):
            _nonnegative(value, "RESOURCE_VECTOR_INVALID")

    def fits_within(self, capacity: "ResourceVector") -> bool:
        require(type(capacity) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
        return (self.cpu_milli <= capacity.cpu_milli and self.memory_bytes <= capacity.memory_bytes
                and self.storage_bytes <= capacity.storage_bytes and self.wall_time_ms <= capacity.wall_time_ms)

    def add(self, other: "ResourceVector") -> "ResourceVector":
        require(type(other) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
        return ResourceVector(self.cpu_milli + other.cpu_milli, self.memory_bytes + other.memory_bytes,
                              self.storage_bytes + other.storage_bytes, self.wall_time_ms + other.wall_time_ms)

    def subtract(self, other: "ResourceVector") -> "ResourceVector":
        require(type(other) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
        require(other.fits_within(self), "RESOURCE_VECTOR_UNDERFLOW")
        return ResourceVector(self.cpu_milli - other.cpu_milli, self.memory_bytes - other.memory_bytes,
                              self.storage_bytes - other.storage_bytes, self.wall_time_ms - other.wall_time_ms)


@dataclass(frozen=True, slots=True)
class BudgetEnvelope:
    budget_id: str
    limit: ResourceVector
    control_reserve: ResourceVector
    measured_use: ResourceVector
    reserved_use: ResourceVector
    generation: int

    def __post_init__(self) -> None:
        _identifier(self.budget_id)
        require(all(type(value) is ResourceVector for value in
                    (self.limit, self.control_reserve, self.measured_use, self.reserved_use)),
                "RESOURCE_BUDGET_VECTOR_REQUIRED")
        _nonnegative(self.generation, "RESOURCE_BUDGET_GENERATION_INVALID")
        require(self.control_reserve.fits_within(self.limit), "RESOURCE_CONTROL_RESERVE_INVALID")
        require(self.measured_use.add(self.reserved_use).add(self.control_reserve).fits_within(self.limit),
                "RESOURCE_BUDGET_CONSERVATION_FAILED")

    @property
    def allocatable(self) -> ResourceVector:
        return self.limit.subtract(self.control_reserve).subtract(self.measured_use).subtract(self.reserved_use)


@dataclass(frozen=True, slots=True)
class ReservationRequest:
    request_id: str
    budget_id: str
    expected_generation: int
    requirements: ResourceVector
    observation_sequence: int
    observation_monotonic_ns: int

    def __post_init__(self) -> None:
        _identifier(self.request_id); _identifier(self.budget_id)
        _nonnegative(self.expected_generation, "RESOURCE_BUDGET_GENERATION_INVALID")
        require(type(self.requirements) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
        _nonnegative(self.observation_sequence, "RESOURCE_SEQUENCE_INVALID")
        _nonnegative(self.observation_monotonic_ns, "RESOURCE_OBSERVATION_TIME_INVALID")


@dataclass(frozen=True, slots=True)
class ReservationResult:
    state: AdmissionState
    reservation_ref: str | None
    generation: int | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        require(type(self.state) is AdmissionState and type(self.reason_codes) is tuple
                and len(self.reason_codes) <= 16 and all(type(x) is str and 1 <= len(x) <= 96 for x in self.reason_codes),
                "RESOURCE_RESERVATION_RESULT_INVALID")
        if self.state is AdmissionState.ADMITTED:
            _identifier(self.reservation_ref or "", "RESOURCE_RESERVATION_REFERENCE_INVALID")
            _nonnegative(self.generation, "RESOURCE_BUDGET_GENERATION_INVALID")
        else:
            require(self.reservation_ref is None and self.generation is None and bool(self.reason_codes),
                    "RESOURCE_RESERVATION_DENIAL_INVALID")


class ReservationPort(Protocol):
    """Canonical state owner. This domain package does not implement it."""
    def reserve(self, request: ReservationRequest) -> ReservationResult: ...


class MonotonicClock(Protocol):
    def monotonic_ns(self) -> int: ...


@dataclass(frozen=True, slots=True)
class TelemetrySourceBinding:
    """Declared source epoch/order, not authenticated task or evidence authority.

    The canonical producer must establish these facts. Legacy samples without
    a binding remain useful for historical analysis, not current comparison.
    """
    source_digest: str
    source_generation: int
    sequence: int
    workload_digest: str

    def __post_init__(self) -> None:
        digest(self.source_digest, "RESOURCE_TELEMETRY_SOURCE_DIGEST_INVALID")
        digest(self.workload_digest, "RESOURCE_WORKLOAD_DIGEST_INVALID")
        _nonnegative(self.source_generation, "RESOURCE_TELEMETRY_GENERATION_INVALID")
        _nonnegative(self.sequence, "RESOURCE_TELEMETRY_SEQUENCE_INVALID")


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    sample_id: str
    scope_digest: str
    environment_digest: str
    observed_monotonic_ns: int
    cpu_milli: QuantityObservation
    memory_bytes: QuantityObservation
    storage_bytes: QuantityObservation
    latency_ms: QuantityObservation
    source: TelemetrySourceBinding | None = None

    def __post_init__(self) -> None:
        _identifier(self.sample_id)
        digest(self.scope_digest, "RESOURCE_SCOPE_DIGEST_INVALID")
        digest(self.environment_digest, "RESOURCE_ENVIRONMENT_DIGEST_INVALID")
        _nonnegative(self.observed_monotonic_ns, "RESOURCE_OBSERVATION_TIME_INVALID")
        require(all(type(value) is QuantityObservation for value in
                    (self.cpu_milli, self.memory_bytes, self.storage_bytes, self.latency_ms)),
                "RESOURCE_TELEMETRY_OBSERVATION_REQUIRED")
        require(self.source is None or type(self.source) is TelemetrySourceBinding,
                "RESOURCE_TELEMETRY_SOURCE_BINDING_INVALID")

