"""Shadow mode controller for reasoning integration.

Controls whether societal reasoning assessments are:
- Computed silently (shadow mode, default)
- Attached as advisory context to compilation results
- Bound as evidence to continuity records

The controller never promotes itself to kernel authority. It records
the current mode and enforces mode-transition boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ShadowLevel(str, Enum):
    """Bounded operating levels for the reasoning subsystem."""
    OFF = "OFF"
    SHADOW_SILENT = "SHADOW_SILENT"
    SHADOW_LOGGED = "SHADOW_LOGGED"
    ADVISORY_ATTACHED = "ADVISORY_ATTACHED"


# Transitions that do NOT require owner authorization
_SAFE_TRANSITIONS = frozenset({
    (ShadowLevel.OFF, ShadowLevel.SHADOW_SILENT),
    (ShadowLevel.SHADOW_SILENT, ShadowLevel.OFF),
    (ShadowLevel.SHADOW_SILENT, ShadowLevel.SHADOW_LOGGED),
    (ShadowLevel.SHADOW_LOGGED, ShadowLevel.SHADOW_SILENT),
    (ShadowLevel.SHADOW_LOGGED, ShadowLevel.OFF),
})

# Transitions that require explicit owner authorization
_AUTHORIZED_TRANSITIONS = frozenset({
    (ShadowLevel.OFF, ShadowLevel.SHADOW_LOGGED),
    (ShadowLevel.OFF, ShadowLevel.ADVISORY_ATTACHED),
    (ShadowLevel.SHADOW_SILENT, ShadowLevel.ADVISORY_ATTACHED),
    (ShadowLevel.SHADOW_LOGGED, ShadowLevel.ADVISORY_ATTACHED),
    (ShadowLevel.ADVISORY_ATTACHED, ShadowLevel.SHADOW_LOGGED),
    (ShadowLevel.ADVISORY_ATTACHED, ShadowLevel.SHADOW_SILENT),
    (ShadowLevel.ADVISORY_ATTACHED, ShadowLevel.OFF),
})


@dataclass(frozen=True)
class ModeTransition:
    """Record of a shadow level change."""
    from_level: ShadowLevel
    to_level: ShadowLevel
    authorized: bool
    reason: str


class ShadowModeController:
    """Governs the operating level of the reasoning subsystem.

    Default level is SHADOW_SILENT: assessments are computed but
    not logged or attached to any CETA state. Transitions toward
    ADVISORY_ATTACHED require explicit owner authorization.
    """

    def __init__(self, initial: ShadowLevel = ShadowLevel.SHADOW_SILENT):
        if not isinstance(initial, ShadowLevel):
            raise TypeError(f"Expected ShadowLevel, got {type(initial).__name__}")
        self._level = initial
        self._history: list[ModeTransition] = []

    @property
    def level(self) -> ShadowLevel:
        return self._level

    @property
    def is_active(self) -> bool:
        return self._level != ShadowLevel.OFF

    @property
    def should_log(self) -> bool:
        return self._level in (ShadowLevel.SHADOW_LOGGED, ShadowLevel.ADVISORY_ATTACHED)

    @property
    def should_attach(self) -> bool:
        return self._level == ShadowLevel.ADVISORY_ATTACHED

    @property
    def transition_history(self) -> tuple[ModeTransition, ...]:
        return tuple(self._history)

    def transition(self, target: ShadowLevel, *, authorized: bool = False,
                   reason: str = "") -> ModeTransition:
        """Attempt a mode transition.

        Safe transitions (between OFF/SILENT/LOGGED) proceed without
        authorization. Transitions to or from ADVISORY_ATTACHED require
        authorized=True. Raises PermissionError if authorization is
        needed but not provided.
        """
        if not isinstance(target, ShadowLevel):
            raise TypeError(f"Expected ShadowLevel, got {type(target).__name__}")
        if target == self._level:
            raise ValueError(f"Already at {self._level.value}")

        pair = (self._level, target)
        if pair in _SAFE_TRANSITIONS:
            record = ModeTransition(self._level, target, True, reason or "safe_transition")
        elif pair in _AUTHORIZED_TRANSITIONS:
            if not authorized:
                raise PermissionError(
                    f"Transition {self._level.value} -> {target.value} "
                    f"requires explicit owner authorization"
                )
            record = ModeTransition(self._level, target, True, reason or "authorized_transition")
        else:
            raise ValueError(f"Invalid transition: {self._level.value} -> {target.value}")

        self._level = target
        self._history.append(record)
        return record
