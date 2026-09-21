from copy import deepcopy

import pytest

from jev_browser import agent
from jev_browser.config import Settings
from jev_browser.models import Condition, ResumeRequest, RunRequest
from jev_browser.workflow import matches

SETTINGS = Settings(api_key="test")


def page(text="start", controls=None, sensitive=False):
    return dict(
        url="https://example.com/",
        title="Fixture",
        text=text,
        actions=[],
        controls=controls or [],
        sensitive_fields=sensitive,
        fingerprint=text,
    )


def condition(source="text", expected="result", **kwargs):
    return dict(source=source, expected=expected, **kwargs)


def decision(label="Search", kind="click", operation="CLICK", text_choice=None):
    return dict(
        operation=operation,
        action=dict(label=label, kind=kind, id="e1", node=1),
        text_choice=text_choice,
        latency_ms=1,
    )


class FakeBrowser:
    instances = []
    pages = [page()]
    fail_after_action = False

    def __init__(self, *args, **kwargs):
        self.target = "same-tab"
        self.current = deepcopy(self.pages[0])
        self.actions = []
        self.instances.append(self)

    def observe(self):
        if self.fail_after_action and self.actions:
            raise RuntimeError("private browser data must not escape")
        return deepcopy(self.current)

    def act(self, action, old, text=None):
        self.actions.append((action, text))
        self.current = deepcopy(self.pages[min(len(self.actions), len(self.pages) - 1)])

    def fresh(self, *args):
        return True

    def close(self):
        self.target = None


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    agent.SESSIONS.clear()
    FakeBrowser.instances = []
    FakeBrowser.pages = [page()]
    FakeBrowser.fail_after_action = False
    monkeypatch.setattr(agent, "Browser", FakeBrowser)
    yield
    agent.SESSIONS.clear()


def request(**kwargs):
    kwargs.setdefault("keep_open", True)
    return RunRequest.model_validate(dict(url="https://example.com/", goal="Find requested result", **kwargs))


def test_control_evidence_is_bound_to_unique_label():
    c = Condition.model_validate(condition("value", "Kyoto", label="Destination"))
    assert not matches(c, page("Kyoto recommendations"), [])
    assert matches(c, page(controls=[dict(label="Destination", value="Kyoto")]), [])
    assert not matches(c, page(controls=[dict(label="Destination", value="Kyoto")] * 2), [])


def test_premature_search_is_filtered_then_enabled(monkeypatch):
    first = page()
    fill = dict(id="fill", node=1, kind="fill", label="Query", value="", search_input=True)
    submit = dict(id="submit", node=2, kind="click", label="Search", search_input_node=1)
    first["actions"] = [fill, submit]
    second = page("prepared")
    second["actions"] = [dict(fill, value="logic"), submit]
    FakeBrowser.pages = [first, second, page("result")]

    def choose(p, *args):
        # Deliberately prefer premature submission whenever it is offered.
        action = next((a for a in p["actions"] if a["kind"] == "click"), p["actions"][0])
        return dict(
            operation="CLICK" if action["kind"] == "click" else "TYPE_TEXT",
            action=action,
            text_choice="q" if action["kind"] == "fill" else None,
            latency_ms=0,
        )

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(
        request(text_values=[dict(id="q", field="Query", value="logic")], success_when=[condition()]),
        SETTINGS,
    )
    assert result["status"] == "done"
    assert [a[0]["kind"] for a in FakeBrowser.instances[-1].actions] == ["fill", "click"]


def test_filtered_submission_cannot_bypass_dispatch_guard(monkeypatch):
    p = page()
    submit = dict(id="submit", node=2, kind="click", label="Search", search_input_node=1)
    p["actions"] = [dict(id="fill", node=1, kind="fill", label="Query", value="", search_input=True), submit]
    FakeBrowser.pages = [p]
    monkeypatch.setattr(
        agent, "choose", lambda *a: dict(operation="CLICK", action=submit, text_choice=None, latency_ms=0)
    )
    result = agent.run(request(text_values=[dict(id="q", field="Query", value="logic")]), SETTINGS)
    assert result["status"] == "blocked"
    assert not FakeBrowser.instances[-1].actions


def test_action_evidence_requires_execution():
    c = Condition.model_validate(condition("action", "Search"))
    assert not matches(c, page(), [dict(action="Search")])
    assert matches(c, page(), [dict(action="Search", executed=True)])


