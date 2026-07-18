"""An in-memory driver: a fake site you can walk without a browser.

This is a first-class framework tool, not just test scaffolding — it lets a maze
author (or the crawl skill's own tests) exercise a maze's logic deterministically
and fast. You describe states, their elements, and where clicking each element
leads; :class:`FakePage` then satisfies the :class:`~edumaze.page.Page` protocol
so the real :class:`~edumaze.player.Player` drives it unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..page import ElementNotFound


@dataclass
class FakeElement:
    role: str
    name: str = ""
    text: str = ""
    #: State to navigate to when clicked (None = inert, e.g. a text field).
    on_click: Optional[str] = None


@dataclass
class FakeState:
    name: str
    url: str
    elements: List[FakeElement] = field(default_factory=list)
    status: int = 200
    console_errors: List[str] = field(default_factory=list)


class FakeSite:
    """A directed graph of :class:`FakeState` — the simulated app under test."""

    def __init__(self, states: List[FakeState], start: str) -> None:
        self.states: Dict[str, FakeState] = {s.name: s for s in states}
        if start not in self.states:
            raise ValueError(f"start state {start!r} not defined")
        self.start = start

    def state_for_url(self, url: str) -> Optional[str]:
        target = _norm(url)
        for name, st in self.states.items():
            if _norm(st.url) == target or target.endswith(_norm(st.url)):
                return name
        return None


class _Handle:
    """A lazy query handle satisfying the Element protocol."""

    def __init__(self, page: "FakePage", role: Optional[str],
                 name: Optional[str], text: Optional[str]) -> None:
        self._page = page
        self._role = role
        self._name = name
        self._text = text

    def _find(self) -> Optional[FakeElement]:
        return self._page._find(self._role, self._name, self._text)

    def visible(self) -> bool:
        return self._find() is not None

    exists = visible

    def text(self) -> str:
        el = self._find()
        return el.text if el else ""

    def click(self) -> None:
        el = self._find()
        if el is None:
            raise ElementNotFound(
                f"no element role={self._role!r} name={self._name!r} "
                f"text={self._text!r} on {self._page.url}")
        if el.on_click is not None:
            self._page._navigate(el.on_click)

    def fill(self, value: str) -> None:
        el = self._find()
        if el is None:
            raise ElementNotFound(
                f"no field role={self._role!r} name={self._name!r} "
                f"on {self._page.url}")
        self._page._fills[(el.role, el.name)] = value


class FakePage:
    """Satisfies :class:`~edumaze.page.Page` against a :class:`FakeSite`."""

    def __init__(self, site: FakeSite) -> None:
        self._site = site
        self._current = site.start
        self._history: List[str] = []
        self._fills: Dict[tuple, str] = {}
        self.navigations: List[str] = [site.start]  # for assertions in tests

    # -- state -------------------------------------------------------------
    @property
    def _state(self) -> FakeState:
        return self._site.states[self._current]

    @property
    def url(self) -> str:
        return self._state.url

    @property
    def status(self) -> Optional[int]:
        return self._state.status

    @property
    def console_errors(self) -> List[str]:
        return list(self._state.console_errors)

    # -- navigation --------------------------------------------------------
    def goto(self, path: str) -> None:
        name = self._site.state_for_url(path)
        self._navigate(name if name is not None else self._site.start)

    def back(self) -> None:
        if self._history:
            self._current = self._history.pop()
            self.navigations.append(self._current)

    def _navigate(self, state_name: str) -> None:
        if state_name not in self._site.states:
            raise ElementNotFound(f"navigation to unknown state {state_name!r}")
        self._history.append(self._current)
        self._current = state_name
        self.navigations.append(state_name)

    # -- queries -----------------------------------------------------------
    def by_role(self, role: str, name: Optional[str] = None) -> _Handle:
        return _Handle(self, role, name, None)

    def by_text(self, text: str) -> _Handle:
        return _Handle(self, None, None, text)

    def by_css(self, selector: str) -> _Handle:
        # CSS isn't modeled; treat the selector as a text probe so mazes that
        # fall back to CSS still run (and simply won't match here).
        return _Handle(self, None, None, selector)

    def _find(self, role: Optional[str], name: Optional[str],
              text: Optional[str]) -> Optional[FakeElement]:
        for el in self._state.elements:
            if role is not None and el.role != role:
                continue
            if name is not None and el.name != name:
                continue
            if text is not None and text not in el.text:
                continue
            if role is None and text is None:
                continue  # empty query matches nothing
            return el
        return None


def _norm(url: str) -> str:
    return url.rstrip("/") or "/"
