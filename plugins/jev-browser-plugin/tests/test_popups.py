from unittest.mock import Mock

import pytest

from jev_browser.browser import Browser


def browser():
    b = Browser.__new__(Browser)
    b.target = "owned"
    b.owned_targets = {"owned"}
    b.visible = True
    b.call = Mock()
    b.evaluate = Mock(return_value=["https://example.com/result", "complete"])
    return b


def test_only_new_direct_child_is_adopted(monkeypatch):
    targets = [
        {"targetId": "unrelated", "type": "page"},
        {"targetId": "child", "type": "page", "openerId": "owned"},
    ]
    cdp = Mock(
        side_effect=lambda method, **kw: (
            {"targetInfos": targets} if method == "Target.getTargets" else {"sessionId": "child-session"}
        )
    )
    monkeypatch.setattr("jev_browser.browser.cdp", cdp)
    b = browser()
    b.follow_popup()
    assert b.target == "child"
    assert b.session == "child-session"
    assert b.owned_targets == {"owned", "child"}
    b.follow_popup()
    assert b.target == "child"


def test_ambiguous_popups_stop_without_choosing(monkeypatch):
    monkeypatch.setattr(
        "jev_browser.browser.cdp",
        lambda *a, **kw: {
            "targetInfos": [{"targetId": name, "type": "page", "openerId": "owned"} for name in ("a", "b")]
        },
    )
    b = browser()
    with pytest.raises(RuntimeError, match="Multiple"):
        b.follow_popup()
    assert b.target == "owned"


def test_blank_popup_waits_for_navigation(monkeypatch):
    monkeypatch.setattr(
        "jev_browser.browser.cdp",
        lambda method, **kw: (
            {"targetInfos": [{"targetId": "child", "type": "page", "openerId": "owned"}]}
            if method == "Target.getTargets"
            else {"sessionId": "child-session"}
        ),
    )
    monkeypatch.setattr("jev_browser.browser.time.sleep", lambda _: None)
    b = browser()
    b.evaluate.side_effect = [["about:blank", "complete"], ["https://example.com/result", "complete"]]
    b.follow_popup()
    assert b.evaluate.call_count == 2


def test_initial_blank_complete_is_not_navigation_complete(monkeypatch):
    monkeypatch.setattr("jev_browser.browser.ensure_daemon", lambda: None)
    monkeypatch.setattr("jev_browser.browser.time.sleep", lambda _: None)
    monkeypatch.setattr("jev_browser.browser.cdp", lambda *a, **kw: {"targetId": "new", "sessionId": "s"})
    states = Mock(side_effect=[["about:blank", "complete"], ["https://example.com", "interactive"]])
    monkeypatch.setattr(Browser, "evaluate", states)
    b = Browser("https://example.com", visible=True)
    assert b.target == "new" and states.call_count == 2
