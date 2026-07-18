# edumaze-player

A **universal, code-first exploratory tester**. Model any web app as a *maze* (a
graph of states), then let a *player* walk it like a monkey — poking forms,
clicking things, trying cases — and report what's broken with a deterministic
replay path.

The maze is **code, not data**: a self-describing Python script built from the
`edumaze` framework. See [`docs/architecture.md`](docs/architecture.md) for the
full design.

## Status

Framework core is built, unit-tested (browser-free, via an in-memory driver),
**and validated against a live site** (`sites/edumaze/maze.py` walks
`edumaze.lyabah.com` with the real Playwright driver):

- `edumaze/` — the framework: `Node`, `Site`, `Role`, `Budgets`, the walk `Player`,
  matcher, oracles (L1 technical + acceptance, L2 differential), safety policy,
  locators (role / placeholder / text / css), SPA settle-polling, and a
  real-browser Playwright adapter.
- `edumaze/drivers/fake.py` — an in-memory driver to exercise a maze without a
  browser (used by the tests, and handy for maze authors).
- `tests/example_maze.py` — a reference hand-written maze + matching fake app,
  with two deliberately broken states.
- `sites/edumaze/maze.py` — a real maze for a live SPA (landing → create game →
  lobby → exit).

Not built yet: the **crawl skill** (generate a maze from a live site) and the
**triage skill** (classify/prioritize reports).

## Run the tests

```bash
python3 -m pytest -q
```

## Walk a real site (needs a browser)

```bash
pip install -e ".[playwright]" && playwright install chromium
edumaze run path/to/maze.py --mode explore --seed 1
```

## The maze in one glance

```python
from edumaze import Node, Site, Role, Budgets

class Dashboard(Node):
    url = "/dashboard"
    def matches(self, page):                 # how to recognize this state
        return page.by_role("heading", name="Dashboard").visible()
    def options(self):                       # the outgoing edges
        return [self.go("Settings", to=Settings),
                self.submit("Search", fields={"Query": "text"}, to=Results)]
    def accept(self, page):                  # acceptance criteria, as code
        assert page.by_role("navigation").visible(), "nav missing"

class ExampleSite(Site):
    base_url = "https://staging.example.com"
    entry = Dashboard
    roles = [Role("admin", login=login_admin)]
    budgets = Budgets(max_actions=500)
```
