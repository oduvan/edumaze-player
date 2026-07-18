"""Turn a declared maze into a normalized data structure, and diff two of them.

The maze is *code*, so we can't text-diff it meaningfully. Instead we materialize
the declared structure into a plain dict and diff that. This is the L2
differential oracle's baseline representation.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .site import Site


def materialize(site: Site) -> dict:
    """Declared maze -> normalized dict (stable, JSON-serializable)."""
    nodes: Dict[str, dict] = {}
    for nc in site.nodes():
        opts = nc().options()
        nodes[nc.__name__] = {
            "url": nc.url,
            "options": [
                {
                    "label": o.label,
                    "kind": o.kind,
                    "to": o.target_name,
                    "classify": o.classify,
                }
                # sort for a canonical, order-independent representation
                for o in sorted(opts, key=lambda o: o.label)
            ],
        }
    return {"site_id": site.site_id, "nodes": nodes}


# A change is a tuple whose first element is its type; kept simple and
# assertion-friendly for tests and the triage skill.
Change = Tuple


def diff(baseline: dict, current: dict) -> List[Change]:
    """Structural diff of two materialized mazes. Empty list == identical."""
    changes: List[Change] = []
    bn: Dict[str, dict] = baseline.get("nodes", {})
    cn: Dict[str, dict] = current.get("nodes", {})

    for name in sorted(set(bn) - set(cn)):
        changes.append(("node_removed", name))
    for name in sorted(set(cn) - set(bn)):
        changes.append(("node_added", name))

    for name in sorted(set(bn) & set(cn)):
        bopts = {o["label"]: o for o in bn[name]["options"]}
        copts = {o["label"]: o for o in cn[name]["options"]}
        for lbl in sorted(set(bopts) - set(copts)):
            changes.append(("option_removed", name, lbl))
        for lbl in sorted(set(copts) - set(bopts)):
            changes.append(("option_added", name, lbl))
        for lbl in sorted(set(bopts) & set(copts)):
            if bopts[lbl]["to"] != copts[lbl]["to"]:
                changes.append(("option_retargeted", name, lbl,
                                 bopts[lbl]["to"], copts[lbl]["to"]))
            if bopts[lbl]["classify"] != copts[lbl]["classify"]:
                changes.append(("option_reclassified", name, lbl,
                                 bopts[lbl]["classify"], copts[lbl]["classify"]))
    return changes
