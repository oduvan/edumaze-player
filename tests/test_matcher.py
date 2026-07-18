"""State resolution: unmatched (undocumented) and ambiguous states."""
from __future__ import annotations

from edumaze import EXPLORE, Node, Player, Role, Site
from edumaze import matcher
from edumaze.drivers.fake import FakeElement, FakePage, FakeSite, FakeState


class _A(Node):
    url = "/x"


class _B(Node):
    url = "/x"          # deliberately collides with _A


class _C(Node):
    url = "/y"


def _page_at(url: str) -> FakePage:
    site = FakeSite([FakeState("s", url, [])], start="s")
    return FakePage(site)


def test_unique_match():
    m = matcher.resolve(_page_at("/y"), [_A, _B, _C])
    assert m.node is _C
    assert not m.ambiguous and not m.unmatched


def test_no_match_is_unmatched():
    m = matcher.resolve(_page_at("/zzz"), [_A, _B, _C])
    assert m.unmatched
    assert m.node is None


def test_two_nodes_claiming_a_page_is_ambiguous():
    m = matcher.resolve(_page_at("/x"), [_A, _B, _C])
    assert m.ambiguous
    assert m.node is None
    assert set(m.candidates) == {"_A", "_B"}


def test_player_reports_an_undocumented_state():
    # The maze thinks "Explore" leads back Home, but the app navigates to a
    # state no node describes.
    class Home(Node):
        url = "/home"

        def matches(self, page):
            return page.by_role("heading", name="Home").visible()

        def options(self):
            return [self.go("Explore", to=Home)]

    class Ghosts(Site):
        base_url = "/home"
        entry = Home
        roles = []

    fake = FakeSite([
        FakeState("Home", "/home", [
            FakeElement("heading", "Home"),
            FakeElement("link", "Explore", on_click="Ghost"),
        ]),
        FakeState("Ghost", "/ghost", [FakeElement("heading", "Boo")]),
    ], start="Home")

    report = Player(Ghosts(), FakePage(fake), seed=0, mode=EXPLORE).run()
    assert any("undocumented state" in f.summary for f in report.findings), \
        [f.summary for f in report.findings]
