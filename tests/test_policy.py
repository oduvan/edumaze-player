"""Safety policy: mode gating, reset-hook requirement, denylist, boundaries."""
from __future__ import annotations

from edumaze import DESTRUCTIVE, EXTERNAL, Node, Site
from edumaze.policy import CHAOS, EXPLORE, allowed


class _N(Node):
    pass


N = _N()
SAFE_OPT = N.go("Settings")
DESTRUCTIVE_OPT = N.go("Delete", classify=DESTRUCTIVE)
EXTERNAL_OPT = N.external("Pay with PayPal")


class _Plain(Site):
    pass


class _WithReset(Site):
    reset_hook = {"method": "POST", "url": "/reset"}


class _WithDenylist(Site):
    denylist = ["*logout*", "Delete"]


def test_safe_edge_always_allowed():
    ok, _ = allowed(SAFE_OPT, _Plain(), EXPLORE)
    assert ok


def test_destructive_blocked_in_explore():
    ok, reason = allowed(DESTRUCTIVE_OPT, _WithReset(), EXPLORE)
    assert not ok and "explore" in reason


def test_destructive_needs_reset_hook_even_in_chaos():
    ok, reason = allowed(DESTRUCTIVE_OPT, _Plain(), CHAOS)
    assert not ok and "reset_hook" in reason


def test_destructive_allowed_in_chaos_with_reset_hook():
    ok, _ = allowed(DESTRUCTIVE_OPT, _WithReset(), CHAOS)
    assert ok


def test_external_never_traversed():
    ok, reason = allowed(EXTERNAL_OPT, _WithReset(), CHAOS)
    assert not ok and "external" in reason


def test_denylist_wins():
    ok, reason = allowed(N.go("Delete"), _WithDenylist(), EXPLORE)
    assert not ok and reason == "denylist"
