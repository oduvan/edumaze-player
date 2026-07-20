#!/usr/bin/env python3
"""Probe a page's structure for the Explorer skill.

Given a URL (and optional steps to reach a deeper state), it renders the page in
a real browser and prints, as JSON, everything needed to write a map entry for
that state: headings, buttons (with disabled state), links (with hrefs), and form
inputs **with their constraints** (type / required / maxlength) read straight
from the DOM.

Usage:
    probe.py <url>
    probe.py <url> --steps '[{"fill":{"placeholder":"Name","value":"QA"}},
                             {"click":{"name":"Create"}}]'

Steps run in order before the dump; each is one of:
    {"goto": "<url>"}
    {"fill": {"placeholder": "<ph>", "value": "<v>"}}
    {"click": {"name": "<accessible name>"}}     # button or link, visible match
"""
import argparse
import json
import sys

from playwright.sync_api import sync_playwright

DUMP_JS = r"""
() => {
  const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const t = e => (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().replace(/\s+/g,' ').slice(0,80);
  const uniq = (arr, key) => { const s=new Set(), o=[]; for (const x of arr){const k=key(x); if(!s.has(k)){s.add(k);o.push(x);}} return o; };

  const headings = uniq([...document.querySelectorAll('h1,h2,h3,[role=heading]')]
      .filter(vis).map(e => ({tag: e.tagName.toLowerCase(), text: t(e)})).filter(h=>h.text), h=>h.text);

  const buttons = uniq([...document.querySelectorAll('button,[role=button],input[type=submit],input[type=button]')]
      .map(e => ({name: t(e), disabled: e.disabled === true || e.getAttribute('aria-disabled')==='true', visible: vis(e)}))
      .filter(b=>b.name), b=>b.name);

  const links = uniq([...document.querySelectorAll('a[href]')]
      .map(e => ({text: t(e), href: e.getAttribute('href'), visible: vis(e)}))
      .filter(l=>l.text), l=>l.text+'|'+l.href);

  const inputs = [...document.querySelectorAll('input,textarea,select')]
      .filter(e => (e.type||'') !== 'hidden')
      .map(e => ({
        kind: (e.tagName.toLowerCase()==='input') ? (e.getAttribute('type')||'text') : e.tagName.toLowerCase(),
        placeholder: e.getAttribute('placeholder') || '',
        name: e.getAttribute('name') || e.getAttribute('aria-label') || e.id || '',
        required: e.required === true || e.getAttribute('aria-required')==='true',
        maxlength: e.getAttribute('maxlength'),
        visible: vis(e),
      }));

  return {headings, buttons, links, inputs};
}
"""


def dismiss(page):
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    for sel in ("[class*='om-close']", "[id^='om-'] button",
                "button[aria-label*='close' i]", "#onetrust-accept-btn-handler"):
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 3)):
                if loc.nth(i).is_visible():
                    loc.nth(i).click(timeout=1000, force=True)
        except Exception:
            pass


def click_by_name(page, name):
    loc = page.get_by_role("button", name=name)
    if loc.count() == 0:
        loc = page.get_by_role("link", name=name)
    for i in range(min(loc.count(), 25)):
        el = loc.nth(i)
        try:
            if not el.is_visible():
                continue
            el.evaluate("e => e.scrollIntoView({block:'center'})")
            el.click(timeout=4000)
            return
        except Exception:
            continue
    raise RuntimeError(f"could not click {name!r}")


def run(url, steps, viewport):
    with sync_playwright() as pw:
        page = pw.chromium.launch(headless=True).new_page()
        if viewport:
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        resp = page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1200)
        dismiss(page)
        for step in steps:
            if "goto" in step:
                resp = page.goto(step["goto"], wait_until="networkidle")
            elif "fill" in step:
                page.get_by_placeholder(step["fill"]["placeholder"]).first.fill(step["fill"]["value"])
            elif "click" in step:
                click_by_name(page, step["click"]["name"])
            page.wait_for_timeout(1200)
        data = page.evaluate(DUMP_JS)
        data["url"] = page.url
        data["title"] = page.title()
        data["status"] = resp.status if resp else None
        return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--steps", default="[]", help="JSON list of steps to reach a state")
    ap.add_argument("--viewport", default="", help="WIDTHxHEIGHT, e.g. 390x844")
    args = ap.parse_args()
    vp = None
    if args.viewport:
        w, h = args.viewport.lower().split("x")
        vp = (int(w), int(h))
    data = run(args.url, json.loads(args.steps), vp)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
