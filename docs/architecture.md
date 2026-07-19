# edumaze-player — Spec (v2)

> Supersedes the earlier "maze walker" spec. That version drifted into a
> page-by-page **coverage walker**. This one is what was actually intended: a
> cheap, deterministic **breakage-hunter** that varies inputs, sizes, toggles,
> and paths to find *the configuration under which the site breaks* — with an
> expensive AI on each side (one to map the site, one to triage results).

---

## 1. Purpose

Testing a site exhaustively with an AI (every path, every edge case, breaking
forms, different screen sizes…) works but burns tokens. So split it: **spend AI
tokens only where judgement is needed, and let a cheap deterministic script do
the repetitive stress-testing.**

Three parts, one cheap core in the middle:

- **① Explorer AI** — expensive, runs rarely. Crawls the site once and writes a
  structured **map**: for each page, one list of **elements**, where every
  element can be *informational* (content the user should perceive), *interactive*
  (something the user can do), or both — and each carries a **visibility**
  expectation (visible / hidden).
- **② The script (stress engine)** — cheap, no tokens, deterministic. Given the
  map, it **messes with the site**: fuzzes forms, resizes the viewport, opens
  menus/modals, and walks different sequences — checking the expectations after
  every variation. It emits **breakage cases**.
- **③ Triage AI** — cheap, per case. Replays a case's exact steps, decides real
  vs. false. Real → **alert the user**. False → **fix the script's root cause**
  *and* **suppress every sibling case with the same signature** so the same
  false positive isn't analysed 50 times.

```
        ① Explorer AI                ② Stress script              ③ Triage AI
   crawl once, emit map  ─────▶  vary + check, emit  ─────▶  replay one case,
   (pages, elements,             breakage cases            judge real/false
    expectations, forms)         (config + steps +          ├─ real  → ALERT USER
        ▲                         failed check)             └─ false → fix script +
        │                                                             suppress siblings
        └───────────────── script fixes / suppressions ◀────────────────┘
```

---

## 2. The map — one element list per state

Code-as-config (a Python script the Explorer writes; the engine imports it). Per
**state** the map declares its **identity** plus a single list of **elements**.

There are **not** two separate kinds of element. Every element can be
**informational**, **interactive**, or **both**, and every element carries a
**visibility** expectation. Two guarantees per page fall straight out of this:

