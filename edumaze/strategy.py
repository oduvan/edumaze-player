"""Walk strategy: seeded, coverage-guided, with a pure-random mode.

Determinism contract: same seed + same maze => same sequence of choices. The RNG
is the *only* source of nondeterminism, so a reported walk always replays.
"""
from __future__ import annotations

import random
from typing import List, Optional, Set, Tuple

from .node import Option

Edge = Tuple[str, str]  # (node_name, option_label)


class Strategy:
    def __init__(self, seed: int, mode: str = "coverage") -> None:
        self.rng = random.Random(seed)
        self.mode = mode
        self.visited: Set[Edge] = set()

    def choose(self, node_name: str, options: List[Option]) -> Optional[Option]:
        """Pick the next option (already safety-filtered) or None if there is
        no *unvisited* edge here. Returning None hands control back to the
        player, which backtracks to the entry to reach unexplored edges."""
        if not options:
            return None
        if self.mode == "random":
            # pure chaos: any edge, revisits allowed
            choice = self.rng.choice(_stable(options))
            self.visited.add((node_name, choice.label))
            return choice

        unvisited = [o for o in options if (node_name, o.label) not in self.visited]
        if not unvisited:
            return None
        choice = self.rng.choice(_stable(unvisited))
        self.visited.add((node_name, choice.label))
        return choice

    def mark(self, node_name: str, label: str) -> None:
        self.visited.add((node_name, label))


def _stable(options: List[Option]) -> List[Option]:
    # rng.choice depends on order; sort by label so the seed fully determines it.
    return sorted(options, key=lambda o: o.label)
