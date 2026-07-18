"""The driver-agnostic page/element interface.

Maze scripts (and the framework) only ever touch these two protocols. Real
browsers (Playwright) and the in-memory test driver both implement them, so the
exact same maze runs against either without change.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Element(Protocol):
    """A handle to (a query for) a single element on the page.

    Handles are lazy: they describe *how to find* an element, and resolve on each
    call. So ``visible()`` may be False now and True after a navigation.
    """

    def visible(self) -> bool: ...
    def exists(self) -> bool: ...
    def text(self) -> str: ...
    def click(self) -> None: ...
    def fill(self, value: str) -> None: ...


@runtime_checkable
class Page(Protocol):
    """The current page. Accessible-first: prefer ``by_role`` over ``by_css``."""

    @property
    def url(self) -> str: ...

    @property
    def status(self) -> Optional[int]:
        """HTTP status of the last document navigation, or None if unknown."""
        ...

    @property
    def console_errors(self) -> list[str]:
        """Uncaught JS console errors observed on the current page."""
        ...

    def goto(self, path: str) -> None: ...
    def back(self) -> None: ...

    def by_role(self, role: str, name: Optional[str] = None) -> Element: ...
    def by_text(self, text: str) -> Element: ...
    def by_css(self, selector: str) -> Element: ...


class ElementNotFound(Exception):
    """Raised when an action targets an element that isn't present."""
