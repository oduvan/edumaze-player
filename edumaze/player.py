"""The Player — imports a maze and walks it, driver-agnostic.

Walk model: coverage-guided by default. At each node it takes an unvisited safe
edge; when a node has none, it navigates (via shortest declared path) toward the
nearest node that still does. It stops when every allowed edge is covered or the
action budget runs out. ``walk="random"`` is pure chaos: any edge, revisits
allowed, until the budget.

Determinism: (maze, seed, walk-mode) fully determines the sequence, so every
finding replays by re-running to its action index.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional, Type

from . import matcher, oracles, policy
from .materialize import materialize
from .node import BACK, SUBMIT, Node, Option
from .page import ElementNotFound, Page
from .report import Finding, Report
from .site import Site
from .strategy import Strategy


class Player:
    def __init__(self, site: Site, page: Page, seed: int = 0,
                 mode: str = policy.EXPLORE, walk: str = "coverage",
                 baseline: Optional[dict] = None) -> None:
        self.site = site
        self.page = page
        self.seed = seed
        self.mode = mode              # safety: explore | chaos
        self.walk = walk              # strategy: coverage | random
        self.baseline = baseline
        self.nodes: List[Type[Node]] = site.nodes()
        self.strategy = Strategy(seed, mode=("random" if walk == "random" else "coverage"))
        self._log: List[dict] = []
        self._report = Report(site_id=site.site_id, seed=seed, mode=f"{mode}/{walk}")

    # -- public ------------------------------------------------------------
    def run(self) -> Report:
        page = self.page
        self._enter(page)
        budget = self.site.budgets.max_actions
        restarts = 0
        max_restarts = 4 * len(self.nodes) + 5

        while self._report.actions_taken < budget:
            match = matcher.resolve(page, self.nodes)

            if match.ambiguous:
                self._finding(Finding(
                    oracle="L1", severity_hint="med",
                    summary=f"ambiguous state at {page.url}: "
                            f"{', '.join(match.candidates)} all match"))
                break
            if match.node is None:
                self._finding(Finding(
                    oracle="L1", severity_hint="high",
                    summary=f"undocumented state at {page.url} "
                            f"(no declared node matches)"))
                break

            node_cls = match.node
            inst = node_cls()
            self._visit(node_cls.__name__)
            self._run_l1(inst, page, node_cls.__name__)

            allowed = self._allowed_options(node_cls)
            choice = self.strategy.choose(node_cls.__name__, allowed)

            if choice is None:
                hop = self._hop_toward_frontier(node_cls)
                if hop is not None:
                    choice = hop  # route a visited edge toward unexplored ground
                elif self._frontier_nonempty():
                    # dead-end (no way out from here), but edges remain elsewhere:
                    # re-enter from the top to escape it.
                    if restarts >= max_restarts:
                        break
                    restarts += 1
                    self._enter(page)
                    continue
                else:
                    break  # every allowed edge covered

            self._take(choice, node_cls.__name__, page)

        self._run_l2()
        return self._report

    # -- walk mechanics ----------------------------------------------------
    def _take(self, option: Option, from_node: str, page: Page) -> None:
        self._log.append({"node": from_node, "action": option.label})
        try:
            self._execute(option, page)
        except (ElementNotFound, Exception) as exc:  # noqa: BLE001
            self._finding(Finding(
                oracle="L1", node=from_node, severity_hint="high",
                summary=f"option '{option.label}' on {from_node} not actionable: "
                        f"{type(exc).__name__}: {exc}"))
        self._report.actions_taken += 1

    def _execute(self, option: Option, page: Page) -> None:
        if option.kind == BACK:
            page.back()
            return
        if option.kind == SUBMIT:
            for field_label, semantic in option.fields.items():
                value = self.site.seed_data.get(semantic, semantic)
                page.by_role("textbox", name=field_label).fill(value)
            assert option.locator is not None
            option.locator.resolve(page).click()
            return
        assert option.locator is not None
        option.locator.resolve(page).click()

    def _hop_toward_frontier(self, node_cls: Type[Node]) -> Optional[Option]:
        """First edge on the shortest declared path to a node that still has an
        unvisited allowed edge. None if no such node is reachable."""
        by_name = {n.__name__: n for n in self.nodes}
        frontier = {name for name, nc in by_name.items()
                    if self._has_unvisited(nc)}
        if not frontier:
            return None
        queue: deque = deque([(node_cls, None)])
        seen = {node_cls.__name__}
        while queue:
            cur, first_hop = queue.popleft()
            for opt in self._allowed_options(cur):
                if opt.to is None:
                    continue
                hop = first_hop or opt
                if opt.to.__name__ in frontier:
                    return hop
                if opt.to.__name__ not in seen:
                    seen.add(opt.to.__name__)
                    queue.append((opt.to, hop))
        return None

    # -- helpers -----------------------------------------------------------
    def _allowed_options(self, node_cls: Type[Node]) -> List[Option]:
        return [o for o in node_cls().options()
                if policy.allowed(o, self.site, self.mode)[0]]

    def _has_unvisited(self, node_cls: Type[Node]) -> bool:
        name = node_cls.__name__
        return any((name, o.label) not in self.strategy.visited
                   for o in self._allowed_options(node_cls))

    def _frontier_nonempty(self) -> bool:
        return any(self._has_unvisited(nc) for nc in self.nodes)

    def _enter(self, page: Page) -> None:
        role = self.site.roles[0] if self.site.roles else None
        if role and role.login:
            role.login(page)
            if role.logged_in_when:
                r, n = role.logged_in_when
                if not page.by_role(r, name=n).visible():
                    self._finding(Finding(
                        oracle="L1", severity_hint="high",
                        summary=f"login as {role.name} failed "
                                f"({r} '{n}' not visible)"))
        else:
            page.goto(self.site.base_url or "/")

    def _run_l1(self, inst: Node, page: Page, node_name: str) -> None:
        for f in oracles.technical(page, node_name):
            self._finding(f)
        af = oracles.acceptance(inst, page)
        if af is not None:
            self._finding(af)

    def _run_l2(self) -> None:
        if self.baseline is None:
            return
        current = materialize(self.site)
        for f in oracles.differential(self.site, self.baseline, current):
            self._report.findings.append(f)  # L2 findings are structural, no path

    def _visit(self, name: str) -> None:
        if name not in self._report.nodes_visited:
            self._report.nodes_visited.append(name)

    def _finding(self, finding: Finding) -> None:
        if not finding.path:
            finding.path = list(self._log)
        self._report.findings.append(finding)
