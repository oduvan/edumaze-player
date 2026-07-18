# -*- coding: utf-8 -*-
"""A real maze for https://edumaze.lyabah.com/ ("Лабіринт Знань").

Hand-written from exploring the live site. Covers the core entry flow:
the landing screen, creating a game (which routes to /room/<code>), and the
lobby — plus leaving the lobby back to the landing screen.

Written against the live SPA, so a couple of real-world facts shaped it:
- the name/code inputs have no accessible role-name, only placeholders, so we
  target them with ``Locator.placeholder(...)``;
- the name placeholder uses a curly apostrophe (U+2019): "Твоє ім’я".
"""
from edumaze import Budgets, Locator, Node, Site

NAME_PLACEHOLDER = "Твоє ім’я"  # note: U+2019, not a straight apostrophe


class Landing(Node):
    """The entry screen: enter a name and create a game, or join by code."""

    url = "/"

    def matches(self, page):
        return ("/room/" not in page.url
                and page.by_role("heading", name="ЛАБІРИНТ ЗНАНЬ").visible())

    def options(self):
        return [
            self.submit(
                "Створити гру",
                fields={Locator.placeholder(NAME_PLACEHOLDER): "name"},
                button="Створити гру",
                to=Lobby,
            ),
        ]

    def accept(self, page):
        assert page.by_role("button", name="Створити гру").visible(), \
            "create-game button missing"
        assert page.by_role("button", name="Увійти").visible(), \
            "join button missing"


class Lobby(Node):
    """The room lobby after creating a game."""

    url = "/room/"

    def matches(self, page):
        return "/room/" in page.url and page.by_role("heading", name="Лобі").visible()

    def options(self):
        return [self.go("Вийти", to=Landing, role="button")]

    def accept(self, page):
        assert page.by_role("heading", name="Лобі").visible(), \
            "lobby heading missing"
        assert page.by_text("КОД КІМНАТИ").visible(), \
            "room-code panel missing"


class EduMaze(Site):
    id = "edumaze"
    base_url = "https://edumaze.lyabah.com/"
    domain_allowlist = ["edumaze.lyabah.com"]
    entry = Landing
    roles = []  # anonymous; no login
    budgets = Budgets(max_actions=8)
    seed_data = {"name": "QA Bot"}
