from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    oracle: str                      # "L1" | "L2"
    summary: str
    node: Optional[str] = None
    severity_hint: str = "med"       # high | med | low
    #: Steps from entry that reproduce this: [{"node","action"}, ...]
    path: List[Dict[str, str]] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    site_id: str
    seed: int
    mode: str
    findings: List[Finding] = field(default_factory=list)
    actions_taken: int = 0
    nodes_visited: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def ok(self) -> bool:
        return not self.findings
