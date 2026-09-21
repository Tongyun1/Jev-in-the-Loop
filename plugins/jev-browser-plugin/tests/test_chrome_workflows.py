"""Opt-in real Chrome integration; deterministic decisions, no provider dependency."""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from jev_browser import agent
from jev_browser.browser import Browser
from jev_browser.config import Settings
from jev_browser.models import RunRequest, Viewport

pytestmark = pytest.mark.skipif(
    os.environ.get("JEV_TEST_CHROME") != "1", reason="requires Chrome remote debugging"
)


@pytest.fixture(autouse=True)
def stable_fixture_viewport(monkeypatch):
    # Chrome toolbar animations can resize the native viewport between observations.
    # Fix only this synthetic test environment; production retains native sizing.
    original = Browser.__init__

    def initialize(self, *args, **kwargs):
        kwargs["viewport"] = Viewport(width=1280, height=900)
        original(self, *args, **kwargs)

    monkeypatch.setattr(Browser, "__init__", initialize)


@pytest.fixture
def website():
    html = Path(__file__).with_name("workflows.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = b"<title>Preview</title><p>Preview ready</p>" if self.path == "/child" else html
            if self.path == "/private":
                data = b'<label>Password<input type="password" value="secret-fixture"></label>'
            if self.path == "/hotel-flow":
                data = Path(__file__).with_name("hotel-flow.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_real_search_filter_tabs_popup(monkeypatch, website):
    sequence = iter(
        [
            ("Query", "fill"),
            ("Search", "click"),
            ("Category → Books", "select"),
            ("Available only", "click"),
            ("Specifications", "click"),
            ("Open preview", "click"),
        ]
    )

    def choose(page, *args):
        label, kind = next(sequence)
        action = next(a for a in page["actions"] if a["label"] == label and a["kind"] == kind)
        return dict(
            operation={"click": "CLICK", "fill": "TYPE_TEXT", "select": "SELECT"}[kind],
            action=action,
            text_choice="query" if kind == "fill" else None,
            latency_ms=0,
        )

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(
        RunRequest.model_validate(
            dict(
                url=website,
                goal="Search and filter, then inspect preview",
                keep_open=False,
                text_values=[dict(id="query", field="Query", value="logic")],
                stages=[
                    dict(
                        goal="Search logic",
                        complete_when=[dict(source="text", expected="Results for logic", match="line")],
                        transitions=[
                            dict(
                                after_label="Search",
                                until=[dict(source="text", expected="Results for logic", match="contains")],
                            )
                        ],
                    ),
                    dict(
                        goal="Filter books available",
                        complete_when=[
                            dict(source="value", label="Category", expected="Books"),
                            dict(source="checked", label="Available only", expected="true"),
                        ],
                    ),
                    dict(
                        goal="Inspect specifications",
                        complete_when=[dict(source="selected", label="Specifications", expected="true")],
                    ),
                    dict(goal="Open preview", complete_when=[dict(source="text", expected="Preview ready")]),
                ],
            )
        ),
        Settings(api_key="test"),
    )
    assert result["status"] == "done", result
    assert result["steps"] == 6 and len(result["evidence"]) == 4


def test_real_sensitive_page_never_sent(monkeypatch, website):
    monkeypatch.setattr(agent, "choose", lambda *a: pytest.fail("private page sent to model"))
    result = agent.run(
        RunRequest(url=website + "/private", goal="Inspect", keep_open=False), Settings(api_key="test")
    )
    assert result["status"] == "safety_stop" and "secret-fixture" not in str(result)


def test_real_replaced_node_is_stale(website):
    browser = Browser(website, visible=True)
    try:
        page = browser.observe()
        action = next(a for a in page["actions"] if a["label"] == "Search")
        browser.evaluate("document.querySelector('#search').outerHTML='<button>Search</button>'")
        assert not browser.fresh(page, action)
    finally:
        browser.close()


def test_unlabelled_search_div_and_enter(website):
    browser = Browser(website, visible=True)
    try:
        page = browser.observe()
        icon = next(
            a
            for a in page["actions"]
            if a["label"] == "Search"
            and a["kind"] == "click"
            and a["role"] == "button"
            and a["node"] != next(x["node"] for x in page["actions"] if x["label"] == "Search")
        )
        browser.act(icon, page)
        page = browser.observe()
        assert "Icon search complete" in page["text"]
        key = next(a for a in page["actions"] if a["kind"] == "press")
        browser.act(key, page)
        assert "Keyboard search complete" in browser.observe()["text"]
    finally:
        browser.close()


def test_background_text_does_not_invalidate_field(website):
    browser = Browser(website, visible=True)
    try:
        page = browser.observe()
        action = next(a for a in page["actions"] if a["label"] == "Secondary search" and a["kind"] == "fill")
        browser.evaluate("document.querySelector('#result').textContent='Unrelated recommendation changed'")
        assert browser.fresh(page, action)
        browser.evaluate("document.querySelector('#generic-search input').value='changed by user'")
        assert not browser.fresh(page, action)
    finally:
        browser.close()


def test_search_readiness_uses_form_relation_and_live_value(website):
    from jev_browser.models import TextValue
    from jev_browser.readiness import unready_actions

    browser = Browser(website, visible=True)
    try:
        browser.evaluate("""document.body.innerHTML = `<button>Search</button>
          <form role="search" onsubmit="event.preventDefault()">
          <input type="search" aria-label="Query" value="cached recommendation">
          <button>Search</button></form>`""")
        values = [TextValue(id="q", field="Query", value="Stanford CS336")]
        page = browser.observe()
        blocked = unready_actions(page, values, None, [])
        assert len(blocked) == 2  # Associated submit and Enter, not the reveal button.
        submit = next(a for a in page["actions"] if a["kind"] == "click" and a["id"] in blocked)
        browser.evaluate("document.querySelector('input').value='Stanford CS336'")
        assert not browser.fresh(page, submit)
        page = browser.observe()
        assert not unready_actions(page, values, None, [])
        submit = next(a for a in page["actions"] if a.get("search_input_node") and a["kind"] == "click")
        browser.evaluate("document.querySelector('input').value='changed while deciding'")
        assert not browser.fresh(page, submit)
    finally:
        browser.close()


def test_unlabelled_empty_search_input_is_not_omitted(website):
    from jev_browser.models import TextValue
    from jev_browser.readiness import unready_actions

    browser = Browser(website, visible=True)
    try:
        browser.evaluate("""document.body.innerHTML = `<form id="nav-searchform">
          <input class="nav-search-input" placeholder="">
          <div class="nav-search-btn" onclick="void 0" style="width:32px;height:32px"></div>
          </form>`""")
        page = browser.observe()
        field = next(a for a in page["actions"] if a["kind"] == "fill")
        assert field["label"] == "Search query" and field["value"] == ""
        submit = next(a for a in page["actions"] if a["label"] == "Search")
        assert submit["search_input_node"] == field["node"]
        values = [TextValue(id="q", field="Video search input", value="Stanford CS336")]
        assert submit["id"] in unready_actions(page, values, None, [])
        browser.act(field, page, text="Stanford CS336")
        assert not unready_actions(browser.observe(), values, None, [])
    finally:
        browser.close()


def test_search_icons_are_distinct_and_explicit_names_win(website):
    browser = Browser(website, visible=True)
    try:
        browser.evaluate("""document.body.innerHTML = `<form>
          <input class="search-input" aria-label="Query" value="logic">
          <div class="nav-search-clean" onclick="this.previousElementSibling.value=''">×</div>
          <div class="nav-search-btn" onclick="document.title='searched'"></div>
          <div class="search-close" onclick="void 0"></div>
          <div class="search-panel" onclick="void 0"></div>
          <div class="search-btn" aria-label="Filter" onclick="void 0"></div>
          </form><style>div{width:30px;height:30px}</style>`""")
        page = browser.observe()
        labels = [a["label"] for a in page["actions"] if a["kind"] == "click"]
        assert labels.count("Search") == 1
        # Visible text takes precedence over class-derived naming.
        assert "×" in labels and "Close search" in labels and "Filter" in labels
        browser.evaluate("document.querySelector('.nav-search-clean').textContent=''")
        page = browser.observe()
        clear = next(a for a in page["actions"] if a["label"] == "Clear search")
        browser.act(clear, page)
        page = browser.observe()
        assert next(c["value"] for c in page["controls"] if c["label"] == "Query") == ""
        search = next(a for a in page["actions"] if a["label"] == "Search")
        browser.act(search, page)
        assert browser.observe()["title"] == "searched"
    finally:
        browser.close()


def test_price_repeat_recovers_by_scrolling_to_reservation(monkeypatch, website):
    observed_text = []

    def choose(page, *args):
        observed_text.append(page["text"])
        actions = page["actions"]
        action = next((a for a in actions if a["label"] == "Current price SGD 47"), None)
        if action is None:
            action = next((a for a in actions if a["label"] == "Reserve room"), None)
        if action is None:
            action = next(a for a in actions if a["id"] == "scroll_down")
        return dict(
            operation="SCROLL_DOWN" if action["kind"] == "scroll" else "CLICK",
            action=action,
            text_choice=None,
            latency_ms=0,
        )

    monkeypatch.setattr(agent, "choose", choose)
    result = agent.run(
        RunRequest.model_validate(
            dict(
                url=website + "/hotel-flow",
                goal="Open reservation; stop before entering guest data",
                max_steps=8,
                keep_open=False,
                stop_when=[dict(source="text", expected="Guest details", match="line")],
            )
        ),
        Settings(api_key="test"),
    )
    assert result["status"] == "safety_stop", result
    labels = [h["action"] for h in result["history"]]
    assert labels.count("Current price SGD 47") == 2
    assert "Scroll down" in labels and labels[-1] == "Reserve room"
    assert all("Guest details" not in text for text in observed_text)
    assert not result["tab_kept_open"]


def test_pointer_stepper_icons_have_context_and_numeric_state(website):
    browser = Browser(website, visible=True)
    try:
        browser.evaluate("""document.body.innerHTML = `<div role="button" aria-expanded="true">
          <div><div>Adults<span>18 years or above</span></div>
          <div tabindex="0" style="cursor:pointer">
            <i aria-hidden="true" class="icon-minusline" onclick="this.nextElementSibling.textContent--"></i>
            <span>1</span>
            <i aria-hidden="true" class="icon-plusline"
               onclick="this.previousElementSibling.textContent++"></i>
          </div></div></div>
          <div aria-hidden="true"><button>Hidden action</button></div>
          <style>i{display:inline-block;width:24px;height:30px;cursor:pointer}</style>`""")
        page = browser.observe()
        increase = next(a for a in page["actions"] if a["label"].startswith("Increase Adults"))
        assert increase["current_value"] == "1"
        assert not any(a["label"] in {"1", "Hidden action"} for a in page["actions"])
        assert len([c for c in page["controls"] if c["role"] == "spinbutton"]) == 1
        browser.act(increase, page)
        after = browser.observe()
        assert next(c for c in after["controls"] if c["role"] == "spinbutton")["value"] == "2"
    finally:
        browser.close()
