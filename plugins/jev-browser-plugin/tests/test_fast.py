import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from jev_browser.config import Settings
from jev_browser.model import action_space, choose
from jev_browser.models import RunRequest
from jev_browser.safety import action_block_reason, allowed_url, link_block_reason


async def test_stdio_exposes_only_fast_run_and_health():
    env = dict(os.environ)
    env.pop("TYPESAFE_API_KEY", None)
    env.pop("JEV_ENV_FILE", None)
    params = StdioServerParameters(command=sys.executable, args=["-m", "jev_browser.server"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert set(tools) == {"jev_run", "jev_health", "jev_resume", "jev_release"}
            assert not tools["jev_run"].annotations.readOnlyHint
            assert tools["jev_health"].annotations.readOnlyHint
            health = await session.call_tool("jev_health", {})
            assert not health.isError
            assert health.structuredContent["execution_mode"] == "ultrafast"
            assert health.structuredContent["browser_harness_available"]


def test_request_validation_and_domain_normalization():
    request = RunRequest.model_validate(
        {
            "url": "https://hotels.ctrip.com/",
            "goal": "Search Kunming hotels",
            "text_values": [{"id": "city", "field": "destination", "value": "昆明"}],
            "allowed_domains": ["CTRIP.COM."],
            "stop_before": ["提交订单"],
        }
    )
    assert request.allowed_domains == ["ctrip.com"]
    with pytest.raises(ValueError):
        RunRequest.model_validate(
            {"url": "https://example.com", "goal": "x", "allowed_domains": ["https://bad"]}
        )


def test_safety_boundaries():
    assert action_block_reason({"kind": "click", "label": "最后一步"}, [])
    assert action_block_reason({"kind": "fill", "label": "电话号码"}, [])
    assert action_block_reason({"kind": "click", "label": "Continue"}, ["Continue"])
    assert not action_block_reason({"kind": "click", "label": "查看详情"}, [])
    assert allowed_url("https://hotels.ctrip.com/a", {"ctrip.com"})
    assert not allowed_url("https://example.com", {"ctrip.com"})
    assert link_block_reason(
        {"href": "https://example.com", "kind": "click", "label": "external"}, {"ctrip.com"}
    )


def test_dynamic_action_space_keeps_real_actions():
    actions = [
        {"id": "e1", "node": 3, "kind": "fill", "label": "Destination", "role": "textbox", "value": ""},
        {"id": "e2", "node": 4, "kind": "click", "label": "Search", "role": "button", "value": ""},
        {"id": "wait", "kind": "wait", "label": "Wait"},
    ]
    elements, targets, controls = action_space(actions)
    assert [element["index"] for element in elements] == ["1", "2"]
    assert targets["TYPE_TEXT"]["1"]["id"] == "e1"
    assert targets["CLICK"]["2"]["id"] == "e2"
    assert controls["WAIT"]["id"] == "wait"


def test_one_request_selects_operation_target_and_text(monkeypatch):
    page = {
        "url": "https://example.com",
        "title": "Search",
        "text": "Destination Search",
        "actions": [
            {"id": "e1", "node": 3, "kind": "fill", "label": "Destination", "role": "textbox", "value": ""},
            {"id": "wait", "kind": "wait", "label": "Wait"},
        ],
    }
    values = RunRequest.model_validate(
        {
            "url": "https://example.com",
            "goal": "Search Kunming",
            "text_values": [{"id": "city", "field": "destination", "value": "昆明"}],
        }
    ).text_values

    def fake_post(_url, _key, body, _timeout):
        assert set(body["questions"]) == {"operation", "type_text_target", "type_text_value"}
        return {
            "model": "jev-test",
            "answers": {
                "operation": {
                    "choice": "TYPE_TEXT",
                    "confidence": 1.0,
                    "probabilities": {"TYPE_TEXT": 1.0, "WAIT": 0.0, "DONE": 0.0, "BLOCKED": 0.0},
                },
                "type_text_target": {"choice": "1", "confidence": 1.0, "probabilities": {"1": 1.0}},
                "type_text_value": {"choice": "city", "confidence": 1.0, "probabilities": {"city": 1.0}},
            },
        }

    monkeypatch.setattr("jev_browser.model._post", fake_post)
    result = choose(page, "Search Kunming", [], values, Settings(api_key="test"))
    assert result["operation"] == "TYPE_TEXT"
    assert result["action"]["id"] == "e1"
    assert result["text_choice"] == "city"
