"""Nodes and options — the vocabulary a maze script is written in.

A ``Node`` subclass *is* a state: it says how to recognize itself
(:meth:`Node.matches`), what you can do from it (:meth:`Node.options`), and what
must be true when you're on it (:meth:`Node.accept`). The ``go``/``submit``/
``external``/``back`` helpers keep option declarations terse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from .page import Page

# Edge classifications — drive the safety policy.
SAFE = "safe"
DESTRUCTIVE = "destructive"
EXTERNAL = "external"

# Option kinds.
GO = "go"
SUBMIT = "submit"
BACK = "back"


@dataclass(frozen=True)
class Locator:
    role_: Optional[str] = None
    name: Optional[str] = None
    text_: Optional[str] = None
    placeholder_: Optional[str] = None
    css_: Optional[str] = None

    # Constructors — accessible-first, but real inputs often only have a
    # placeholder, so that's a first-class strategy too.
    @staticmethod
    def role(role: str, name: Optional[str] = None) -> "Locator":
        return Locator(role_=role, name=name)

    @staticmethod
    def text(value: str) -> "Locator":
        return Locator(text_=value)

    @staticmethod
    def placeholder(value: str) -> "Locator":
        return Locator(placeholder_=value)

    @staticmethod
    def css(selector: str) -> "Locator":
        return Locator(css_=selector)

    def resolve(self, page: Page):
        if self.role_ is not None:
            return page.by_role(self.role_, self.name)
        if self.placeholder_ is not None:
            return page.by_placeholder(self.placeholder_)
        if self.text_ is not None:
            return page.by_text(self.text_)
        if self.css_ is not None:
            return page.by_css(self.css_)
        raise ValueError("empty locator")


@dataclass
class Option:
    """One outgoing edge from a node."""

    kind: str
    label: str
    to: Optional[Type["Node"]] = None
    classify: str = SAFE
    locator: Optional[Locator] = None
    # For SUBMIT: {field_label: semantic}; values filled from Site.seed_data.
    fields: Dict[str, str] = field(default_factory=dict)

    @property
    def target_name(self) -> Optional[str]:
        return self.to.__name__ if self.to is not None else None


class Node:
    """Base class for a state. Subclass it in a maze script."""

    #: URL (suffix) used by the default :meth:`matches`. Override matches for
    #: content-based identity.
    url: Optional[str] = None

    # --- identity ---------------------------------------------------------
    def matches(self, page: Page) -> bool:
        """True if ``page`` is this state. Default: URL-suffix match."""
        if self.url is None:
            return False
        return _norm(page.url).endswith(_norm(self.url))

    # --- structure --------------------------------------------------------
    def options(self) -> List[Option]:
        """Outgoing edges. Labels must be unique within a node."""
        return []

    # --- oracle -----------------------------------------------------------
    def accept(self, page: Page) -> None:
        """Acceptance criteria, as code. Raise/assert on violation."""
        return None

    # --- option helpers ---------------------------------------------------
    def go(self, name: str, to: Optional[Type["Node"]] = None,
           classify: str = SAFE, role: str = "link") -> Option:
        return Option(GO, name, to=to, classify=classify,
                      locator=Locator.role(role, name))

    def submit(self, form: str, fields: Dict, to: Optional[Type["Node"]] = None,
               classify: str = SAFE, button: Optional[str] = None) -> Option:
        # fields keys may be a plain str (targets textbox by accessible name) or
        # a Locator (e.g. Locator.placeholder(...)); values are seed_data semantics.
        return Option(SUBMIT, form, to=to, classify=classify, fields=dict(fields),
                      locator=Locator.role("button", button or form))

    def external(self, name: str, role: str = "link") -> Option:
        return Option(GO, name, to=None, classify=EXTERNAL,
                      locator=Locator.role(role, name))

    def back(self, to: Optional[Type["Node"]] = None) -> Option:
        return Option(BACK, "<back>", to=to, classify=SAFE)

    @property
    def name(self) -> str:
        return type(self).__name__


def _norm(url: str) -> str:
    return url.rstrip("/") or "/"
