"""The Site class — the per-site 'manifest', but as code.

Everything a universal engine can't infer lives here: where the app is, who logs
in, what's off-limits, what's volatile. The crawl skill emits one ``Site``
subclass per app alongside its nodes.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Type

from .budgets import Budgets
from .node import Node
from .role import Role


class Site:
    base_url: str = ""
    #: Hosts the walker may visit. Leaving them is a hard stop.
    domain_allowlist: List[str] = []
    #: Start node.
    entry: Optional[Type[Node]] = None
    roles: List[Role] = []
    #: Selectors/params excluded from state identity and the L2 diff.
    volatile: List[str] = []
    #: Label/target glob patterns that must never be traversed.
    denylist: List[str] = []
    budgets: Budgets = Budgets()
    #: Optional {"method","url"} that resets app state; enables chaos mode.
    reset_hook: Optional[dict] = None
    #: Field-input values keyed by semantic (see Option.fields).
    seed_data: Dict[str, str] = {}
    #: Nodes not reachable from ``entry`` that should still be modeled.
    extra_nodes: List[Type[Node]] = []

    @property
    def site_id(self) -> str:
        return getattr(self, "id", type(self).__name__)

    def nodes(self) -> List[Type[Node]]:
        """All declared nodes: BFS from ``entry`` through option targets,
        plus ``extra_nodes``. Order is stable (discovery order)."""
        seen: Dict[str, Type[Node]] = {}
        queue: deque[Type[Node]] = deque()

        def add(nc: Optional[Type[Node]]) -> None:
            if nc is not None and nc.__name__ not in seen:
                seen[nc.__name__] = nc
                queue.append(nc)

        if self.entry is not None:
            add(self.entry)
        for nc in self.extra_nodes:
            add(nc)

        while queue:
            nc = queue.popleft()
            for opt in nc().options():
                add(opt.to)
        return list(seen.values())
