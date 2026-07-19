"""The driver-agnostic page/element interface.

The map (and the engine) only ever touch these two protocols. Real browsers
(Playwright) and the in-memory test driver both implement them, so the same map
runs against either without change.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Element(Protocol):
    """A handle to (a query for) a single element on the page.

    Handles are lazy: they describe *how to find* an element and resolve on each
    call, so ``visible()`` may be False now and True after an action.
    """

    def visible(self) -> bool: ...
    def exists(self) -> bool: ...
    def enabled(self) -> bool: ...
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

    @property
    def last_load_ms(self) -> Optional[int]:
        """Wall-clock ms of the last navigation/click that caused a load."""
        ...

    def goto(self, path: str) -> None: ...
    def back(self) -> None: ...

    def wait(self, ms: int) -> None:
        """Pause ~ms milliseconds so an async (SPA) re-render can settle."""
        ...

    def set_viewport(self, width: int, height: int) -> None:
        """Resize the viewport (the responsive variation dimension)."""
        ...

    def by_role(self, role: str, name: Optional[str] = None) -> Element: ...
    def by_text(self, text: str) -> Element: ...
    def by_placeholder(self, text: str) -> Element: ...
    def by_css(self, selector: str) -> Element: ...


class ElementNotFound(Exception):
    """Raised when an action targets an element that isn't present."""
