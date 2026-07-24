# edumaze-player

A deterministic **breakage-hunter** for websites. Given a **map** of a site, it
varies configurations — viewport sizes, form inputs, menu toggles, navigation
paths — and reports the conditions under which something breaks.

One skill drives the whole loop; a cheap deterministic engine does the grinding
(see [`docs/architecture.md`](docs/architecture.md)):

- **`/check-site <url>`** — the skill: build the map (or reuse it), run the engine,
  triage results into real vs. false, report findings + statistics, and self-heal
  (fix the map or an engine module, suppress confirmed-false cases). Tokens are
  spent only on building the map and triaging — not on running it.
- **The engine** — cheap & deterministic; stress-tests the map (viewports, form
  fuzzing, toggles) and emits **breakage cases** with signatures.
- **`tools/probe.py`** — dumps any page's structure (elements + form constraints)
  so the skill can build the map without guessing.

## The map

One `State` per page; one list of `Element`s per state. Every element carries a
visible/hidden expectation and may be informational, interactive, or both.

```python
from edumaze import State, Element, Submit, Field, Toggle, Click, role, text, placeholder

class Lobby(State):
    url = "/lobby"
    def elements(self):
        return [
            Element(text("Room"), info=True),                        # must be visible
            Element(role("button", "Menu"),                          # interactive toggle
                    toggle=Toggle(reveals=[text("Settings")])),
            Element(text("Settings"), visible=False),                # hidden until menu opens
            Element(role("button", "Create"),                        # a fuzzable form
                    submit=Submit(fields=[Field(placeholder("Name"), required=True, max_len=20)],
                                  on_valid=Game)),
        ]
```

## What it checks (the oracle)

- **See** — every element's actual visibility matches its expectation.
- **Do** — every interactive element is usable and does what it's declared to do
  (links navigate, toggles reveal/hide, valid submits succeed, invalid submits
  fail gracefully).
- **Signals** — dead links, JS/HTTP errors, slow loads.

…run across each **viewport**, with **form fuzzing** on every submit.

## Output

Breakage cases, each `state + config + failed check + replay steps`, tagged with a
**signature** (`state | see/do/signal | target | config`) so triage can dismiss or
fix a whole group at once.

## Run

```bash
python3 -m pytest -q                       # browser-free tests (fake driver)

pip install -e ".[playwright]" && playwright install chromium
edumaze run path/to/map.py --seed 1        # against a real browser
edumaze run path/to/map.py --suppress known.txt   # skip triage-dismissed signatures
```
