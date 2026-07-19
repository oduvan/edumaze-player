# -*- coding: utf-8 -*-
"""A map for https://edumaze.lyabah.com/ ("Лабіринт Знань") in the v2 model.

Read/interact only. Covers the entry flow: the landing screen (with the
create-game form) and the room lobby it leads to. The name input uses a curly
apostrophe (U+2019): "Твоє ім’я".
"""
from edumaze import (DESKTOP, MOBILE, Budgets, Click, Element, Field, Site,
                     State, Submit, placeholder, role, text)

NAME_PH = "Твоє ім’я"  # U+2019


class Landing(State):
    url = "/"

    def elements(self):
        return [
            Element(role("heading", "ЛАБІРИНТ ЗНАНЬ"), info=True),
            Element(role("button", "Увійти"), name="Join", info=True),
            Element(role("button", "Створити гру"), name="Create game",
                    submit=Submit(fields=[Field(placeholder(NAME_PH), required=True)],
                                  on_valid=Lobby)),
        ]


class Lobby(State):
    url = "/room/"

    def identify(self, page):
        return "/room/" in page.url and page.by_role("heading", name="Лобі").visible()

    def elements(self):
        return [
            Element(role("heading", "Лобі"), info=True),
            Element(text("КОД КІМНАТИ"), info=True),
            Element(role("button", "Вийти"), name="Exit", click=Click(to=Landing)),
        ]


class EduMaze(Site):
    id = "edumaze"
    base_url = "https://edumaze.lyabah.com/"
    domain_allowlist = ["edumaze.lyabah.com"]
    entry = Landing
    viewports = [DESKTOP, MOBILE]
    budgets = Budgets(max_actions=40)
    seed_data = {NAME_PH: "QA Bot"}
