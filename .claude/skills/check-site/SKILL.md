---
name: check-site
description: Check whether a website works by stress-testing it — build a map of the site (or reuse one), run the deterministic engine over it (viewports, form fuzzing, toggles), triage the results into real issues vs false positives, report findings + run statistics, and self-heal (fix the map or the engine modules, suppress confirmed-false cases). Use when the user gives a URL (and optionally what matters) and wants to know if the site is broken.
---

# Check a site — the whole loop, one skill

You run the full lifecycle. Spend tokens only at the two thinking ends —
**building/updating the map** and **triaging results**. The middle — *running* the
map — is a cheap deterministic subprocess, not an AI task. See
`docs/architecture.md`.

```
1. MAP     reuse sites/<id>/map.py, or generate it            [AI, only if needed]
2. RUN     edumaze run … --suppress sites/<id>/suppress.txt    [cheap subprocess]
3. TRIAGE  per signature: replay/inspect → real vs false       [AI]
4. REPORT  real issues + run statistics                        [AI]
5. HEAL    fix map OR engine module; suppress false; re-run     [AI + subprocess]
```

## Setup

Needs Playwright + `tools/probe.py`. If missing:
```
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium
```
Run the engine and probe with that interpreter (`.venv/bin/python -m edumaze.cli …`,
`.venv/bin/python tools/probe.py …`). Pick a short `<id>` for the site.

## 1 — Map: reuse or generate

- If `sites/<id>/map.py` exists and the user didn't ask to rebuild → use it.
- Otherwise **generate it** by probing the live site:
  1. `probe.py <url>` and `probe.py <url> --viewport 390x844`. Catalog headings /
     key text (informational), buttons & links (interactive), inputs (with
     `required` / `maxlength` / `kind`).
  2. Model the entry as a `State`; each element is informational, interactive, or
     both, with a visible/hidden expectation. Forms → a submit `Element` carrying
     its `Field`s. Menus/modals → `Toggle(reveals=[…])` with the revealed items
     marked `visible=False` in the base state.
  3. BFS the navigations (`--steps` to reach deeper states) until no new states or
     ~8–12 states. Weave in whatever the user said "matters".
  4. Write `sites/<id>/map.py` (see the model in README / any existing map).
  - **`maxlength` caveat**: don't set `Field.max_len` when the DOM already enforces
    `maxlength` (the browser prevents longer input → over-length fuzz would
    false-positive). Keep `required` and `type`.
  - **Safety**: third-party sites are **read-only** — never submit destructive
    forms (mark them `destructive=True`), never create real accounts/leads, set
    `domain_allowlist` to the host. The user's own staging → fuller interaction OK.

## 2 — Run (cheap)

```
python3 -m edumaze.cli run sites/<id>/map.py --seed 1 --suppress sites/<id>/suppress.txt
```
Capture the JSON: `cases`, `states_checked`, `configs_run`, `actions_taken`,
`duration_ms`, `cases_by_kind`, `suppressed_signatures`.

## 3 — Triage (the expensive judgement)

The engine already de-duplicates by **signature**, so you triage *unique
signatures*, not every path. For each case:
- **Reproduce it** — replay its `steps` at its `config` (viewport / input) with the
  probe or a short browser script; look at what's actually on screen.
- Classify:
  - **REAL** — a genuine defect (element the user needs is missing/covered, a link
    dead, an invalid input accepted, an error/slow load). Keep as an alert.
  - **FALSE — map is wrong** — the expectation is incorrect (that element is *meant*
    to be hidden here, that submit is *meant* to stay). → fix the map (step 5).
  - **FALSE — engine is wrong** — a systemic checker flaw the case exposes (e.g. an
    element judged visible while off-canvas or covered). → fix the module (step 5).
- If several signatures share one root cause, decide it **once** and apply to all.

## 4 — Report to the user

Give a plain report, honest about confidence:
- **Issues found** (real only): what, which state + config, steps to reproduce,
  evidence (screenshot/console/status). If none, say so.
- **What was dismissed** and why (false positives you triaged away).
- **Run statistics**: states checked, viewports/configs, `actions_taken`,
  `duration_ms`, total vs unique cases, `cases_by_kind`, how many suppressed.
- **What you changed** (map / module / suppressions).

## 5 — Heal, then re-run

- **Map fix** → edit `sites/<id>/map.py` (correct the expectation, mark destructive,
  fix a locator).
- **Suppress** → append the confirmed-false `signature` (one per line) to
  `sites/<id>/suppress.txt` so it won't recur.
- **Engine/module fix** → edit `edumaze/…` **only** for a systemic flaw; keep the
  change minimal and **run `python3 -m pytest -q`** — it must stay green.
- **Re-run** step 2 to confirm the report is now clean or shows only real issues.
  Iterate until stable.

## Output

A human-readable report (issues + statistics + what changed) and the updated
artifacts: `sites/<id>/map.py`, `sites/<id>/suppress.txt`, and — only if a
systemic bug was fixed — changes under `edumaze/`.
