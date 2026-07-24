"""The stress engine — the cheap, deterministic core.

For every reachable state, under every viewport, it checks the two guarantees
(See / Do) and generic signals, exercises toggles, and fuzzes form submits. It
reaches each state by replaying a canonical path from the entry, and re-enters to
reset between mutating variations. Output: a de-duplicated list of breakage cases.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Type

from . import checks
from .cases import DO, BreakageCase, Report
from .checks import invalid_values, valid_value
from .model import Element, Site, State, Viewport


class Engine:
    def __init__(self, site: Site, page, seed: int = 0, mode: str = "explore",
                 suppressions: Optional[Set[str]] = None,
                 settle_timeout_ms: int = 6000, settle_interval_ms: int = 250) -> None:
        self.site = site
        self.page = page
        self.seed = seed
        self.mode = mode
        self.suppressions = suppressions or set()
        self.settle_timeout_ms = settle_timeout_ms
        self.settle_interval_ms = settle_interval_ms
        self.states: List[Type[State]] = site.states()
        self.paths: Dict[str, List[Element]] = self._plan_paths()
        self._report = Report(site_id=site.site_id, seed=seed)
        self._seen_sigs: Set[str] = set()
        self._actions = 0

    # -- public ------------------------------------------------------------
    def run(self) -> Report:
        for vp in self.site.viewports:
            self.page.set_viewport(vp.width, vp.height)
            self._report.configs_run += 1
            for state_cls in self.states:
                if self._out_of_budget():
                    self._report.actions_taken = self._actions
                    return self._report
                self._check_state(state_cls, vp)
        self._report.actions_taken = self._actions
        return self._report

    # -- per-state checks --------------------------------------------------
    def _check_state(self, state_cls: Type[State], vp: Viewport) -> None:
        if state_cls.__name__ not in self.paths:
            return  # unreachable in this mode (e.g. only via a destructive edge)
        config = {"viewport": vp.name}
        steps = self._steps_to(state_cls)

        if not self._go_to(state_cls):
            self._add(BreakageCase(state_cls.__name__, DO, "<navigation>",
                      "could not reach this state by its declared path",
                      dict(config), list(steps)))
            return

        self._note_checked(state_cls.__name__)
        state = state_cls()
        for case in checks.see_check(state, self.page, config, steps):
            self._add(case)
        for case in checks.interact_check(state, self.page, config, steps):
            self._add(case)
        for case in checks.signal_check(state.name, self.page, config, steps,
                                        self.site.slow_load_ms):
            self._add(case)

        for el in state.elements():
            if el.is_destructive() and self.mode != "chaos":
                continue
            if el.toggle is not None:
                self._check_toggle(state_cls, el, vp)
            if el.submit is not None:
                self._fuzz_submit(state_cls, el, vp)

    def _check_toggle(self, state_cls: Type[State], el: Element, vp: Viewport) -> None:
        if self._out_of_budget() or not self._go_to(state_cls):
            return
        config = {"viewport": vp.name, "action": f"open:{el.label}"}
        steps = self._steps_to(state_cls) + [{"action": f"open {el.label}"}]
        try:
            el.find.resolve(self.page).click()
        except Exception:
            self._add(BreakageCase(state_cls.__name__, DO, el.label,
                      "toggle could not be clicked", config, steps))
            return
        self.page.wait(self.settle_interval_ms * 2)
        for loc in el.toggle.reveals:
            if not checks._safe(loc.resolve(self.page).visible):
                self._add(BreakageCase(state_cls.__name__, DO, el.label,
                          f"toggle did not reveal {loc.label()}", config, steps))
        for loc in el.toggle.hides:
            if checks._safe(loc.resolve(self.page).visible):
                self._add(BreakageCase(state_cls.__name__, DO, el.label,
                          f"toggle did not hide {loc.label()}", config, steps))

    def _fuzz_submit(self, state_cls: Type[State], el: Element, vp: Viewport) -> None:
        sub = el.submit
        base_steps = self._steps_to(state_cls)

        # valid submit should succeed (reach on_valid)
        if sub.on_valid is not None and not self._out_of_budget():
            if self._go_to(state_cls):
                self._fill_valid(sub)
                self._click(el)
                self._settle_any()
                if self._identify() is not sub.on_valid:
                    self._add(BreakageCase(state_cls.__name__, DO, el.label,
                              f"valid submit did not reach {sub.on_valid.__name__}",
                              {"viewport": vp.name, "input": "valid"},
                              base_steps + [{"action": f"submit {el.label}"}]))

        # invalid inputs should be rejected gracefully
        for f in sub.fields:
            for iv in invalid_values(f):
                if self._out_of_budget() or not self._go_to(state_cls):
                    return
                self._fill_valid(sub)
                try:
                    f.find.resolve(self.page).fill(iv["value"])
                except Exception:
                    continue
                self._click(el)
                self._settle_any()
                stayed = self._identify() is state_cls
                config = {"viewport": vp.name, "input": iv["variant"],
                          "field": f.find.label()}
                steps = base_steps + [{"action": f"submit {el.label} / {iv['variant']}"}]
                if sub.invalid_stays and not stayed:
                    self._add(BreakageCase(state_cls.__name__, DO, el.label,
                              f"invalid input ({iv['variant']}) accepted — navigated away",
                              config, steps))
                elif sub.invalid_shows is not None and stayed \
                        and not checks._safe(sub.invalid_shows.resolve(self.page).visible):
                    self._add(BreakageCase(state_cls.__name__, DO, el.label,
                              f"invalid input ({iv['variant']}) showed no error",
                              config, steps))

    # -- navigation --------------------------------------------------------
    def _plan_paths(self) -> Dict[str, List[Element]]:
        by_name = {s.__name__: s for s in self.states}
        paths: Dict[str, List[Element]] = {}
        if self.site.entry is None:
            return paths
        paths[self.site.entry.__name__] = []
        queue: deque = deque([self.site.entry])
        while queue:
            s = queue.popleft()
            for el in s().elements():
                if el.is_destructive() and self.mode != "chaos":
                    continue
                t = el.target()
                if t is not None and t.__name__ not in paths and t.__name__ in by_name:
                    paths[t.__name__] = paths[s.__name__] + [el]
                    queue.append(t)
        return paths

    def _go_to(self, state_cls: Type[State]) -> bool:
        self._actions += 1
        self._enter()
        for el in self.paths.get(state_cls.__name__, []):
            if el.submit is not None:
                self._fill_valid(el.submit)
            try:
                el.find.resolve(self.page).click()
            except Exception:
                return False
            if not self._settle_to(el.target()):
                return False
        return self._identify() is state_cls

    def _enter(self) -> None:
        role = self.site.roles[0] if self.site.roles else None
        if role is not None and role.login is not None:
            role.login(self.page)
        else:
            self.page.goto(self.site.base_url or "/")
        self._settle_to(self.site.entry)

    def _settle_to(self, target: Optional[Type[State]]) -> bool:
        waited = 0
        while waited < self.settle_timeout_ms:
            if self._identify() is target:
                return True
            self.page.wait(self.settle_interval_ms)
            waited += self.settle_interval_ms
        return self._identify() is target

    def _settle_any(self) -> None:
        # give a submit a moment to either navigate or show an inline error
        self.page.wait(self.settle_interval_ms * 3)

    def _identify(self) -> Optional[Type[State]]:
        for sc in self.states:
            try:
                if sc().identify(self.page):
                    return sc
            except Exception:
                continue
        return None

    # -- helpers -----------------------------------------------------------
    def _fill_valid(self, sub) -> None:
        for f in sub.fields:
            try:
                f.find.resolve(self.page).fill(valid_value(f, self.site.seed_data))
            except Exception:
                pass

    def _click(self, el: Element) -> None:
        try:
            el.find.resolve(self.page).click()
        except Exception:
            pass

    def _steps_to(self, state_cls: Type[State]) -> List[dict]:
        return [{"action": el.label} for el in self.paths.get(state_cls.__name__, [])]

    def _out_of_budget(self) -> bool:
        return self._actions >= self.site.budgets.max_actions

    def _note_checked(self, name: str) -> None:
        if name not in self._report.states_checked:
            self._report.states_checked.append(name)

    def _add(self, case: BreakageCase) -> None:
        sig = case.signature
        if sig in self.suppressions or sig in self._seen_sigs:
            return  # suppressed by triage, or an identical duplicate this run
        self._seen_sigs.add(sig)
        self._report.cases.append(case)
