"""The map — how a site is described (code-as-config).

Per state, the map lists **elements**. Every element carries a visibility
expectation and may be informational, interactive, or both. The interactive
aspect is one of ``click`` / ``fill`` / ``submit`` / ``toggle``.

See ``docs/architecture.md`` (v2) for the design.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type
from urllib.parse import urlparse

# Re-exported so a map only imports from ``edumaze``.
from .budgets import Budgets  # noqa: F401
from .role import Role  # noqa: F401

# ---------------------------------------------------------------------------
# Locators
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Locator:
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    placeholder: Optional[str] = None
    css: Optional[str] = None

    def resolve(self, page):
        if self.role is not None:
            return page.by_role(self.role, self.name)
        if self.placeholder is not None:
            return page.by_placeholder(self.placeholder)
        if self.text is not None:
            return page.by_text(self.text)
        if self.css is not None:
            return page.by_css(self.css)
        raise ValueError("empty locator")

    def label(self) -> str:
        for part in (self.name, self.text, self.placeholder, self.css, self.role):
            if part:
                return str(part)
        return "?"


def role(name_role: str, name: Optional[str] = None) -> Locator:
    return Locator(role=name_role, name=name)


def text(value: str) -> Locator:
    return Locator(text=value)


def placeholder(value: str) -> Locator:
    return Locator(placeholder=value)


def css(selector: str) -> Locator:
    return Locator(css=selector)


# ---------------------------------------------------------------------------
# Field types (for form fuzzing)
# ---------------------------------------------------------------------------
TEXT = "text"
EMAIL = "email"
NUMBER = "number"
PASSWORD = "password"


@dataclass
class Field:
    """One form input and its constraints — the fuzzer works from these."""

    find: Locator
    type: str = TEXT
    required: bool = False
    max_len: Optional[int] = None
    min_len: Optional[int] = None
    #: An explicit valid example; otherwise one is derived from ``type``.
    valid: Optional[str] = None


# ---------------------------------------------------------------------------
# Interactive aspects
# ---------------------------------------------------------------------------
@dataclass
class Click:
    """A link/button that navigates to (or opens) another state."""

    to: Optional[Type["State"]] = None
    destructive: bool = False  # gated by the safety mode


@dataclass
class Submit:
    """A form submission carried by its submit button element."""

    fields: List[Field] = field(default_factory=list)
    #: State a *valid* submit should reach.
    on_valid: Optional[Type["State"]] = None
    #: A valid submit should navigate; an invalid one should NOT (graceful).
    invalid_stays: bool = True
    #: Optional element expected to appear after an invalid submit (an error).
    invalid_shows: Optional[Locator] = None
    destructive: bool = False


@dataclass
class Toggle:
    """A control (menu/modal/accordion) that reveals/hides other elements."""

    reveals: List[Locator] = field(default_factory=list)
    hides: List[Locator] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Element — the unit of the map
# ---------------------------------------------------------------------------
@dataclass
class Element:
    find: Locator
    #: Expected visibility in this state's base configuration.
    visible: bool = True
    #: Informational aspect: content the user should perceive (for reporting).
    info: bool = False
    # Interactive aspect (at most one is set):
    click: Optional[Click] = None
    submit: Optional[Submit] = None
    toggle: Optional[Toggle] = None
    #: Short label for reports/signatures; defaults to the locator's label.
    name: Optional[str] = None

    @property
    def label(self) -> str:
        return self.name or self.find.label()

    @property
    def interactive(self) -> bool:
        return self.click is not None or self.submit is not None \
            or self.toggle is not None

    def target(self) -> Optional[Type["State"]]:
        if self.click is not None:
            return self.click.to
        if self.submit is not None:
            return self.submit.on_valid
        return None

    def is_destructive(self) -> bool:
        if self.click is not None:
            return self.click.destructive
        if self.submit is not None:
            return self.submit.destructive
        return False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class State:
    """One page/screen. Subclass it: set ``url`` (or override ``identify``) and
    return the page's elements from ``elements()``."""

    url: Optional[str] = None

    def identify(self, page) -> bool:
        """True if ``page`` is this state. Default: exact URL-path match."""
        if self.url is None:
            return False
        path = _norm(urlparse(page.url).path or "/")
        return path == _norm(self.url)

    def elements(self) -> List[Element]:
        return []

    @property
    def name(self) -> str:
        return type(self).__name__


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


DESKTOP = Viewport("desktop", 1280, 800)
MOBILE = Viewport("mobile", 390, 844)


class Site:
    base_url: str = ""
    domain_allowlist: List[str] = []
    entry: Optional[Type[State]] = None
    roles: List[Role] = []
    #: The responsive variation dimension.
    viewports: List[Viewport] = [DESKTOP, MOBILE]
    budgets: Budgets = Budgets()
    #: Values used for valid fills, keyed by field type or field label.
    seed_data: Dict[str, str] = {}
    #: A load slower than this (ms) is a signal-level finding.
    slow_load_ms: int = 4000
    extra_states: List[Type[State]] = []

    @property
    def site_id(self) -> str:
        return getattr(self, "id", type(self).__name__)

    def states(self) -> List[Type[State]]:
        """All reachable states: BFS from ``entry`` through element targets."""
        seen: Dict[str, Type[State]] = {}
        queue: deque = deque()

        def add(sc: Optional[Type[State]]) -> None:
            if sc is not None and sc.__name__ not in seen:
                seen[sc.__name__] = sc
                queue.append(sc)

        add(self.entry)
        for sc in self.extra_states:
            add(sc)
        while queue:
            sc = queue.popleft()
            for el in sc().elements():
                add(el.target())
        return list(seen.values())


def _norm(url: str) -> str:
    return url.rstrip("/") or "/"
