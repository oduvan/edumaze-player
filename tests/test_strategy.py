"""Walk strategy: coverage preference and seed determinism."""
from __future__ import annotations

from edumaze.node import Node
from edumaze.strategy import Strategy


class _N(Node):
    def options(self):
        return [self.go("A"), self.go("B"), self.go("C")]


OPTS = _N().options()


def test_prefers_unvisited_then_returns_none_when_exhausted():
    s = Strategy(seed=0)
    picked = []
    for _ in range(3):
        opt = s.choose("N", OPTS)
        assert opt is not None
        picked.append(opt.label)
    # all three distinct edges taken before any repeat
    assert sorted(picked) == ["A", "B", "C"]
    # nothing unvisited left -> None (hands control back to the player)
    assert s.choose("N", OPTS) is None


def test_same_seed_same_sequence():
    s1, s2 = Strategy(seed=99), Strategy(seed=99)
    seq1 = [s1.choose("N", OPTS).label for _ in range(3)]
    seq2 = [s2.choose("N", OPTS).label for _ in range(3)]
    assert seq1 == seq2


def test_random_mode_never_starves():
    s = Strategy(seed=7, mode="random")
    # revisits are allowed, so it always returns a choice
    assert all(s.choose("N", OPTS) is not None for _ in range(20))
