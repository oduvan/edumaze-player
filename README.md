# edumaze-player

A deterministic **breakage-hunter** for websites. Given a **map** of a site, it
varies configurations — viewport sizes, form inputs, menu toggles, navigation
paths — and reports the conditions under which something breaks.

Three parts (see [`docs/architecture.md`](docs/architecture.md)):

- **① Explorer AI** *(not built yet)* — crawls a site once and writes the map.
- **② The engine** *(this repo)* — cheap & deterministic; stress-tests the map and
  emits **breakage cases**.
- **③ Triage AI** *(not built yet)* — replays a case, confirms real vs. false; real
  → alert; false → fix the map + suppress the case's signature.

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
