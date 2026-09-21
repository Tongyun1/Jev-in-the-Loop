"""Fast site-independent loop with locally verified stages and resumable pauses."""

import threading
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .browser import Browser, StalePage
from .model import choose
from .progress import Progress, action_identity, state_identity
from .readiness import unready_actions
from .safety import action_block_reason, allowed_url, link_block_reason
from .workflow import safety_boundary, satisfied


@dataclass
class Session:
    request: object
    browser: object = None
    history: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    stage: int = 0
    stage_start: int = 0
    pending: object = None
    lock: object = field(default_factory=threading.Lock)
    touched: float = field(default_factory=time.monotonic)
    recent_controls: list = field(default_factory=list)
    progress: Progress = field(default_factory=Progress)


SESSIONS = {}
STORE_LOCK = threading.Lock()


def fill_clear_cycle(records):
    """Detect two identical fill/clear cycles independently of decorative page changes."""
    if len(records) < 4:
        return False
    a, b, c, d = records[-4:]
    if a != c or b != d or a[0] != "fill" or b[0] != "click" or a[2:4] != b[2:4]:
        return False
    filled = next((v for node, v, *_ in a[4] if node == a[1]), None)
    cleared = next((v for node, v, *_ in b[4] if node == a[1]), None)
    return bool(filled) and cleared == ""


def run(request, settings):
    with STORE_LOCK:
        for key, state in list(SESSIONS.items()):
            if not state.lock.locked() and time.monotonic() - state.touched > 1800:
                del SESSIONS[key]  # Expiry forgets state; visible tabs stay open.
        if len(SESSIONS) >= 16:
            return {"status": "blocked", "reason": "session capacity reached; release a paused session"}
        key, state = uuid.uuid4().hex, Session(request)
        state.lock.acquire()
        SESSIONS[key] = state
    try:
        return _execute(key, state, settings, request.max_steps)
    finally:
        state.touched = time.monotonic()
        state.lock.release()


def resume(request, settings):
    with STORE_LOCK:
        state = SESSIONS.get(request.session_id)
        if state is None or time.monotonic() - state.touched > 1800:
            return {"status": "blocked", "reason": "session missing or expired"}
        if not state.lock.acquire(blocking=False):
            return {"status": "blocked", "reason": "session is already running"}
    try:
        values = {v.id: v for v in state.request.text_values}
        values.update({v.id: v for v in request.text_values})
        state.request = type(state.request).model_validate(
            {**state.request.model_dump(), "text_values": list(values.values())}
        )
        return _execute(request.session_id, state, settings, request.max_steps)
    finally:
        state.touched = time.monotonic()
        state.lock.release()


def release(session_id):
    """Forget a paused session without closing tabs. Active runs cannot be released."""
    with STORE_LOCK:
        state = SESSIONS.get(session_id)
        if state and not state.lock.acquire(blocking=False):
            return {"status": "blocked", "reason": "session is already running"}
        if state:
            del SESSIONS[session_id]
            state.lock.release()
    return {"status": "released", "tabs_closed": False}


