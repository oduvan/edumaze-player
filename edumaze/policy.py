"""Safety policy: which options may be traversed, in which mode.

Designed to be safe even when the site declares no reset hook — the default
``explore`` mode only ever touches ``safe`` edges.
"""
from __future__ import annotations

from fnmatch import fnmatch
from typing import Tuple

from .node import DESTRUCTIVE, EXTERNAL, Option
from .site import Site

EXPLORE = "explore"
CHAOS = "chaos"


def allowed(option: Option, site: Site, mode: str) -> Tuple[bool, str]:
    """Return (permitted, reason_if_denied)."""
    if _denylisted(option, site):
        return False, "denylist"
    if option.classify == EXTERNAL:
        return False, "external boundary"
    if option.classify == DESTRUCTIVE:
        if mode != CHAOS:
            return False, "destructive (explore mode)"
        if not site.reset_hook:
            return False, "destructive without reset_hook"
        return True, ""
    return True, ""


def _denylisted(option: Option, site: Site) -> bool:
    targets = [option.label]
    if option.target_name:
        targets.append(option.target_name)
    if option.locator and option.locator.name:
        targets.append(option.locator.name)
    for pattern in site.denylist:
        for t in targets:
            if fnmatch(t, pattern):
                return True
    return False
