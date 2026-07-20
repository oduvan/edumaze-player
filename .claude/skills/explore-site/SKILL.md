---
name: explore-site
description: Explore a website from a URL and generate a map.py for the edumaze breakage engine — the states, their elements (informational/interactive), visibility expectations, and fuzzable forms. Use when the user gives a link and wants a map generated (the Explorer, ① in docs/architecture.md).
---

# Explore a site → write a map

You are the **Explorer** (① in `docs/architecture.md`). Given a URL, walk the site
and write `sites/<id>/map.py` in the edumaze model. You spend the tokens here so the
cheap engine can run forever. Don't guess the DOM — **probe it**.

## Tooling

Use `tools/probe.py` (real browser) to see any page as structured JSON: headings,
buttons (with `disabled`), links (with `href`), and inputs **with constraints**
(`required`, `maxlength`, `kind`).

```
python3 tools/probe.py <url>
python3 tools/probe.py <url> --viewport 390x844
python3 tools/probe.py <url> --steps '[{"fill":{"placeholder":"Name","value":"QA"}},{"click":{"name":"Create"}}]'
```

Needs Playwright. If missing:
```
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium
# then run the probe with .venv/bin/python tools/probe.py ...
```

## Process

1. **Probe the entry URL.** Also probe it at `--viewport 390x844` to see what the
   mobile layout hides.

2. **Model the entry as a `State`.** From the probe output:
   - headings and key visible text → informational elements
     (`Element(role("heading","…"), info=True)` or `Element(text("…"), info=True)`);
   - each visible button/link that goes somewhere → an interactive element
     (`Element(role("button","name"), click=Click(to=NextState))`);
   - a form → one **submit** element carrying its fields:
     `Element(role("button","Submit"), submit=Submit(fields=[Field(placeholder("…"), required=…, max_len=…, type=…)], on_valid=NextState))`.
     Read `required`/`maxlength`/`kind` straight from the probe's `inputs`.

3. **Discover and follow navigations (BFS).** For each element that changes state:
   - links → the `href` path is the target;
   - a form/create button → reach the next state by probing **with `--steps`**
     (fill valid values, click submit) and see where you land.
   Add a new `State` per distinct URL/screen. Stop when no new states appear or you
   hit a sensible budget (~8–12 states). Focus on primary flows; don't crawl forever.

4. **Set visibility expectations.**
   - Present & visible in a state → `visible=True` (the default).
   - Appears only after opening a menu/modal → model the control as
     `Element(role("button","Menu"), toggle=Toggle(reveals=[text("Item")]))` and mark
     the revealed items `visible=False` in the base state.
   - Should *not* be here (e.g. an inline error before any submit) → `visible=False`.
   - Something visible on desktop but gone in the mobile probe → still `visible=True`
     (that mismatch is a *finding* for the engine to surface, not a map fact).

5. **Make forms fuzzable.** Map each field's constraints. Set `on_valid` to the state
   a correct submit reaches (verify by probing with valid steps). Mark clearly
   destructive submits (delete / pay / deactivate) `destructive=True` so the engine
   skips them in explore mode.
   - **`maxlength` caveat**: if the probe shows an input has a DOM `maxlength`, the
     browser already prevents longer input, so do **not** set `max_len` on that
     `Field` — an over-length fuzz there can't happen and would only false-positive.
     Set `max_len` only to test a limit the DOM doesn't enforce. (Still record
     `required` and `type` — those are worth fuzzing.)

6. **Write `sites/<id>/map.py`** using the model:

   ```python
   from edumaze import (DESKTOP, MOBILE, Budgets, Click, Element, Field, Site,
                        State, Submit, Toggle, placeholder, role, text)

   class Landing(State):
       url = "/"
       def elements(self):
           return [
               Element(role("heading", "Title"), info=True),
               Element(role("button", "Create"), name="Create",
                       submit=Submit(fields=[Field(placeholder("Name"), required=True, max_len=16)],
                                     on_valid=Lobby)),
           ]

   class Lobby(State):
       url = "/room/"
       def identify(self, page):
           return "/room/" in page.url and page.by_role("heading", name="Lobby").visible()
       def elements(self):
           return [ Element(role("button", "Exit"), name="Exit", click=Click(to=Landing)) ]

   class TheSite(Site):
       id = "thesite"
       base_url = "https://…/"
       domain_allowlist = ["<host>"]
       entry = Landing
       viewports = [DESKTOP, MOBILE]
       budgets = Budgets(max_actions=40)
       seed_data = {"Name": "QA Bot"}   # valid values, keyed by field label
   ```

   Locators: prefer `role(kind, name)`; use `placeholder(...)` for inputs with no
   accessible name; `text(...)` for content. `elements()` is a **method** (so it can
   reference states defined later). For an SPA where the URL doesn't change per
   screen, override `identify()` with a content check.

7. **Validate.** Run `edumaze run sites/<id>/map.py --seed 1` (via the venv if the
   package isn't installed). If a state won't resolve, fix its `url`/`identify`. A
   clean run — or plausible breakage cases — means the map is coherent. Iterate.

## Safety

- **Third-party sites**: interact read-only. Never submit destructive forms (mark
  them `destructive=True`), never create real accounts/leads, set `domain_allowlist`
  to the site's host. When in doubt, model a form's fields but leave `on_valid=None`
  so the engine won't complete it.
- **The user's own staging**: fuller interaction is fine.

## Output

The single deliverable is `sites/<id>/map.py`. Report the states you found, the
forms/toggles you modeled, and the result of the validation run.
