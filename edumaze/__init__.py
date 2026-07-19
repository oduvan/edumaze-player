"""edumaze — a deterministic breakage-hunter for websites.

A **map** describes a site as states, each with a list of **elements** (each
informational, interactive, or both, with a visible/hidden expectation). The
**engine** stress-tests it — varying viewport, fuzzing forms, toggling menus,
walking paths — and reports **breakage cases**. See ``docs/architecture.md``.

Public API for a map:

    from edumaze import (State, Element, Site, Field, Submit, Toggle, Click,
                         role, text, placeholder, css, Budgets, Role,
                         DESKTOP, MOBILE, Viewport, TEXT, EMAIL, NUMBER)

and, to run one without a browser:

    from edumaze.drivers.fake import FakeSite, FakeState, FakeElement, FakePage
"""
from .budgets import Budgets
from .cases import DO, SEE, SIGNAL, BreakageCase, Report
from .engine import Engine
from .model import (
    DESKTOP, EMAIL, MOBILE, NUMBER, PASSWORD, TEXT,
    Click, Element, Field, Locator, Site, State, Submit, Toggle, Viewport,
    css, placeholder, role, text,
)
from .page import Element as ElementHandle
from .page import ElementNotFound, Page
from .role import Role

__all__ = [
    # map vocabulary
    "State", "Element", "Site", "Field", "Submit", "Toggle", "Click",
    "Locator", "role", "text", "placeholder", "css",
    "Viewport", "DESKTOP", "MOBILE",
    "TEXT", "EMAIL", "NUMBER", "PASSWORD",
    "Role", "Budgets",
    # engine + output
    "Engine", "Report", "BreakageCase", "SEE", "DO", "SIGNAL",
    # driver protocols
    "Page", "ElementHandle", "ElementNotFound",
]
