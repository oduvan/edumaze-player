"""edumaze — model a web app as a maze, walk it, report what's broken.

Public API for maze scripts:

    from edumaze import Node, Site, Role, Budgets

and, for testing a maze without a browser:

    from edumaze.drivers.fake import FakeSite, FakeState, FakeElement, FakePage
"""
from .budgets import Budgets
from .materialize import diff, materialize
from .node import DESTRUCTIVE, EXTERNAL, SAFE, Locator, Node, Option
from .page import Element, ElementNotFound, Page
from .player import Player
from .policy import CHAOS, EXPLORE
from .report import Finding, Report
from .role import Role
from .site import Site

__all__ = [
    "Node", "Site", "Role", "Budgets", "Option", "Locator",
    "Player", "Report", "Finding",
    "Page", "Element", "ElementNotFound",
    "materialize", "diff",
    "SAFE", "DESTRUCTIVE", "EXTERNAL", "EXPLORE", "CHAOS",
]
