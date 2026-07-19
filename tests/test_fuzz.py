"""Form fuzzing catches a submit that accepts invalid input."""
from __future__ import annotations

from edumaze import (DESKTOP, Budgets, Element, Engine, Field, Site, State,
                     Submit, placeholder, role, text)
from edumaze.drivers.fake import FakeElement, FakePage, FakeSite, FakeState


class Form(State):
    url = "/"

    def elements(self):
        return [Element(role("button", "Go"), name="Go",
                        submit=Submit(fields=[Field(placeholder("Email"),
                                                    required=True)],
                                      on_valid=Done))]


class Done(State):
    url = "/done"

    def elements(self):
        return [Element(text("Done"), info=True)]


class FormSite(Site):
    id = "formsite"
    base_url = "/"
    entry = Form
    viewports = [DESKTOP]          # one config is enough for these tests
    budgets = Budgets(max_actions=200)


def _page(good: bool):
    # good: "Go" requires a non-empty Email before navigating.
    # buggy: "Go" navigates unconditionally (accepts empty required field).
    go = FakeElement(role="button", name="Go", on_click="Done",
                     requires=("Email",) if good else ())
    return FakePage(FakeSite([
        FakeState("Form", "/", [FakeElement(placeholder="Email"), go]),
        FakeState("Done", "/done", [FakeElement(text="Done")]),
    ], start="Form"))


def test_fuzzer_flags_accepted_empty_required_field():
    report = Engine(FormSite(), _page(good=False)).run()
    empties = [c for c in report.cases
               if c.kind == "do" and "empty-required" in c.config.get("input", "")]
    assert empties, [c.to_dict() for c in report.cases]
    assert empties[0].target == "Go"


def test_good_form_has_no_fuzz_findings():
    report = Engine(FormSite(), _page(good=True)).run()
    assert report.ok, [c.to_dict() for c in report.cases]
