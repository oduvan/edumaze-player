from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from .page import Page


@dataclass
class Role:
    """An authenticated identity plus how to become it.

    ``login`` is a recipe that receives a :class:`Page` and drives it to a
    logged-in state (navigate, fill, click). ``logged_in_when`` is an optional
    ``(role, name)`` sanity check asserted right after login.
    """

    name: str
    login: Optional[Callable[[Page], None]] = None
    logged_in_when: Optional[Tuple[str, str]] = None