def _execute(key, state, settings, max_steps):
    request, history = state.request, state.history
    started, initial_steps = time.monotonic(), len(history)
    deadline = started + 150
    page = None
    domains = {(urlparse(str(request.url)).hostname or "").lower().rstrip("."), *request.allowed_domains}
    values = {v.id: v.value for v in request.text_values}

    def finish(status, **extra):
        terminal = status in {"done", "safety_stop", "error"} or not request.keep_open
        if terminal:
            with STORE_LOCK:
                SESSIONS.pop(key, None)
        withheld = page and (
            safety_boundary(page, request.stop_when) or not allowed_url(page["url"], domains)
        )
        return {
            "status": status,
            "session_id": None if terminal else key,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "steps": len(history),
            "steps_this_run": len(history) - initial_steps,
            "url": page.get("url") if page and not withheld else None,
            "title": page.get("title") if page and not withheld else None,
            "visible_text": page.get("text", "")[:2000] if page and not withheld else "",
            "history": history.copy(),
            "stage_index": state.stage,
            "evidence": state.evidence.copy(),
            "tab_target_id": state.browser.target if state.browser else None,
            "tab_kept_open": bool(state.browser and request.keep_open),
            **extra,
        }

    def boundary():
        if not allowed_url(page["url"], domains):
            return "page left the allowed domains"
        return safety_boundary(page, request.stop_when)

    try:
        if settings.configuration_error or not settings.api_key:
            return finish("error", error_code="configuration_error")
        for value in request.text_values:
            if action_block_reason({"kind": "fill", "label": value.field}, []):
                return finish("safety_stop", reason="sensitive supplied field description")
        if state.browser is None:
            state.browser = Browser(str(request.url), visible=request.visible, viewport=request.viewport)
        browser = state.browser
        page = browser.observe()
        stale_retries = decisions = blocked_rechecks = exploratory_scrolls = 0
        while True:
            reason = boundary()
            if reason:
                return finish("safety_stop", reason=reason)
            if time.monotonic() >= deadline:
                return finish("blocked", reason="time budget reached")
            # Re-observe a pending transition on resume; never replay its action.
            if state.pending:
                transition = state.pending
                until = min(deadline, time.monotonic() + transition.timeout_ms / 1000)
                while not satisfied(transition.until, page, history[state.stage_start :]):
                    if time.monotonic() >= until:
                        return finish(
                            "blocked", reason="expected transition not observed; action not retried"
                        )
                    time.sleep(0.05)
                    page = browser.observe()
                    reason = boundary()
                    if reason:
                        return finish("safety_stop", reason=reason)
                state.pending = None
            while state.stage < len(request.stages):
                stage = request.stages[state.stage]
                if not satisfied(stage.complete_when, page, history[state.stage_start :]):
                    break
                if not browser.fresh(page):
                    page = browser.observe()
                    break
                state.evidence.append(
                    {
                        "stage": state.stage,
                        "url": page["url"],
                        "conditions": [c.model_dump() for c in stage.complete_when],
                    }
                )
                state.stage += 1
                state.stage_start = len(history)
            if boundary():
                return finish("safety_stop", reason=boundary())
            stages_done = state.stage == len(request.stages)
            verified = (
                satisfied(request.success_when, page, history)
                if request.success_when
                else bool(request.stages)
            )
            if stages_done and verified and browser.fresh(page):
                return finish(
                    "done",
                    completion="locally_verified",
                    final_conditions=[c.model_dump() for c in request.success_when],
                )
            if stages_done and request.stages and not verified:
                return finish(
                    "unverified",
                    reason="stages completed but final evidence is unmet; completed stages not replayed",
                )
            if fill_clear_cycle(state.recent_controls) and state.recent_controls[-1][3] == state.stage:
                state.recent_controls.clear()
                return finish("blocked", reason="repeated fill/clear cycle; choose a different control")
            if len(history) - initial_steps >= max_steps or decisions >= max_steps * 3:
                return finish("blocked", reason="action or decision budget reached")
            decisions += 1
            stage = request.stages[state.stage] if not stages_done else None
            active_goal = request.goal
            if blocked_rechecks:
                active_goal += (
                    "\nRecheck: loading may have finished. Scroll to reveal below-fold controls; "
                    "use Search/Enter for a prepared query. Do not choose unrelated links."
                )
            if stage:
                active_goal += (
                    f"\nCompleted stages: {state.stage}. CURRENT STAGE ONLY: {stage.goal}"
                    f"\nRequired evidence: {[c.model_dump() for c in stage.complete_when]}"
                )
            context = state_identity(page, state.stage)
            exhausted = state.progress.exhausted(context)
            model_page = page
            if exhausted:
                model_page = {
                    **page,
                    "actions": [a for a in page.get("actions", []) if action_identity(a) not in exhausted],
                }
                active_goal += (
                    "\nActions repeating an already explored state transition have been removed. "
                    "Choose another observed control or scroll to reveal actual actionable options. "
                    "A changing countdown or price text is not task progress."
                )
            unready = unready_actions(page, request.text_values, stage, history[state.stage_start :])
            if unready:
                model_page = {
                    **model_page,
                    "actions": [a for a in model_page["actions"] if a["id"] not in unready],
                }
                active_goal += (
                    "\nSubmission actions with unmet local prerequisites have been removed. "
                    "Prepare the required field values before submitting."
                )
            decision = choose(model_page, active_goal, history, request.text_values, settings)
            if time.monotonic() >= deadline:
                return finish("blocked", reason="time budget reached before executing decision")
            operation = decision["operation"]
            if operation == "DONE":
                if not browser.fresh(page):
                    page = browser.observe()
                    continue
                return finish(
                    "unverified",
                    reason="model reports done but local completion conditions are absent or unmet",
                )
            if operation == "BLOCKED":
                if blocked_rechecks < 2:
                    blocked_rechecks += 1
                    time.sleep(0.5)
                    page = browser.observe()
                    continue
                scroll = next(
                    (a for a in model_page.get("actions", []) if a.get("id") == "scroll_down"), None
                )
                if scroll and exploratory_scrolls < 3:
                    exploratory_scrolls += 1
                    decision = {
                        **decision,
                        "operation": "SCROLL_DOWN",
                        "action": scroll,
                        "text_choice": None,
                        "latency_ms": decision.get("latency_ms", 0),
                    }
                    operation = "SCROLL_DOWN"
                else:
                    return finish(
                        "blocked", reason="Jev found no supported operation after bounded observation/scroll"
                    )
            action = decision["action"]
            if not action:
                return finish("error", error_code="invalid_decision")
            if action.get("id") in unready:
                return finish("blocked", reason="action preconditions not verified; no action executed")
            if action_identity(action) in exhausted:
                return finish("blocked", reason="repeated state transition; action not retried")
            reason = action_block_reason(action, request.stop_before) or link_block_reason(action, domains)
            if reason:
                return finish(
                    "safety_stop",
                    reason=reason,
                    pending_action={"kind": action["kind"], "label": action["label"]},
                )
            text = None
            if action["kind"] == "fill":
                choice = decision["text_choice"]
                if not choice or choice not in values:
                    return finish(
                        "needs_text", pending_action={"kind": action["kind"], "label": action["label"]}
                    )
                text = values[choice]
                if action.get("value") == text:
                    # Filling an already equal value is not submission/autocomplete selection.
                    # Keep click/Enter alternatives; do not emit another input event or spend an action.
                    state.progress.record(context, action, context)
                    state.progress.record(context, action, context)
                    continue
            before = page["fingerprint"]
            transition = (
                next((t for t in stage.transitions if t.after_label == action["label"]), None)
                if stage
                else None
            )
            if (
                transition
                and transition.require_before
                and not satisfied(transition.require_before, page, history[state.stage_start :])
            ):
                return finish("blocked", reason="action preconditions not verified; no action executed")
            try:
                browser.act(action, page, text=text)
            except StalePage:
                stale_retries += 1
                if stale_retries > 10:
                    return finish("blocked", reason="page changed too often to act safely")
                page = browser.observe()
                continue
            except Exception:
                history.append(
                    {
                        "step": len(history) + 1,
                        "executed": None,
                        "action": action["label"],
                        "kind": action["kind"],
                        "page_changed": None,
                        "outcome": "uncertain; never automatically retried",
                    }
                )
                raise
            stale_retries = 0
            history.append(
                {
                    "step": len(history) + 1,
                    "executed": True,
                    "operation": operation,
                    "action": action["label"],
                    "kind": action["kind"],
                    "text_value_id": decision["text_choice"],
                    "decision_latency_ms": decision["latency_ms"],
                    "page_changed": None,
                    "executed_ms": round((time.monotonic() - started) * 1000),
                }
            )
            state.pending = transition
            page = browser.observe()
            history[-1]["page_changed"] = page["fingerprint"] != before
            history[-1].update(state.progress.record(context, action, state_identity(page, state.stage)))
            state.recent_controls.append(
                (
                    action["kind"],
                    action.get("node"),
                    page["url"],
                    state.stage,
                    tuple(
                        (c.get("node"), c.get("value"), c.get("checked"), c.get("selected"))
                        for c in page.get("controls", [])
                    ),
                )
            )
            state.recent_controls = state.recent_controls[-4:]
            repeated = history[-3:]
            if len(repeated) == 3 and all(
                h["page_changed"] is False and h["kind"] != "wait" for h in repeated
            ):
                return finish("blocked", reason="three actions produced no visible state change")
    except Exception as error:
        return finish(
            "error",
            error_code=type(error).__name__,
            reason="execution interrupted; inspect retained tab before another run",
        )
    finally:
        if state.browser and not request.keep_open:
            state.browser.close()
