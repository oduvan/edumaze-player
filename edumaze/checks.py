"""The oracle: the two guarantees (See / Do) plus generic signals, and the
fuzz-value generator that feeds form submission checks.

Non-mutating checks live here (they observe the current page). Mutating checks
(toggles, form submits) are driven by the engine, which can re-enter a state to
reset between variations.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .cases import DO, SEE, SIGNAL, BreakageCase
from .model import EMAIL, NUMBER, PASSWORD, Element, Field, State


def _case(state: str, kind: str, target: str, detail: str,
          config: Dict[str, Any], steps: List[dict],
          evidence: Dict[str, Any] = None) -> BreakageCase:
    return BreakageCase(state=state, kind=kind, target=target, detail=detail,
                        config=dict(config), steps=list(steps),
                        evidence=evidence or {})


# --- See: every element's actual visibility matches expectation --------------
def see_check(state: State, page, config, steps) -> List[BreakageCase]:
    out: List[BreakageCase] = []
    for el in state.elements():
        actual = _safe_visible(el.find, page)
        if el.visible and not actual:
            out.append(_case(state.name, SEE, el.label,
                             f"expected VISIBLE but not shown", config, steps))
        elif not el.visible and actual:
            out.append(_case(state.name, SEE, el.label,
                             f"expected HIDDEN but is shown", config, steps))
    return out


# --- Do: every visible interactive element is actually usable ---------------
def interact_check(state: State, page, config, steps) -> List[BreakageCase]:
    out: List[BreakageCase] = []
    for el in state.elements():
        if not el.interactive or not el.visible:
            continue
        if el.submit is not None:
            # A submit button is often (correctly) disabled until the form is
            # valid; its usability is verified by the fuzzer instead.
            continue
        handle = el.find.resolve(page)
        if not _safe(handle.visible):
            continue  # a See failure already covers "should be visible but isn't"
        if not _safe(handle.enabled):
            out.append(_case(state.name, DO, el.label,
                             "interactive element is present but disabled",
                             config, steps))
    return out


# --- Signals: errors, bad status, slow load ---------------------------------
def signal_check(state_name: str, page, config, steps,
                 slow_load_ms: int) -> List[BreakageCase]:
    out: List[BreakageCase] = []
    status = page.status
    if status is not None and status >= 400:
        out.append(_case(state_name, SIGNAL, f"http-{status}",
                         f"HTTP {status}", config, steps,
                         {"http_status": status, "url": page.url}))
    errors = page.console_errors
    if errors:
        out.append(_case(state_name, SIGNAL, "console-error",
                         f"{len(errors)} JS console error(s)", config, steps,
                         {"console": errors[:5]}))
    load = page.last_load_ms
    if load is not None and load > slow_load_ms:
        out.append(_case(state_name, SIGNAL, "slow-load",
                         f"loaded in {load} ms (> {slow_load_ms} ms)", config,
                         steps, {"load_ms": load}))
    return out


# --- Fuzz value generation --------------------------------------------------
def valid_value(field: Field, seed_data: Dict[str, str]) -> str:
    if field.valid is not None:
        return field.valid
    key = field.find.label()
    if key in seed_data:
        return seed_data[key]
    if field.type in seed_data:
        return seed_data[field.type]
    return {
        EMAIL: "qa@example.com",
        NUMBER: "42",
        PASSWORD: "Passw0rd!",
    }.get(field.type, "QA Bot")


def invalid_values(field: Field) -> List[Dict[str, str]]:
    """Each entry: {'variant': ..., 'value': ...} that SHOULD be rejected."""
    out: List[Dict[str, str]] = []
    if field.required:
        out.append({"variant": "empty-required", "value": ""})
    if field.max_len is not None:
        out.append({"variant": "over-max-len", "value": "x" * (field.max_len + 5)})
    if field.type == EMAIL:
        out.append({"variant": "bad-email", "value": "not-an-email"})
    if field.type == NUMBER:
        out.append({"variant": "non-numeric", "value": "abc"})
    # Note: special-character / injection probes are a *robustness* check (must
    # not crash) rather than an "invalid" one (a correct form may accept them),
    # so they're intentionally not treated as must-be-rejected here.
    return out


def _safe_visible(locator, page) -> bool:
    return _safe(locator.resolve(page).visible)


def _safe(fn) -> bool:
    try:
        return bool(fn())
    except Exception:
        return False
