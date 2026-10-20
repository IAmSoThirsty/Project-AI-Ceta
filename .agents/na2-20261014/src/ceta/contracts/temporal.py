"""Exact temporal value contracts for a future authenticated time provider.

All samples and previous samples must originate from that trusted owner, never
from worker requests. This module reads no clock and maintains no epochs.
Passing a predicate establishes only freshness under its injected assumptions.
"""
from dataclasses import dataclass
from datetime import date
import re

from .wire import ContractError, MIN_INTEGER, MAX_INTEGER

NS_PER_SECOND = 1_000_000_000
_EPOCH_ORDINAL = date(1970, 1, 1).toordinal()
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_TIME = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])"
    r"(?:\.([0-9]{1,9}))?(Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def _integer(value: int, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_INTEGER:
        raise ContractError("INVALID_TEMPORAL_INTEGER")
    return value


def utc_nanoseconds(text: str) -> int:
    """Known-offset date-time to signed 64-bit Unix ns, without float rounding."""
    match = _TIME.fullmatch(text) if type(text) is str and len(text) <= 64 else None
    if match is None:
        raise ContractError("INVALID_DATE_TIME")
    year, month, day, hour, minute, second, fraction, offset = match.groups()
    if offset == "-00:00":
        raise ContractError("UNKNOWN_UTC_OFFSET")
    try:
        days = date(int(year), int(month), int(day)).toordinal() - _EPOCH_ORDINAL
    except ValueError as exc:
        raise ContractError("INVALID_DATE_TIME") from exc
    seconds = days * 86400 + int(hour) * 3600 + int(minute) * 60 + int(second)
    if offset != "Z":
        shift = int(offset[1:3]) * 3600 + int(offset[4:6]) * 60
        seconds -= shift if offset[0] == "+" else -shift
    return _integer(seconds * NS_PER_SECOND + int((fraction or "0").ljust(9, "0")), MIN_INTEGER)


@dataclass(frozen=True)
class ClockSample:
    boot_id: str
    durable_epoch: int
    resume_generation: int
    monotonic_ns: int
    wall_time_ns: int
    uncertainty_ns: int
    wall_trusted: bool

    def __post_init__(self) -> None:
        if type(self.boot_id) is not str or not _IDENTIFIER.fullmatch(self.boot_id):
            raise ContractError("INVALID_BOOT_ID")
        for value in (self.durable_epoch, self.resume_generation, self.monotonic_ns, self.uncertainty_ns):
            _integer(value)
        _integer(self.wall_time_ns, MIN_INTEGER)
        _integer(self.wall_time_ns - self.uncertainty_ns, MIN_INTEGER)
        _integer(self.wall_time_ns + self.uncertainty_ns, MIN_INTEGER)
        if type(self.wall_trusted) is not bool:
            raise ContractError("INVALID_TIME_TRUST_FLAG")

    @property
    def earliest_wall_ns(self) -> int:
        return self.wall_time_ns - self.uncertainty_ns

    @property
    def latest_wall_ns(self) -> int:
        return self.wall_time_ns + self.uncertainty_ns


@dataclass(frozen=True)
class Deadline:
    boot_id: str
    durable_epoch: int
    resume_generation: int
    issued_monotonic_ns: int
    expires_monotonic_ns: int
    issued_earliest_wall_ns: int
    expires_wall_ns: int

    def __post_init__(self) -> None:
        if type(self.boot_id) is not str or not _IDENTIFIER.fullmatch(self.boot_id):
            raise ContractError("INVALID_BOOT_ID")
        for value in (self.durable_epoch, self.resume_generation, self.issued_monotonic_ns,
                      self.expires_monotonic_ns):
            _integer(value)
        _integer(self.issued_earliest_wall_ns, MIN_INTEGER)
        _integer(self.expires_wall_ns, MIN_INTEGER)
        if (self.expires_monotonic_ns <= self.issued_monotonic_ns
                or self.expires_wall_ns <= self.issued_earliest_wall_ns):
            raise ContractError("INVALID_DEADLINE_INTERVAL")


def require_clock_progress(previous: ClockSample, current: ClockSample) -> None:
    if type(previous) is not ClockSample or type(current) is not ClockSample:
        raise ContractError("CLOCK_SAMPLE_REQUIRED")
    if not previous.wall_trusted or not current.wall_trusted:
        raise ContractError("TRUSTED_TIME_UNAVAILABLE")
    if previous.boot_id != current.boot_id:
        raise ContractError("BOOT_CHANGED")
    if previous.durable_epoch != current.durable_epoch:
        raise ContractError("TIME_EPOCH_CHANGED")
    if previous.resume_generation != current.resume_generation:
        raise ContractError("RESUME_GENERATION_CHANGED")
    if current.monotonic_ns < previous.monotonic_ns:
        raise ContractError("MONOTONIC_ROLLBACK")
    if current.latest_wall_ns < previous.earliest_wall_ns:
        raise ContractError("WALL_CLOCK_ROLLBACK")


def issue_deadline(expires_at: str, maximum_lifetime_ns: int,
                   previous: ClockSample, current: ClockSample) -> Deadline:
    require_clock_progress(previous, current)
    _integer(maximum_lifetime_ns, 1)
    wall_expiry = utc_nanoseconds(expires_at)
    # Using the latest possible wall instant conservatively shortens the lease.
    lifetime = min(maximum_lifetime_ns, wall_expiry - current.latest_wall_ns)
    if lifetime <= 0:
        raise ContractError("DEADLINE_EXPIRED_OR_UNCERTAIN")
    monotonic_expiry = _integer(current.monotonic_ns + lifetime)
    bounded_wall_expiry = _integer(current.latest_wall_ns + lifetime, MIN_INTEGER)
    return Deadline(current.boot_id, current.durable_epoch, current.resume_generation,
                    current.monotonic_ns, monotonic_expiry, current.earliest_wall_ns,
                    bounded_wall_expiry)


def require_deadline_current(deadline: Deadline, previous: ClockSample, current: ClockSample) -> None:
    if type(deadline) is not Deadline:
        raise ContractError("DEADLINE_REQUIRED")
    require_clock_progress(previous, current)
    if current.boot_id != deadline.boot_id:
        raise ContractError("BOOT_CHANGED")
    if current.durable_epoch != deadline.durable_epoch:
        raise ContractError("TIME_EPOCH_CHANGED")
    if current.resume_generation != deadline.resume_generation:
        raise ContractError("RESUME_GENERATION_CHANGED")
    if current.monotonic_ns < deadline.issued_monotonic_ns:
        raise ContractError("MONOTONIC_ROLLBACK")
    if current.latest_wall_ns < deadline.issued_earliest_wall_ns:
        raise ContractError("WALL_CLOCK_ROLLBACK")
    if (current.monotonic_ns >= deadline.expires_monotonic_ns
            or current.latest_wall_ns >= deadline.expires_wall_ns):
        raise ContractError("DEADLINE_EXPIRED_OR_UNCERTAIN")
