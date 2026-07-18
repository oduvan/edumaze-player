from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Budgets:
    """Hard limits that guarantee a walk terminates and stays polite.

    v1 enforces ``max_actions`` and ``max_depth``. ``max_wall_clock_s`` and
    ``actions_per_second`` are honored by the real (browser) driver; the
    in-memory driver ignores them (no real clock in tests).
    """

    max_actions: int = 200
    max_depth: int = 25
    max_wall_clock_s: float = 300.0
    actions_per_second: float = 5.0