def test_stage_advancement_changes_goal_and_verifies_without_extra_model_call(monkeypatch):
    FakeBrowser.pages = [page(), page("results"), page("filtered")]
    goals = []

    def choose(p, goal, *args):
        goals.append(goal)
        return decision("Search" if len(goals) == 1 else "Only available")

    monkeypatch.setattr(agent, "choose", choose)
    r = agent.run(
        request(
            stages=[
                dict(
                    goal="Search catalog",
                    complete_when=[condition(expected="results"), condition("action", "Search")],
                ),
                dict(goal="Filter availability", complete_when=[condition(expected="filtered")]),
            ]
        ),
        SETTINGS,
    )
    assert r["status"] == "done" and r["steps"] == 2 and len(r["evidence"]) == 2
    assert "CURRENT STAGE ONLY: Filter availability" in goals[1]
    assert r["session_id"] is None


def test_model_done_is_not_verified_success(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="DONE"))
    assert agent.run(request(success_when=[condition()]), SETTINGS)["status"] == "unverified"
    assert agent.run(request(), SETTINGS)["status"] == "unverified"


@pytest.mark.parametrize("sensitive,stop", [(True, []), (False, [condition(expected="start")])])
def test_page_boundary_precedes_model(monkeypatch, sensitive, stop):
    FakeBrowser.pages = [page(sensitive=sensitive)]
    monkeypatch.setattr(agent, "choose", lambda *a: pytest.fail("page must not reach model"))
    result = agent.run(request(stop_when=stop), SETTINGS)
    assert result["status"] == "safety_stop" and result["visible_text"] == ""
    assert result["session_id"] is None


def test_missing_text_resumes_same_tab_and_stages(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision("Query", "fill", "TYPE_TEXT", "q"))
    FakeBrowser.pages = [page(), page("result")]
    first = agent.run(request(success_when=[condition()]), SETTINGS)
    assert first["status"] == "needs_text"
    second = agent.resume(
        ResumeRequest.model_validate(
            dict(
                session_id=first["session_id"],
                text_values=[dict(id="q", field="Query", value="public topic")],
            )
        ),
        SETTINGS,
    )
    assert second["status"] == "done" and len(FakeBrowser.instances) == 1
    assert second["tab_target_id"] == first["tab_target_id"]


def test_timeout_does_not_replay_action_on_resume(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision())
    first = agent.run(
        request(
            stages=[
                dict(
                    goal="Search",
                    complete_when=[condition()],
                    transitions=[dict(after_label="Search", until=[condition()], timeout_ms=100)],
                )
            ]
        ),
        SETTINGS,
    )
    assert first["status"] == "blocked" and first["steps"] == 1
    b = FakeBrowser.instances[0]
    second = agent.resume(ResumeRequest(session_id=first["session_id"]), SETTINGS)
    assert second["status"] == "blocked" and len(b.actions) == 1
    b.current = page("result")
    third = agent.resume(ResumeRequest(session_id=first["session_id"]), SETTINGS)
    assert third["status"] == "done" and len(b.actions) == 1


def test_executed_action_survives_observation_failure(monkeypatch):
    FakeBrowser.fail_after_action = True
    monkeypatch.setattr(agent, "choose", lambda *a: decision())
    result = agent.run(request(), SETTINGS)
    assert result["status"] == "error" and result["history"][0]["executed"]
    assert "private browser data" not in str(result) and result["session_id"] is None


def test_resume_cannot_change_safety_boundary(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="BLOCKED"))
    first = agent.run(request(stop_before=["Danger"]), SETTINGS)
    FakeBrowser.instances[0].current = dict(page(), url="https://outside.example.org/")
    assert agent.resume(ResumeRequest(session_id=first["session_id"]), SETTINGS)["status"] == "safety_stop"


def test_release_and_concurrent_resume(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="BLOCKED"))
    result = agent.run(request(), SETTINGS)
    key = result["session_id"]
    state = agent.SESSIONS[key]
    state.lock.acquire()
    try:
        assert agent.resume(ResumeRequest(session_id=key), SETTINGS)["status"] == "blocked"
        assert agent.release(key)["status"] == "blocked"
    finally:
        state.lock.release()
    assert agent.release(key)["status"] == "released"
    assert FakeBrowser.instances[0].target == "same-tab"


def test_action_budget_is_per_resume(monkeypatch):
    FakeBrowser.pages = [page(), page("intermediate"), page("result")]
    monkeypatch.setattr(agent, "choose", lambda *a: decision())
    result = agent.run(request(max_steps=1, success_when=[condition()]), SETTINGS)
    assert result["status"] == "blocked" and result["steps"] == 1
    result = agent.resume(ResumeRequest(session_id=result["session_id"], max_steps=1), SETTINGS)
    assert result["status"] == "done" and result["steps_this_run"] == 1