- **See** — the user sees the information they should (and not what they shouldn't).
- **Do** — the user can actually use every element they should be able to use.

Each element declares:

- **`find`** — how to locate it (role+name / text / selector).
- **`visibility`** — expected state here: `VISIBLE` or `HIDDEN`. May be
  **conditional** — e.g. `HIDDEN until "Menu" is opened`.
- **informational aspect** *(optional)* — the content the user should perceive
  (e.g. the expected text).
- **interactive aspect** *(optional)* — what the user can do, and the expected
  effect. One of:
  - **click** → navigates to / opens a target state;
  - **fill** → a form field with type + constraints (required, max length, format);
  - **submit** → with expected *valid* and *invalid* outcomes (valid succeeds;
    invalid fails **gracefully** — an error, never a crash/blank);
  - **toggle** → what it should **reveal** / **hide**.

An element is often both: a "Menu" button is *interactive* (click toggles) and
its own visibility is `VISIBLE`; each menu item is *informational* and
*conditionally* `HIDDEN` until the menu opens. Visibility applies to interactive
elements too — a submit button that should be `VISIBLE` but isn't fails the
**Do** guarantee.

Sketch (illustrative, not final API):

```python
class Lobby(State):
    def identify(self, page): return "/room/" in page.url and page.heading("Лобі")
    elements = [
        Element(text("КОД КІМНАТИ"), visible=True, info=True),           # info only
        Element(role("heading", "Leaderboard"), visible=False),          # must stay hidden
        Element(role("button", "Створити гру"), visible=True,            # info + interactive
                fill=[Field("name", REQUIRED, max_len=40)],
                submit=Submit(on_valid=goes_to(Game), on_invalid=stays_with_error)),
        Element(role("button", "Menu"), visible=True,                    # interactive toggle
                toggle=Toggle(reveals=[text("Settings")], hides=[])),
        Element(text("Settings"), visible="until Menu opened", info=True),  # conditional
        Element(role("button", "Вийти"), visible=True, click=goes_to(Landing)),
    ]
```

> The "expected elements" idea you were unsure about is now just each element's
> `visibility` field; the interactive aspect (`click`/`fill`/`submit`/`toggle`)
> lives on the same element.

---

## 3. The script (stress engine) — what it does

For each state, the engine generates **variations** across four dimensions and,
after each, runs the **oracle**.

**Variation dimensions (v1, all four selected):**
1. **Form fuzzing** — valid, empty, boundary, over-long, and special-character
   inputs; assert valid→success and invalid→graceful failure (never crash/blank).
2. **Responsive / viewport** — mobile / tablet / desktop; directly catches
   "an important element is hidden at this size."
3. **Interactive toggling** — open/close menus, modals, accordions, tabs; assert
   the declared reveal/hide sets.
4. **Navigation sequences** — different orders/paths into a state; catch state
   that breaks depending on how you arrived.

**The oracle (what "broken" means) — the two guarantees + signals:**
- **See (visibility invariant)**: every element's actual state matches its
  expected `visibility` — an element that should be `VISIBLE` but is missing or
  `HIDDEN` fails, and so does one that should be `HIDDEN` but shows.
- **Do (interactability invariant)**: every element with an interactive aspect is
  actually usable (present, enabled, actionable) and produces its declared effect
  — a link navigates, a toggle reveals/hides the right set, a valid submit
  succeeds, an invalid submit fails gracefully.
- **Generic signals**: dead/incorrect links, JS console or HTTP errors, and
  **slow loads** (a load-time threshold).

The four dimensions feed the two guarantees: fuzzing exercises `fill`/`submit`;
viewport + toggling + sequences exercise `visibility` and `click`/`toggle` across
configurations (this is where "important element hidden on mobile" surfaces).

**Determinism**: `(map + seed + dimensions)` fully determines the run, so every
breakage case replays exactly.

**Safety** (unchanged, still needed): domain allowlist as a hard fence;
destructive/external actions gated by mode; forms fuzzed only where the map marks
them safe; polite budgets. On third-party sites: read/interact but never submit
real leads.

---

## 4. Output — breakage cases (with signatures for dedup)

The script returns a list of **breakage cases**. Each is:

```json
{
  "signature": "Lobby|see|room-code-panel|viewport=mobile",
  "state": "Lobby",
  "config": {"viewport": "mobile", "inputs": {...}, "toggles": [...], "path": [...]},
  "check": "see: 'КОД КІМНАТИ' expected VISIBLE, was HIDDEN",
  "steps": [ {"action": "...", ...}, ... ],   // exact replay from entry
  "evidence": {"screenshot": "...", "console": [...], "load_ms": 5200}
}
```

The **`signature`** = `state | check-kind (see/do/signal) | target | config-class`. It groups
cases that fail for the *same reason*, so triage can dismiss a whole group at
once. This is the mechanism that makes "50 broken paths" cheap to triage.

---

## 5. Triage AI — the feedback loop

For one case: **replay the exact steps**, observe, and judge.

- **Real problem** → **alert the user** ("element X hidden on mobile at /lobby",
  with steps + screenshot).
- **False positive** → do **both**:
  1. **Fix the script's root cause** — correct the wrong expectation in the map
     (e.g. that element is *meant* to be hidden on mobile).
  2. **Suppress the signature** — add it to a **suppression list** (a data file
     the engine reads) so every sibling case with that signature is skipped, this
     run and future runs. Keeps triage focused on genuinely-new cases.

So two stores: the **map/script** (root-cause fixes go here) and a **suppression
list** keyed by signature (per-case dismissals go here).

---

## 6. Internal logic (the run loop)

1. Load the **map** + the **suppression list**; start the browser.
2. For each state, for each **viewport**: drive to the state (via a known path),
   run expectation + signal checks.
3. For each **form**: run the fuzz set; check valid→success, invalid→graceful.
4. For each **toggle**: open → check reveals/hides; close → inverse.
5. Try alternate **navigation sequences** into the state.
6. Any failed check whose signature isn't suppressed → record a breakage case.
7. Stop at budget; emit the cases (grouped by signature).

---

## 7. Inputs / outputs at a glance

- **Given:** the map (from the Explorer), run params (seed, which dimensions,
  budgets, viewports), the suppression list, and a browser.
- **Returns:** breakage cases — each a reproducible `(config + steps + failed
  check + evidence)`, grouped by signature. Exit non-zero if any un-suppressed
  case exists (CI-friendly).

---

## 8. What we reuse vs. re-aim from the current build

**Reuse as-is** (already works against real sites):
- the real-browser driver — visible-match clicking, JS-scroll, popup/cookie
  dismissal;
- deterministic **replay by seed**;
- the **safety fence** (domain allowlist, destructive/external gating);
- the report/finding + evidence plumbing.

**Re-aim:**
- the `Node` graph → the richer **map** (element inventory + expectations + form
  constraints + toggles);
- the `Player` "walk" → the **variation/stress runner** (the four dimensions);
- the oracles → **expectation checks + perf/signals**;
- add the **signature + suppression** machinery for the triage loop.

---

## 9. Build order (after this spec is approved)

1. **Map schema** — `State` + the unified `Element` (visibility + optional
   informational/interactive aspects: `click`/`fill`/`submit`/`toggle`); loader +
   the in-memory fake driver updated to model per-element visibility states.
2. **Stress runner core** — viewport + expectation checks against a hand-written
   map + throwaway target (prove the loop browser-free, then live).
3. **Form fuzzing** + graceful-failure checks.
4. **Toggles + navigation-sequence** variation.
5. **Signatures + suppression list**.
6. **① Explorer skill** — generate a map from a live site.
7. **③ Triage skill** — replay, judge, alert / (fix + suppress).

---

## 10. Open questions (not blocking the spec)

- **Perf thresholds** — one global "slow" budget, or per-state? (start global.)
- **Extra environment dimensions** — browser type, network throttling, dark mode
  — later dimensions once the four core ones work.
- **Conditional expectations** — how rich the "hidden until X" language needs to
  be (a predicate on state) vs. a simple per-state list.
- **How the Explorer emits the map** — it writes the code-as-config script; do we
  also want a machine-readable data form it round-trips through? (default: just
  the script.)
