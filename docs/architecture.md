# edumaze-player — Architecture Spec

A **universal, site-agnostic exploratory tester**. It models any web app as a
**maze** (a graph of states), then a **player** walks that maze like a monkey —
poking forms, clicking things, trying cases — and reports what's broken with a
deterministic replay path.

**The maze is code, not data.** The repo ships a framework of common modules; a
site's maze is a self-describing Python script built from those modules. The script
declares *what each state is, what options it offers, and its acceptance criteria*;
all the machinery (browser driving, walk strategy, oracles, diffing, reporting,
safety) lives behind the scenes in the framework.

Three components around one shared artifact (the **maze script**):

1. **Crawl skill** (Claude) — explores a site → writes `sites/<id>/maze.py`.
2. **Player** (Python + Playwright) — imports & runs the maze → emits reports.
3. **Triage skill** (Claude) — reads reports + the maze's git diff → real regression
   vs. legit change, prioritizes, blesses or rejects the regenerated maze.

---

## 1. Design decisions (locked)

| Decision | Choice | Consequence |
|---|---|---|
| Config form | **Code** (Python script), not data files | Framework library + generated script; no JSON/YAML |
| Target scope | **Universal**, not one site | Generic framework + a per-site `Site` class |
| Target ownership | User owns the apps (staging) | Reset hooks & seeded creds *available* but optional |
| App type | **Mixed** SPA/MPA | A state is a declared `Node`, matched by predicate — not a URL |
| Executor | **Real browser** (Playwright) | Handles JS, forms, SPA navigation |
| Auth | Optional, multi-role | `Role` objects with login recipes on the `Site` |
| Maze upkeep | **Full auto-regenerate** | L2 oracle is *differential* (diff materialized graph vs git baseline) |

### The oracle: three layers

What counts as "not working." Cheap→expensive, universal→noisy.

- **L1 — Technical + node acceptance** (always on): HTTP 4xx/5xx, uncaught JS console
  errors, network failures, timeouts, dead-ends **plus** each visited node's
  `accept(page)` criteria (arbitrary code — the code-first win). A failing `accept`
  is a first-class finding.
- **L2 — Differential** (core regression signal): the framework materializes the
  declared maze into a normalized data structure and diffs it against the
  **previously committed baseline** (`sites/<id>/baseline.json`). An edge that used
  to reach a state and now 404s, an option that disappeared, a new undocumented
  state → drift. No text-diffing of Python; diff the materialized graph. Fully
  compatible with auto-regenerate: regenerate the script, re-materialize, diff.
- **L3 — Semantic** (opt-in, off by default): Claude-inferred "this *should* do X."
  High false-positive rate; dormant in v1.

> Why differential: auto-regenerate rewrites the acceptance criteria too, so they
> can't be their own regression baseline. Diffing the materialized graph against the
> last *committed* baseline makes git the source of truth.

---

## 2. The framework (common modules, shipped in the repo)

Package `edumaze/` (renameable). This is the reusable machinery the generated
script leans on.

```
edumaze/
  __init__.py       # public API: Node, Site, Role, Budgets, action helpers
  node.py           # Node base class + option/edge helpers (go/submit/back/...)
  site.py           # Site base class (base_url, allowlist, roles, volatile, budgets)
  role.py           # Role + login recipe execution
  page.py           # thin wrapper over Playwright Page (accessible-first locators)
  matcher.py        # resolve an observed page -> declared Node (§4)
  materialize.py    # declared maze -> normalized graph dict (for L2 diff)
  oracles.py        # L1 (technical + accept), L2 (differential)
  strategy.py       # coverage-guided walk w/ random mode; seeded RNG
  policy.py         # safety policy: which edges allowed in which mode (§7)
  player.py         # the walker: drives the browser, runs the loop
  report.py         # Report/Finding dataclasses + serialization
  cli.py            # `edumaze run sites/example/maze.py --mode explore --seed 123`
```

### Base classes the script uses

- **`Node`** — one state. Declares identity + options + acceptance criteria:
  - `url` / `matches(self, page) -> bool` — how to recognize this state.
  - `options(self) -> list[Option]` — outgoing edges, via helpers:
    `self.go(name, to=Node, classify=...)`, `self.submit(form, fields=..., to=...)`,
    `self.back()`. `classify ∈ {safe, destructive, external}` drives safety (§7).
  - `accept(self, page)` — acceptance criteria as code (asserts). Runs on arrival.
- **`Site`** — the old "manifest," now a class: `base_url`, `domain_allowlist`,
  `entry` (start node), `roles`, `volatile` (selectors/params excluded from
  signature + diff), `denylist`, `budgets`, `reset_hook` (optional), `seed_data`.
- **`Role`** — `name` + a `login(page)` recipe + a `logged_in_when` check.
- **`Budgets`** — `max_actions`, `max_depth`, `max_wall_clock_s`, `actions_per_second`.

Reusable subclasses/mixins ship too (e.g. `FormPage`, `LoggedInNode`) so generated
scripts stay short.

---

## 3. The generated maze script (`sites/<id>/maze.py`)

Self-describing, executable. The crawl skill writes this; the player runs it.