def test_precondition_blocks_wrong_field_before_search(monkeypatch):
    FakeBrowser.pages = [page("logic recommendations", controls=[dict(label="Query", value="wrong")])]
    monkeypatch.setattr(agent, "choose", lambda *a: decision())
    result = agent.run(
        request(
            stages=[
                dict(
                    goal="Search logic",
                    complete_when=[condition()],
                    transitions=[
                        dict(
                            after_label="Search",
                            require_before=[condition("value", "logic", label="Query")],
                            until=[condition()],
                        )
                    ],
                )
            ]
        ),
        SETTINGS,
    )
    assert result["status"] == "blocked" and result["steps"] == 0
    assert FakeBrowser.instances[0].actions == []


def test_partial_dispatch_is_not_retried(monkeypatch):
    def uncertain(*args, **kwargs):
        raise RuntimeError("dispatch interrupted")

    monkeypatch.setattr(FakeBrowser, "act", uncertain)
    monkeypatch.setattr(agent, "choose", lambda *a: decision())
    result = agent.run(request(), SETTINGS)
    assert result["status"] == "error" and result["history"][0]["executed"] is None
    assert result["session_id"] is None


def test_final_evidence_failure_does_not_restart_completed_stages(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: pytest.fail("completed stages replayed"))
    result = agent.run(
        request(
            stages=[dict(goal="Already complete", complete_when=[condition(expected="start")])],
            success_when=[condition(expected="missing final evidence")],
        ),
        SETTINGS,
    )
    assert result["status"] == "unverified" and result["stage_index"] == 1


def test_blocked_can_reveal_below_fold_without_clicking(monkeypatch):
    initial = page()
    initial["actions"] = [dict(id="scroll_down", kind="scroll", label="Scroll down", delta=560)]
    FakeBrowser.pages = [initial, page("result")]
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="BLOCKED"))
    monkeypatch.setattr(agent.time, "sleep", lambda _: None)
    result = agent.run(request(success_when=[condition()]), SETTINGS)
    assert result["status"] == "done" and result["steps"] == 1
    assert result["history"][0]["kind"] == "scroll"


def test_default_run_closes_owned_browser_on_pause(monkeypatch):
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="BLOCKED"))
    result = agent.run(RunRequest(url="https://example.com", goal="Inspect"), SETTINGS)
    assert FakeBrowser.instances[0].target is None
    assert result["session_id"] is None and not result["tab_kept_open"]


@pytest.mark.parametrize("navigate,complete", [(False, False), (True, False), (False, True)])
def test_fill_clear_cycle_with_changing_recommendations(monkeypatch, navigate, complete):
    FakeBrowser.pages = [
        page(f"recommendation {i}", controls=[dict(node=1, label="Query", value="logic" if i % 2 else "")])
        for i in range(5)
    ]
    if navigate:
        FakeBrowser.pages[-1]["url"] = "https://example.com/results"
    if complete:
        FakeBrowser.pages[-1]["text"] = "result"
    sequence = iter(
        [
            decision("Query", "fill", "TYPE_TEXT", "q"),
            decision(),
            decision("Query", "fill", "TYPE_TEXT", "q"),
            decision(),
            decision(operation="DONE"),
        ]
    )
    monkeypatch.setattr(agent, "choose", lambda *a: next(sequence))
    result = agent.run(
        request(
            max_steps=8,
            text_values=[dict(id="q", field="Query", value="logic")],
            success_when=[condition()],
        ),
        SETTINGS,
    )
    assert result["steps"] == 4
    assert result["status"] == ("done" if complete else "unverified" if navigate else "blocked")
    if not navigate and not complete:
        assert "fill/clear cycle" in result["reason"]


def test_cycle_detector_allows_different_query_or_field():
    def record(kind, node, value):
        return kind, node, "https://example.com", 0, ((1, value, None, None),)

    fill, clear = record("fill", 1, "logic"), record("click", 2, "")
    assert agent.fill_clear_cycle([fill, clear, fill, clear])
    assert not agent.fill_clear_cycle([fill, clear, record("fill", 1, "algebra"), clear])
    assert not agent.fill_clear_cycle([fill, clear, record("fill", 3, "logic"), clear])


