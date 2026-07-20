"""Real-browser adapter. Optional: ``pip install edumaze[playwright]``.

Playwright is imported lazily so the framework (and its tests) work without a
browser installed. This module implements the same :class:`~edumaze.page.Page`
protocol the in-memory driver does, so mazes run unchanged.
"""
from __future__ import annotations

import time
from typing import List, Optional


class PlaywrightPage:
    def __init__(self, pw_page, host_allowlist: Optional[List[str]] = None) -> None:
        self._page = pw_page
        self._status: Optional[int] = None
        self._console: List[str] = []
        self._allow = host_allowlist or []
        self._last_load_ms: Optional[int] = None
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

    @property
    def last_load_ms(self) -> Optional[int]:
        return self._last_load_ms

    def goto(self, path: str) -> None:
        self._reset_page_signals()
        t0 = time.perf_counter()
        resp = self._page.goto(path)
        self._last_load_ms = int((time.perf_counter() - t0) * 1000)
        if resp is not None:
            self._status = resp.status

    def back(self) -> None:
        self._reset_page_signals()
        self._page.go_back()

    def wait(self, ms: int) -> None:
        self._page.wait_for_timeout(ms)

    def set_viewport(self, width: int, height: int) -> None:
        self._page.set_viewport_size({"width": width, "height": height})

    def by_role(self, role: str, name: Optional[str] = None):
        loc = (self._page.get_by_role(role, name=name) if name
               else self._page.get_by_role(role))
        return _Loc(loc, self)

    def by_text(self, text: str):
        return _Loc(self._page.get_by_text(text), self)

    def by_placeholder(self, text: str):
        return _Loc(self._page.get_by_placeholder(text), self)

    def by_css(self, selector: str):
        return _Loc(self._page.locator(selector), self)

    def dismiss_overlays(self) -> bool:
        """Best-effort close of cookie banners / marketing popups that intercept
        clicks. Returns True if it dismissed (or plausibly dismissed) something."""
        acted = False
        try:
            self._page.keyboard.press("Escape")
        except Exception:
            pass
        close_selectors = [
            "[class*='om-close']", "[id^='om-'] [class*='close']", "[id^='om-'] button",
            "button[aria-label*='close' i]", "[aria-label*='Close' i]",
            "button:has-text('No thanks')", "button:has-text('Close')",
            ".sequoyah-close", "#onetrust-accept-btn-handler",
            "button:has-text('Accept All')", "button:has-text('Accept')",
        ]
        for sel in close_selectors:
            try:
                loc = self._page.locator(sel)
                for i in range(min(loc.count(), 3)):
                    el = loc.nth(i)
                    if el.is_visible():
                        el.click(timeout=1200, force=True)
                        acted = True
            except Exception:
                continue
        return acted


class _Loc:
    """Wraps a Playwright locator that may match several elements.

    Real sites duplicate labels (a hidden hover-menu link *and* a visible footer
    link share the accessible name), so this targets the *visible* match rather
    than blindly ``.first``, and scrolls via JS (Playwright's auto-scroll stalls
    on tall lazy pages) before clicking.
    """

    def __init__(self, locator, page: PlaywrightPage) -> None:
        self._raw = locator
        self._page = page

    def _visible_elements(self) -> list:
        try:
            n = self._raw.count()
        except Exception:
            return []
        out = []
        for i in range(min(n, 25)):
            el = self._raw.nth(i)
            try:
                if not el.is_visible():
                    continue
                # Playwright's is_visible() ignores off-canvas positioning, so a
                # closed drawer/menu translated off-screen (e.g. translateX(-100%))
                # still reads "visible". Require the box to actually be on-screen.
                box = el.bounding_box()
                if box is None:
                    continue
                if box["x"] + box["width"] <= 0 or box["y"] + box["height"] <= 0:
                    continue  # entirely off the top/left — not user-visible
                out.append(el)
            except Exception:
                continue
        return out

    def visible(self) -> bool:
        return len(self._visible_elements()) > 0

    exists = visible

    def enabled(self) -> bool:
        els = self._visible_elements()
        try:
            return (els[0] if els else self._raw.first).is_enabled()
        except Exception:
            return False

    def text(self) -> str:
        els = self._visible_elements()
        try:
            return (els[0] if els else self._raw.first).inner_text()
        except Exception:
            return ""

    def click(self) -> None:
        self._page._reset_page_signals()
        last_err = None
        for attempt in range(3):
            candidates = self._visible_elements() or [self._raw.first]
            for el in candidates:
                try:
                    el.evaluate("e => e.scrollIntoView({block: 'center'})")
                except Exception:
                    pass
                try:
                    t0 = time.perf_counter()
                    el.click(timeout=4000)
                    self._page._last_load_ms = int((time.perf_counter() - t0) * 1000)
                    return
                except Exception as exc:  # try the next visible match
                    last_err = exc
            # a click was blocked — often a popup/cookie overlay. Clear it & retry.
            if not self._page.dismiss_overlays():
                break
        if last_err is not None:
            raise last_err

    def fill(self, value: str) -> None:
        els = self._visible_elements()
        (els[0] if els else self._raw.first).fill(value)


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
