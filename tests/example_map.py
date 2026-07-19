"""A hand-written map + a matching in-memory site to stress-test it.

The map is deliberately paired with a fake app that has two planted defects, so
the engine's checks have something real to catch:

- Lobby's "Desktop Banner" is expected visible but is **hidden on mobile**  → a
  See failure, only at the mobile viewport.
- Lobby's "Save" button is present but **disabled**                        → a Do
  failure, at every viewport.

Everything else (the create form, the Menu→Settings toggle, navigation) is
healthy, so a correct engine reports exactly those and nothing more.
"""
from __future__ import annotations

from edumaze import (Budgets, Click, Element, Field, Site, State, Submit, Toggle,
                     placeholder, role, text)
from edumaze.drivers.fake import FakeElement, FakePage, FakeSite, FakeState


# --------------------------------------------------------------------------
# The map
# --------------------------------------------------------------------------
class Landing(State):
    url = "/"

    def elements(self):
        return [
            Element(text("Welcome"), info=True),
            Element(role("button", "Create"), name="Create",
                    submit=Submit(fields=[Field(placeholder("Name"),
                                                required=True, max_len=20)],
                                  on_valid=Lobby)),
        ]


class Lobby(State):
    url = "/lobby"

    def elements(self):
        return [
            Element(text("Room"), info=True),
            Element(role("button", "Menu"), name="Menu",
                    toggle=Toggle(reveals=[text("Settings")])),
            Element(text("Settings"), visible=False),          # hidden until menu opens
            Element(role("button", "Save"), name="Save",
                    click=Click(to=Lobby)),                    # planted: disabled
            Element(text("Desktop Banner"), info=True),        # planted: hidden on mobile
            Element(role("button", "Exit"), name="Exit", click=Click(to=Landing)),
        ]


class Example(Site):
    id = "example"
    base_url = "/"
    entry = Landing
    budgets = Budgets(max_actions=200)


# --------------------------------------------------------------------------
# The simulated app
# --------------------------------------------------------------------------
def build_fake() -> FakeSite:
    return FakeSite([
        FakeState("Landing", "/", [
            FakeElement(text="Welcome"),
            FakeElement(placeholder="Name"),
            FakeElement(role="button", name="Create", on_click="Lobby",
                        requires=("Name",), max_lens={"Name": 20}),
        ]),
        FakeState("Lobby", "/lobby", [
            FakeElement(text="Room"),
            FakeElement(role="button", name="Menu", is_toggle=True),
            FakeElement(text="Settings", revealed_by="Menu"),   # hidden until Menu
            FakeElement(role="button", name="Save", enabled=False, on_click="Lobby"),
            FakeElement(text="Desktop Banner", hidden_on=("mobile",)),
            FakeElement(role="button", name="Exit", on_click="Landing"),
        ]),
    ], start="Landing")


def new_page() -> FakePage:
    return FakePage(build_fake())