def test_repeated_price_is_removed_despite_changing_countdown(monkeypatch):
    price = decision("Current price SGD 47")["action"]
    scroll = dict(id="scroll_down", kind="scroll", label="Scroll down", delta=560)
    FakeBrowser.pages = [
        {**page(f"countdown {i}"), "actions": [price, scroll], "scroll": {"y": 0}} for i in range(3)
    ] + [page("Rooms ready")]
    offered = []

    def choose(p, *args):
        offered.append([a["label"] for a in p["actions"]])
        if price in p["actions"]:
            return decision(price["label"])
        return {**decision(operation="SCROLL_DOWN"), "action": scroll}

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(request(success_when=[condition(expected="Rooms ready")]), SETTINGS)
    assert result["status"] == "done" and result["steps"] == 3
    assert price["label"] not in offered[-1]
    assert result["history"][-1]["kind"] == "scroll"


def test_repeat_filter_survives_resume_and_allows_control_progress(monkeypatch):
    price = decision("Price")["action"]
    FakeBrowser.pages = [{**page(f"timer {i}"), "actions": [price]} for i in range(3)]
    monkeypatch.setattr(agent, "choose", lambda *a: decision("Price"))
    first = agent.run(request(max_steps=2), SETTINGS)
    second = agent.resume(ResumeRequest(session_id=first["session_id"]), SETTINGS)
    assert second["status"] == "blocked" and second["steps_this_run"] == 0
    # A real form change makes the same control eligible again.
    FakeBrowser.instances[0].current["controls"] = [dict(label="Guests", value="3")]
    third = agent.resume(ResumeRequest(session_id=first["session_id"], max_steps=1), SETTINGS)
    assert third["steps_this_run"] == 1


def test_completion_rejects_substring_or_action_only_evidence():
    from pydantic import ValidationError

    for conditions in (
        [condition(expected="Guest", match="contains")],
        [condition("action", "Book")],
        [condition(expected="Guest", match="contains"), condition("action", "Book")],
    ):
        with pytest.raises(ValidationError, match="completion requires"):
            request(stages=[dict(goal="Open reservation", complete_when=conditions)])
        with pytest.raises(ValidationError, match="completion requires"):
            request(success_when=conditions)
    # Broad text can supplement independent evidence, and conservative stop rules stay valid.
    request(
        success_when=[
            condition("url", "/booking/", match="contains"),
            condition(expected="Guest", match="contains"),
        ]
    )
    request(stop_when=[condition(expected="Guest", match="contains")])


def test_exact_text_line_distinguishes_reviews_from_guest_form():
    c = Condition(source="text", expected="Guest details", match="line")
    assert not matches(c, page("Guest Reviews\nGuest details and reviews"), [])
    assert matches(c, page("Reservation\n  Guest   details  \nContact details"), [])
    assert not matches(Condition(source="text", expected="Guest", match="line"), page("Guest Reviews"), [])


def test_guest_reviews_never_complete_booking_stage(monkeypatch):
    FakeBrowser.pages = [page("Rooms\nGuest Reviews\nPolicies")]
    monkeypatch.setattr(agent, "choose", lambda *a: decision(operation="DONE"))
    result = agent.run(
        request(
            stages=[
                dict(
                    goal="Open reservation", complete_when=[condition(expected="Guest details", match="line")]
                )
            ]
        ),
        SETTINGS,
    )
    assert result["status"] == "unverified" and result["stage_index"] == 0


def test_open_close_loop_offers_alternative_after_two_round_trips(monkeypatch):
    opening = decision("Open guests")["action"]
    closing = decision("Close guests")["action"]
    search = {**decision("Search")["action"], "node": 3}
    closed = {**page("closed"), "actions": [opening, search]}
    opened = {**page("opened"), "actions": [closing]}
    FakeBrowser.pages = [closed, opened, closed, opened, closed, page("result")]

    def choose(p, *args):
        action = p["actions"][0]
        return {**decision(action["label"]), "action": action}

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(request(success_when=[condition()]), SETTINGS)
    assert result["status"] == "done" and result["steps"] == 5
    assert result["history"][-1]["action"] == "Search"
    assert result["history"][3]["repeated_edge"]


def test_already_equal_fill_is_not_executed_and_click_remains(monkeypatch):
    fill = {**decision("Query", "fill")["action"], "value": "logic"}
    search = {**decision("Search")["action"], "node": 2}
    FakeBrowser.pages = [{**page(), "actions": [fill, search]}, page("result")]

    def choose(p, *args):
        a = p["actions"][0]
        return {**decision(a["label"], a["kind"], text_choice="q"), "action": a}

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(
        request(success_when=[condition()], text_values=[dict(id="q", field="Query", value="logic")]),
        SETTINGS,
    )
    assert result["status"] == "done" and result["steps"] == 1
    assert result["history"][0]["action"] == "Search"
