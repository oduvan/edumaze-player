"""An in-memory driver: a fake site you can stress-test without a browser.

Rich enough to exercise the engine's checks deterministically: elements can be
hidden at certain viewports or until a toggle is opened, buttons can be disabled,
and submit buttons can require valid fills before they navigate (so form fuzzing
has something real to catch).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..page import ElementNotFound

MOBILE_MAX_WIDTH = 768


@dataclass
class FakeElement:
    role: str = ""
    name: str = ""
    text: str = ""
    placeholder: str = ""
    enabled: bool = True
    #: base visibility
    visible: bool = True
    #: viewport names where this element is hidden (e.g. ("mobile",))
    hidden_on: tuple = ()
    #: name of a toggle element that must be opened for this to be visible
    revealed_by: Optional[str] = None
    # interactive behaviour:
    on_click: Optional[str] = None          # navigate to this state when clicked
    is_toggle: bool = False                 # clicking opens (reveals) instead of navigating
    #: fill keys that must be non-empty for on_click to fire (models validation)
    requires: tuple = ()
    #: {fill_key: max_len} — a fill longer than this blocks on_click
    max_lens: Dict[str, int] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return self.placeholder or self.name or self.text


@dataclass
class FakeState:
    name: str
    url: str
    elements: List[FakeElement] = field(default_factory=list)
    status: int = 200
    console_errors: List[str] = field(default_factory=list)
    load_ms: int = 0


class FakeSite:
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
    def __init__(self, page: "FakePage", role, name, text, placeholder=None) -> None:
        self._page = page
        self._role, self._name, self._text, self._ph = role, name, text, placeholder

    def _find(self) -> Optional[FakeElement]:
        return self._page._find(self._role, self._name, self._text, self._ph)

    def visible(self) -> bool:
        el = self._find()
        return el is not None and self._page._is_visible(el)

    def exists(self) -> bool:
        return self._find() is not None

    def enabled(self) -> bool:
        el = self._find()
        return bool(el and el.enabled)

    def text(self) -> str:
        el = self._find()
        return el.text if el else ""

    def click(self) -> None:
        el = self._find()
        if el is None or not self._page._is_visible(el):
            raise ElementNotFound(f"not clickable: {self._name or self._text or self._ph!r}")
        if el.is_toggle:
            self._page._opened.add(el.name or el.text)
            return
        if el.on_click is not None and self._page._satisfied(el):
            self._page._navigate(el.on_click)

    def fill(self, value: str) -> None:
        el = self._find()
        if el is None:
            raise ElementNotFound(f"no field {self._ph or self._name!r}")
        self._page._fills[el.key] = value


class FakePage:
    def __init__(self, site: FakeSite) -> None:
        self._site = site
        self._current = site.start
        self._opened: set = set()
        self._fills: Dict[str, str] = {}
        self._w, self._h = 1280, 800
        self._last_load_ms = site.states[site.start].load_ms

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

    @property
    def last_load_ms(self) -> Optional[int]:
        return self._last_load_ms

    def goto(self, path: str) -> None:
        name = self._site.state_for_url(path)
        self._navigate(name if name is not None else self._site.start)

    def back(self) -> None:
        pass

    def wait(self, ms: int) -> None:
        return None

    def set_viewport(self, width: int, height: int) -> None:
        self._w, self._h = width, height

    def by_role(self, role, name=None):
        return _Handle(self, role, name, None)

    def by_text(self, text):
        return _Handle(self, None, None, text)

    def by_placeholder(self, text):
        return _Handle(self, None, None, None, placeholder=text)

    def by_css(self, selector):
        return _Handle(self, None, None, selector)

    # -- internals ---------------------------------------------------------
    def _viewport_name(self) -> str:
        return "mobile" if self._w < MOBILE_MAX_WIDTH else "desktop"

    def _is_visible(self, el: FakeElement) -> bool:
        if not el.visible:
            return False
        if self._viewport_name() in el.hidden_on:
            return False
        if el.revealed_by is not None and el.revealed_by not in self._opened:
            return False
        return True

    def _satisfied(self, el: FakeElement) -> bool:
        for k in el.requires:
            if not self._fills.get(k):
                return False
        for k, limit in el.max_lens.items():
            if len(self._fills.get(k, "")) > limit:
                return False
        return True

    def _navigate(self, state_name: str) -> None:
        if state_name not in self._site.states:
            raise ElementNotFound(f"navigation to unknown state {state_name!r}")
        self._current = state_name
        self._opened.clear()
        self._fills.clear()
        self._last_load_ms = self._site.states[state_name].load_ms

    def _find(self, role, name, text, placeholder) -> Optional[FakeElement]:
        for el in self._state.elements:
            if role is not None and el.role != role:
                continue
            if name is not None and el.name != name:
                continue
            if text is not None and text not in el.text:
                continue
            if placeholder is not None and el.placeholder != placeholder:
                continue
            if role is None and text is None and placeholder is None:
                continue
            return el
        return None


def _norm(url: str) -> str:
    return url.rstrip("/") or "/"
