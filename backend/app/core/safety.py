"""Runtime AI safety state (emergency kill switch).

In-process mutable state; a fresh boot always returns to the safe, fully
enabled default. The execution layer consults `execution_allowed()` before any
mutating write, so pausing execution blocks every Apply* path at the source.
"""
from dataclasses import dataclass, asdict


@dataclass
class SafetyState:
    execution_enabled: bool = True
    read_only: bool = False


_state = SafetyState()


def execution_allowed() -> bool:
    return _state.execution_enabled and not _state.read_only


def get_safety() -> dict:
    return {**asdict(_state), "execution_allowed": execution_allowed()}


def set_safety(*, execution_enabled: bool, read_only: bool) -> dict:
    _state.execution_enabled = execution_enabled
    _state.read_only = read_only
    return get_safety()
