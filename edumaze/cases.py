"""Breakage cases — the script's output.

Each case is a reproducible failure: which guarantee broke, on what element, in
what configuration, and the steps to get there. The ``signature`` groups cases
that fail for the same reason so triage can dismiss (or fix) a whole group at
once instead of analysing 50 near-duplicates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

# check kinds
SEE = "see"    # visibility invariant
DO = "do"      # interactability invariant
SIGNAL = "signal"  # generic: dead link, error, slow load


@dataclass
class BreakageCase:
    state: str
    kind: str                       # SEE | DO | SIGNAL
    target: str                     # element label / locator
    detail: str                     # human description of the failure
    config: Dict[str, Any] = field(default_factory=dict)   # viewport, input, ...
    steps: List[Dict[str, str]] = field(default_factory=list)  # replay from entry
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def signature(self) -> str:
        cfg = ",".join(f"{k}={v}" for k, v in sorted(self.config.items()))
        return f"{self.state}|{self.kind}|{self.target}|{cfg}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["signature"] = self.signature
        return d


@dataclass
class Report:
    site_id: str
    seed: int
    cases: List[BreakageCase] = field(default_factory=list)
    states_checked: List[str] = field(default_factory=list)
    configs_run: int = 0

    def to_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "seed": self.seed,
            "configs_run": self.configs_run,
            "states_checked": self.states_checked,
            "case_count": len(self.cases),
            "unique_signatures": len({c.signature for c in self.cases}),
            "cases": [c.to_dict() for c in self.cases],
        }

    @property
    def ok(self) -> bool:
        return not self.cases
