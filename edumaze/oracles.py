"""Oracles — the definitions of 'not working'.

L1 runs live during the walk (technical signals + each node's ``accept``).
L2 is differential and runs once against the committed baseline (see
:mod:`edumaze.materialize`).
"""
from __future__ import annotations

from typing import List, Optional

from .materialize import diff
from .node import Node
from .page import Page
from .report import Finding
from .site import Site


def technical(page: Page, node_name: Optional[str]) -> List[Finding]:
    """L1 technical: HTTP errors and uncaught console errors."""
    findings: List[Finding] = []
    status = page.status
    if status is not None and status >= 400:
        findings.append(Finding(
            oracle="L1", node=node_name,
            severity_hint="high" if status >= 500 else "med",
            summary=f"HTTP {status} on {page.url}",
            evidence={"http_status": status, "url": page.url},
        ))
    errors = page.console_errors
    if errors:
        findings.append(Finding(
            oracle="L1", node=node_name, severity_hint="med",
            summary=f"{len(errors)} console error(s) on {page.url}",
            evidence={"console": errors, "url": page.url},
        ))
    return findings


def acceptance(node: Node, page: Page) -> Optional[Finding]:
    """L1 node acceptance: run the node's declared criteria."""
    try:
        node.accept(page)
        return None
    except AssertionError as exc:
        msg = str(exc) or "assertion failed"
        return Finding(oracle="L1", node=node.name, severity_hint="high",
                       summary=f"{node.name}.accept() failed: {msg}",
                       evidence={"url": page.url})
    except Exception as exc:  # noqa: BLE001 - a crashing check is itself a finding
        return Finding(oracle="L1", node=node.name, severity_hint="high",
                       summary=f"{node.name}.accept() raised "
                               f"{type(exc).__name__}: {exc}",
                       evidence={"url": page.url})


def differential(site: Site, baseline: dict, current: dict) -> List[Finding]:
    """L2 differential: structural drift vs the committed baseline."""
    findings: List[Finding] = []
    for change in diff(baseline, current):
        findings.append(Finding(
            oracle="L2",
            node=change[1] if len(change) > 1 else None,
            severity_hint="med",
            summary="maze drift: " + " ".join(str(c) for c in change),
            evidence={"change": list(change)},
        ))
    return findings
