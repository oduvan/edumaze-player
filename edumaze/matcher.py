"""Resolve a live page to the declared node that describes it."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Type

from .node import Node
from .page import Page


@dataclass
class Match:
    node: Optional[Type[Node]]        # the single matching node, or None
    candidates: List[str]             # names of *all* nodes that claimed the page

    @property
    def unmatched(self) -> bool:
        return self.node is None and not self.candidates

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1


def resolve(page: Page, node_classes: List[Type[Node]]) -> Match:
    hits = [nc for nc in node_classes if _safe_matches(nc, page)]
    names = [nc.__name__ for nc in hits]
    node = hits[0] if len(hits) == 1 else None
    return Match(node=node, candidates=names)


def _safe_matches(nc: Type[Node], page: Page) -> bool:
    try:
        return bool(nc().matches(page))
    except Exception:
        # A matcher that throws simply doesn't match; never abort the walk.
        return False