```python
from edumaze import Node, Site, Role, Budgets

def login_admin(page):
    page.goto("/login")
    page.get_by_role("textbox", name="Email").fill(env("ADMIN_EMAIL"))
    page.get_by_role("textbox", name="Password").fill(env("ADMIN_PASSWORD"))
    page.get_by_role("button", name="Sign in").click()

class Dashboard(Node):
    url = "/dashboard"
    def matches(self, page):
        return page.get_by_role("heading", name="Dashboard").is_visible()
    def options(self):
        return [
            self.go("Settings", to=Settings, classify="safe"),
            self.submit("Search", fields={"q": "text"}, to=SearchResults),
        ]
    def accept(self, page):
        assert page.get_by_role("navigation").is_visible(), "nav missing"

class Settings(Node):
    url = "/settings"
    def matches(self, page): ...
    def options(self):
        return [self.go("Delete account", to=Deleted, classify="destructive")]
    def accept(self, page): ...

class ExampleSite(Site):
    base_url = "https://staging.example.com"
    domain_allowlist = ["staging.example.com"]
    entry = Dashboard
    roles = [Role("admin", login=login_admin, logged_in_when=("link", "Dashboard"))]
    volatile = ["#clock", ".feed", "input[name=csrf]"]
    denylist = ["*/logout"]
    budgets = Budgets(max_actions=500, actions_per_second=3)
    seed_data = {"text": "lorem", "email": "qa+test@example.com", "number": "42"}
```

**Locators are accessibility-first** (`get_by_role` + accessible name), not CSS or
test-ids — so the framework works across sites whose markup we don't control. CSS is
the fallback when no accessible handle exists. If a given app *does* have test-ids,
a node can opt into them.

Secrets come from the environment (`env(...)`), never committed.

---

## 4. State identity: matching, not hashing

A state is a declared `Node`. On arrival, `matcher.py` resolves the live page to a
node by (a) `url` pattern then (b) `matches(page)` predicate. This replaces an opaque
hash with declared, reviewable identity, and gives two useful signals for free:

- **Unmatched page** → an undocumented state: a finding, and a TODO for the crawl
  skill to add a `Node`.
- **Ambiguous match** (two nodes claim the page) → the model is too coarse; flag it.

**Volatile regions** (declared on the `Site`) are stripped before matching *and* the
L2 diff — otherwise clocks/feeds/tokens cause phantom mismatches every run.

---

## 5. The Player (walk loop)

`edumaze run sites/example/maze.py --mode explore --seed 12345`

1. Import the script, materialize the declared maze, load the committed baseline.
   Start Playwright; authenticate each `Role`.
2. From the current node: `options()` → filter by safety policy (§7) → pick next via
   `strategy` (bias to unvisited edges; `--mode random` for pure chaos). RNG is
   **seeded** → reproducible walk.
3. Execute the action. Run L1 (technical + `accept`). Resolve the new node (§4).
4. Run L2 differential against baseline; record divergences.
5. On failure or budget exhaustion, stop. Emit reports + refresh `baseline.json`.

Reproducibility contract: `(maze commit, seed, optional reset_hook)` →
byte-identical walk. Every finding is therefore a runnable replay script.

### Report — `reports/<id>/<run_id>.json`

```json
{
  "run_id": "…", "site_id": "…", "seed": 12345, "maze_commit": "<git sha>",
  "findings": [{
    "oracle": "L1|L2", "severity_hint": "high|med|low",
    "summary": "Node 'Search' accept() failed: results container missing",
    "path": [{"node": "Dashboard", "action": {"submit": "Search"}}, "…"],
    "evidence": {"http_status": 500, "console": ["…"], "screenshot": "…png"}
  }]
}
```

---

## 6. (reserved)

---

## 7. Safety policy (universal, degrades gracefully)

Universal ⇒ can't assume a reset endpoint. Safety is layered so it's safe *without*
one:

- **Domain allowlist is a hard wall.** Off-allowlist → abort + flag.
- **`external` options** (OAuth, payment, `mailto:`, off-domain) are recorded as
  boundary nodes, never traversed.
- **`classify` governs modes:**
  - `explore` (default): `safe` options only. Read-mostly. Safe with **no** reset hook.
  - `chaos`: also `destructive` options — **only when a `reset_hook` is declared**,
    so damage is undone between runs.
- **Denylist** always wins, every mode.
- **Budgets + politeness cap** guarantee termination and bounded load.
- **Kill-switch invariants:** off-domain / forbidden-URL → abort + flag.
- **Prod guard:** refuse unless `base_url` host ∈ `domain_allowlist`; require an
  explicit ack to run destructive mode with no `reset_hook`.

---

## 8. Triage skill (Claude)

Reads `reports/` + the git diff of the regenerated `maze.py`. Per finding:

- **Real regression** — L1 crash / `accept` failure, or an L2 diff reflecting genuine
  behavior loss.
- **Legit change** — app intentionally changed; the new maze is correct → bless it as
  the baseline.
- **Flaky / phantom** — volatile region leaked → propose a `volatile` addition, not a
  bug.

Output: prioritized findings (severity × reachability × confidence) + recommended
action each (file bug / accept maze / patch volatile).

---

## 9. Build order

1. **Framework skeleton** — `Node`/`Site`/`Role`/`Budgets`, `page.py`, `player.py`
   loop, `policy.py`. Prove it against a **hand-written** `maze.py` + a throwaway
   target, L1 only.
2. **Matcher + materialize** — node resolution and the normalized graph form.
3. **L2 differential oracle** — diff materialized maze vs baseline.
4. **Crawl skill** — generate `maze.py` from a live site.
5. **Triage skill** — consume reports + maze diff.

The matcher (§4) and the safety policy (§7) decide whether this finds real bugs or
drowns in noise — they get the most care.

---

## Open questions (deferred, not blocking)

- **Matcher granularity** — tune against a real app; start coarse (role + name +
  landmarks), tighten if states over-collapse or go ambiguous.
- **Form input intelligence** — v1 uses `Site.seed_data` by field semantic; smarter,
  validation-aware generation is later (candidate for L3).
- **Running generated code** — the maze is executable Python the crawl skill wrote.
  Acceptable here (user's own tool, own staging), but worth remembering it's not a
  sandbox.
- **Parallelism** — v1 is single-session sequential; parallel players need per-worker
  isolation (fine with reset hooks, tricky without).
