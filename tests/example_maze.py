"""A hand-written maze + a matching in-memory site to run it against.

This is the reference example: it exercises healthy paths, a destructive edge
that ``explore`` mode must avoid, and two deliberately broken states —
``Reports`` (HTTP 500, an L1 technical failure) and ``Profile`` (missing nav, an
L1 acceptance failure). Keeping the maze and its fake app side by side makes the
node<->state correspondence obvious.
"""
from __future__ import annotations

from edumaze import Budgets, DESTRUCTIVE, Node, Role, Site
from edumaze.drivers.fake import FakeElement, FakePage, FakeSite, FakeState


# --------------------------------------------------------------------------
# The maze (what the crawl skill would generate)
# --------------------------------------------------------------------------
def login_admin(page):
    page.goto("/login")
    page.by_role("textbox", name="Email").fill("admin@example.test")
    page.by_role("textbox", name="Password").fill("secret")
    page.by_role("button", name="Sign in").click()


class Dashboard(Node):
    url = "/dashboard"

    def matches(self, page):
        return page.by_role("heading", name="Dashboard").visible()

    def options(self):
        return [
            self.go("Settings", to=Settings),
            self.go("Reports", to=Reports),
            self.go("Profile", to=Profile),
            self.submit("Search", fields={"Query": "text"}, to=SearchResults),
        ]

    def accept(self, page):
        assert page.by_role("navigation").visible(), "nav missing"


class Settings(Node):
    url = "/settings"

    def matches(self, page):
        return page.by_role("heading", name="Settings").visible()

    def options(self):
        return [self.go("Delete account", to=Deleted, classify=DESTRUCTIVE)]

    def accept(self, page):
        assert page.by_role("navigation").visible(), "nav missing"


class SearchResults(Node):
    url = "/search"

    def matches(self, page):
        return page.by_role("heading", name="Results").visible()

    def options(self):
        return [self.go("Back to dashboard", to=Dashboard)]

    def accept(self, page):
        assert page.by_role("heading", name="Results").visible()


class Reports(Node):
    """Broken: the server returns 500. L1 technical catches it. Uses the
    default URL matcher so it resolves regardless of page content."""

    url = "/reports"

    def options(self):
        return []


class Profile(Node):
    """Broken: renders 200 but is missing its nav. L1 acceptance catches it."""

    url = "/profile"

    def options(self):
        return []

    def accept(self, page):
        assert page.by_role("navigation").visible(), "nav missing on profile"


class Deleted(Node):
    """Only reachable via a destructive edge; must never be seen in explore."""

    url = "/deleted"

    def matches(self, page):
        return page.by_role("heading", name="Account deleted").visible()

    def options(self):
        return []

    def accept(self, page):
        assert page.by_role("heading", name="Account deleted").visible()


class ExampleSite(Site):
    id = "example"
    base_url = "https://app.example.test/login"
    domain_allowlist = ["app.example.test"]
    entry = Dashboard
    roles = [Role("admin", login=login_admin,
                  logged_in_when=("heading", "Dashboard"))]
    budgets = Budgets(max_actions=100)
    seed_data = {"text": "hello world"}


class ExampleSiteChaos(ExampleSite):
    """Same maze, but a reset hook is declared → chaos mode may touch
    destructive edges."""

    reset_hook = {"method": "POST", "url": "/test/reset"}


# --------------------------------------------------------------------------
# The simulated app (stands in for the real site under test)
# --------------------------------------------------------------------------
def build_fake_site() -> FakeSite:
    nav = FakeElement(role="navigation", name="Main")
    states = [
        FakeState("Login", "/login", [
            FakeElement("textbox", "Email"),
            FakeElement("textbox", "Password"),
            FakeElement("button", "Sign in", on_click="Dashboard"),
        ]),
        FakeState("Dashboard", "/dashboard", [
            FakeElement("heading", "Dashboard"), nav,
            FakeElement("link", "Settings", on_click="Settings"),
            FakeElement("link", "Reports", on_click="Reports"),
            FakeElement("link", "Profile", on_click="Profile"),
            FakeElement("textbox", "Query"),
            FakeElement("button", "Search", on_click="SearchResults"),
        ]),
        FakeState("Settings", "/settings", [
            FakeElement("heading", "Settings"), nav,
            FakeElement("link", "Delete account", on_click="Deleted"),
        ]),
        FakeState("SearchResults", "/search", [
            FakeElement("heading", "Results"), nav,
            FakeElement("link", "Back to dashboard", on_click="Dashboard"),
        ]),
        # Broken: 500.
        FakeState("Reports", "/reports", [
            FakeElement("heading", "Server Error"),
        ], status=500),
        # Broken: 200 but NO nav element.
        FakeState("Profile", "/profile", [
            FakeElement("heading", "Profile"),
        ]),
        FakeState("Deleted", "/deleted", [
            FakeElement("heading", "Account deleted"), nav,
        ]),
    ]
    return FakeSite(states, start="Login")


def new_page() -> FakePage:
    return FakePage(build_fake_site())
