"""Placeholder-targeted form fields — the locator strategy real inputs need.

Many real inputs expose no accessible role-name, only a placeholder (this is
exactly what the live edumaze site does), so a maze must be able to fill by
placeholder.
"""
from __future__ import annotations

from edumaze import EXPLORE, Locator, Node, Player, Site
from edumaze.drivers.fake import FakeElement, FakePage, FakeSite, FakeState


class Start(Node):
    url = "/"

    def matches(self, page):
        return page.by_role("heading", name="Start").visible()

    def options(self):
        return [self.submit("Create",
                            fields={Locator.placeholder("Your name"): "name"},
                            button="Create", to=Done)]


class Done(Node):
    url = "/done"

    def matches(self, page):
        return page.by_role("heading", name="Done").visible()

    def accept(self, page):
        assert page.by_role("heading", name="Done").visible()


class PlaceholderSite(Site):
    base_url = "/"
    entry = Start
    seed_data = {"name": "QA Bot"}


def _fake():
    return FakePage(FakeSite([
        FakeState("Start", "/", [
            FakeElement("heading", "Start"),
            FakeElement("textbox", placeholder="Your name"),
            FakeElement("button", "Create", on_click="Done"),
        ]),
        FakeState("Done", "/done", [FakeElement("heading", "Done")]),
    ], start="Start"))


def test_by_placeholder_finds_the_field():
    page = _fake()
    assert page.by_placeholder("Your name").visible()
    assert not page.by_placeholder("Nope").visible()


def test_submit_fills_a_placeholder_field_and_advances():
    page = _fake()
    report = Player(PlaceholderSite(), page, seed=0, mode=EXPLORE).run()

    assert report.ok, [f.summary for f in report.findings]
    assert "Done" in report.nodes_visited
    # the seeded value was actually typed into the placeholder field
    assert page._fills[("textbox", "")] == "QA Bot"
