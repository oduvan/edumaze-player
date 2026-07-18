"""`edumaze run path/to/maze.py` — walk a maze against a real browser.

Loads a maze module, finds its single ``Site`` subclass, walks it with the
Playwright driver, and prints a report. Baseline diff (L2) is loaded from
``--baseline` if given.
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

from .player import Player
from .policy import CHAOS, EXPLORE
from .site import Site


def _load_site(maze_path: Path) -> Site:
    spec = importlib.util.spec_from_file_location(maze_path.stem, maze_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {maze_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sites = [obj for _, obj in inspect.getmembers(module, inspect.isclass)
             if issubclass(obj, Site) and obj is not Site
             and obj.__module__ == module.__name__]
    if len(sites) != 1:
        raise SystemExit(f"expected exactly one Site subclass, found {len(sites)}")
    return sites[0]()


def _guard_prod(site: Site, mode: str) -> None:
    from urllib.parse import urlparse
    host = urlparse(site.base_url).hostname or ""
    if site.domain_allowlist and host not in site.domain_allowlist:
        raise SystemExit(f"refusing to run: {host} not in domain_allowlist")
    if mode == CHAOS and not site.reset_hook:
        raise SystemExit("refusing chaos mode without a reset_hook")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="edumaze")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="walk a maze")
    run.add_argument("maze", type=Path)
    run.add_argument("--mode", choices=[EXPLORE, CHAOS], default=EXPLORE)
    run.add_argument("--walk", choices=["coverage", "random"], default="coverage")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--baseline", type=Path, default=None)
    run.add_argument("--headed", action="store_true")

    args = ap.parse_args(argv)
    site = _load_site(args.maze)
    _guard_prod(site, args.mode)

    baseline = json.loads(args.baseline.read_text()) if args.baseline else None

    from .drivers.playwright_driver import launch
    with launch(site.base_url, headless=not args.headed) as page:
        report = Player(site, page, seed=args.seed, mode=args.mode,
                        walk=args.walk, baseline=baseline).run()

    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
