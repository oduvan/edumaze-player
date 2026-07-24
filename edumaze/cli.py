"""`edumaze run path/to/map.py` — stress-test a site against a real browser.

Loads a map module, finds its single ``Site`` subclass, runs the engine with the
Playwright driver, and prints the breakage report. An optional suppression file
(one signature per line) lets triage-dismissed cases stay dismissed.
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

from .engine import Engine
from .model import Site


def _load_site(map_path: Path) -> Site:
    spec = importlib.util.spec_from_file_location(map_path.stem, map_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {map_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sites = [obj for _, obj in inspect.getmembers(module, inspect.isclass)
             if issubclass(obj, Site) and obj is not Site
             and obj.__module__ == module.__name__]
    if len(sites) != 1:
        raise SystemExit(f"expected exactly one Site subclass, found {len(sites)}")
    return sites[0]()


def _guard(site: Site, mode: str) -> None:
    from urllib.parse import urlparse
    host = urlparse(site.base_url).hostname or ""
    if site.domain_allowlist and host not in site.domain_allowlist:
        raise SystemExit(f"refusing to run: {host} not in domain_allowlist")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="edumaze")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="stress-test a site")
    run.add_argument("map", type=Path)
    run.add_argument("--mode", choices=["explore", "chaos"], default="explore")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--suppress", type=Path, default=None,
                     help="file of signatures to skip (one per line)")
    run.add_argument("--headed", action="store_true")

    args = ap.parse_args(argv)
    site = _load_site(args.map)
    _guard(site, args.mode)

    suppressions = set()
    if args.suppress and args.suppress.exists():
        suppressions = {ln.strip() for ln in args.suppress.read_text().splitlines()
                        if ln.strip() and not ln.startswith("#")}

    import time
    from .drivers.playwright_driver import launch
    t0 = time.perf_counter()
    with launch(site.base_url, headless=not args.headed) as page:
        report = Engine(site, page, seed=args.seed, mode=args.mode,
                        suppressions=suppressions).run()

    out = report.to_dict()
    out["duration_ms"] = int((time.perf_counter() - t0) * 1000)
    out["suppressed_signatures"] = len(suppressions)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 1 if report.cases else 0


if __name__ == "__main__":
    sys.exit(main())
