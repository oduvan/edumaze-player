"""End-to-end: the Player walks the example maze against the in-memory app."""
from __future__ import annotations

from edumaze import CHAOS, EXPLORE, Player

from .example_maze import ExampleSite, ExampleSiteChaos, new_page


def _summaries(report):
    return [f.summary for f in report.findings]


def test_explore_finds_exactly_the_two_breakages():
    report = Player(ExampleSite(), new_page(), seed=1, mode=EXPLORE).run()
    summaries = _summaries(report)

    assert len(report.findings) == 2, summaries
    assert any("HTTP 500" in s for s in summaries), summaries
    assert any("Profile.accept() failed" in s for s in summaries), summaries


def test_explore_covers_safe_nodes_but_never_the_destructive_one():
    report = Player(ExampleSite(), new_page(), seed=1, mode=EXPLORE).run()

    assert set(report.nodes_visited) == {
        "Dashboard", "Settings", "SearchResults", "Reports", "Profile"
    }
    assert "Deleted" not in report.nodes_visited
    # the destructive edge is never traversed
    for f in report.findings:
        assert all(step["action"] != "Delete account" for step in f.path)


def test_findings_carry_a_replayable_path():
    report = Player(ExampleSite(), new_page(), seed=3, mode=EXPLORE).run()
    profile = next(f for f in report.findings if "Profile" in f.summary)
    # the path is the sequence of actions from entry that reaches the failure
    assert profile.path, "finding must record how it was reached"
    assert profile.path[-1]["action"] == "Profile"


def test_chaos_mode_reaches_the_destructive_state():
    report = Player(ExampleSiteChaos(), new_page(), seed=1, mode=CHAOS).run()
    assert "Deleted" in report.nodes_visited
    # the two real breakages are still reported, nothing spurious added
    assert len(report.findings) == 2, _summaries(report)


def test_walk_is_deterministic_for_a_fixed_seed():
    a = Player(ExampleSite(), new_page(), seed=42, mode=EXPLORE).run()
    b = Player(ExampleSite(), new_page(), seed=42, mode=EXPLORE).run()

    assert a.nodes_visited == b.nodes_visited
    assert a.actions_taken == b.actions_taken
    assert _summaries(a) == _summaries(b)


def test_healthy_site_reports_nothing():
    # Drop the two broken links from the entry so only healthy paths remain.
    from edumaze import Node

    class Home(Node):
        url = "/dashboard"

        def matches(self, page):
            return page.by_role("heading", name="Dashboard").visible()

        def options(self):
            return [self.submit("Search", fields={"Query": "text"}, to=Results)]

        def accept(self, page):
            assert page.by_role("navigation").visible()

    class Results(Node):
        url = "/search"

        def matches(self, page):
            return page.by_role("heading", name="Results").visible()

        def options(self):
            return [self.go("Back to dashboard", to=Home)]

    from edumaze import Role, Site
    from .example_maze import login_admin

    class HealthySite(Site):
        id = "healthy"
        base_url = "https://app.example.test/login"
        entry = Home
        roles = [Role("admin", login=login_admin,
                      logged_in_when=("heading", "Dashboard"))]

    report = Player(HealthySite(), new_page(), seed=5, mode=EXPLORE).run()
    assert report.ok, _summaries(report)
