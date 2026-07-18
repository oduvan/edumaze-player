"""Materialize the declared maze and diff it — the L2 baseline mechanism."""
from __future__ import annotations

import copy

from edumaze import diff, materialize

from .example_maze import ExampleSite


def test_materialize_captures_nodes_and_options():
    g = materialize(ExampleSite())
    nodes = g["nodes"]

    assert set(nodes) == {
        "Dashboard", "Settings", "SearchResults", "Reports", "Profile", "Deleted"
    }
    dash_labels = {o["label"] for o in nodes["Dashboard"]["options"]}
    assert dash_labels == {"Settings", "Reports", "Profile", "Search"}

    delete = nodes["Settings"]["options"][0]
    assert delete["label"] == "Delete account"
    assert delete["classify"] == "destructive"
    assert delete["to"] == "Deleted"


def test_diff_is_empty_for_identical_graphs():
    g = materialize(ExampleSite())
    assert diff(g, copy.deepcopy(g)) == []


def test_diff_detects_a_removed_option():
    base = materialize(ExampleSite())
    current = copy.deepcopy(base)
    current["nodes"]["Dashboard"]["options"] = [
        o for o in current["nodes"]["Dashboard"]["options"] if o["label"] != "Reports"
    ]
    assert ("option_removed", "Dashboard", "Reports") in diff(base, current)


def test_diff_detects_a_removed_node():
    base = materialize(ExampleSite())
    current = copy.deepcopy(base)
    del current["nodes"]["Profile"]
    assert ("node_removed", "Profile") in diff(base, current)


def test_diff_detects_retarget_and_reclassify():
    base = materialize(ExampleSite())
    current = copy.deepcopy(base)
    delete = current["nodes"]["Settings"]["options"][0]
    delete["to"] = "Dashboard"
    delete["classify"] = "safe"
    changes = diff(base, current)
    assert ("option_retargeted", "Settings", "Delete account", "Deleted", "Dashboard") in changes
    assert ("option_reclassified", "Settings", "Delete account", "destructive", "safe") in changes
