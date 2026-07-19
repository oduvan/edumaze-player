"""End-to-end: the engine stress-tests the example map against the fake app."""
from __future__ import annotations

from edumaze import Engine

from .example_map import Example, new_page


def _run(**kw):
    return Engine(Example(), new_page(), **kw).run()


def test_reports_exactly_the_two_planted_defects():
    report = _run()
    sigs = sorted(c.signature for c in report.cases)

    assert sigs == [
        "Lobby|do|Save|viewport=desktop",       # disabled button, both viewports
        "Lobby|do|Save|viewport=mobile",
        "Lobby|see|Desktop Banner|viewport=mobile",  # hidden only on mobile
    ], sigs


def test_visits_both_states_at_both_viewports():
    report = _run()
    assert set(report.states_checked) == {"Landing", "Lobby"}
    assert report.configs_run == 2  # desktop + mobile


def test_cases_carry_replay_steps_and_config():
    report = _run()
    banner = next(c for c in report.cases if c.target == "Desktop Banner")
    assert banner.kind == "see"
    assert banner.config["viewport"] == "mobile"
    # reachable from entry by creating a game
    assert banner.steps == [{"action": "Create"}]


def test_healthy_form_and_toggle_produce_no_findings():
    # Landing's create form and Lobby's Menu→Settings toggle are correct, so
    # none of them show up as cases.
    report = _run()
    targets = {c.target for c in report.cases}
    assert "Create" not in targets   # valid submits + graceful invalids
    assert "Menu" not in targets      # toggle reveals Settings correctly


def test_suppression_hides_a_signature():
    report = Engine(Example(), new_page(),
                    suppressions={"Lobby|see|Desktop Banner|viewport=mobile"}).run()
    sigs = {c.signature for c in report.cases}
    assert "Lobby|see|Desktop Banner|viewport=mobile" not in sigs
    assert "Lobby|do|Save|viewport=mobile" in sigs   # others still reported
