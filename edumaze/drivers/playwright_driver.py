"""Real-browser adapter. Optional: ``pip install edumaze[playwright]``.

Playwright is imported lazily so the framework (and its tests) work without a
browser installed. This module implements the same :class:`~edumaze.page.Page`
protocol the in-memory driver does, so mazes run unchanged.
"""
from __future__ import annotations

from typing import List, Optional


class PlaywrightPage:
    def __init__(self, pw_page, host_allowlist: Optional[List[str]] = None) -> None:
        self._page = pw_page
        self._status: Optional[int] = None
        self._console: List[str] = []
        self._allow = host_allowlist or []
        pw_page.on("console", self._on_console)
        pw_page.on("response", self._on_response)

    # -- event capture -----------------------------------------------------
    def _on_console(self, msg) -> None:
        if msg.type == "error":
            self._console.append(msg.text)

    def _on_response(self, resp) -> None:
        # Track the status of top-level document navigations only.
        try:
            if resp.request.is_navigation_request() and resp.url == self._page.url:
                self._status = resp.status
        except Exception:
            pass

    def _reset_page_signals(self) -> None:
        self._console = []
        self._status = None

    # -- Page protocol -----------------------------------------------------
    @property
    def url(self) -> str:
        return self._page.url

    @property
    def status(self) -> Optional[int]:
        return self._status

    @property
    def console_errors(self) -> List[str]:
        return list(self._console)

    def goto(self, path: str) -> None:
        self._reset_page_signals()
        resp = self._page.goto(path)
        if resp is not None:
            self._status = resp.status

    def back(self) -> None:
        self._reset_page_signals()
        self._page.go_back()

    def by_role(self, role: str, name: Optional[str] = None):
        loc = (self._page.get_by_role(role, name=name) if name
               else self._page.get_by_role(role))
        return _Loc(loc, self)

    def by_text(self, text: str):
        return _Loc(self._page.get_by_text(text), self)

    def by_css(self, selector: str):
        return _Loc(self._page.locator(selector), self)


class _Loc:
    def __init__(self, locator, page: PlaywrightPage) -> None:
        self._loc = locator.first
        self._page = page

    def visible(self) -> bool:
        try:
            return self._loc.is_visible()
        except Exception:
            return False

    exists = visible

    def text(self) -> str:
        try:
            return self._loc.inner_text()
        except Exception:
            return ""

    def click(self) -> None:
        self._page._reset_page_signals()
        self._loc.click()

    def fill(self, value: str) -> None:
        self._loc.fill(value)


def launch(base_url: str, headless: bool = True):
    """Context manager yielding a :class:`PlaywrightPage`. Lazy-imports Playwright."""
    from contextlib import contextmanager

    from playwright.sync_api import sync_playwright

    @contextmanager
    def _ctx():
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context()
            page = PlaywrightPage(context.new_page())
            try:
                yield page
            finally:
                context.close()
                browser.close()

    return _ctx()
