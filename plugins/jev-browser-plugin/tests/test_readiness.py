import pytest

from jev_browser.models import Stage, TextValue
from jev_browser.readiness import unready_actions


def snapshot(value):
    return {
        "actions": [
            dict(id="fill", node=1, kind="fill", label="Query", value=value, search_input=True),
            dict(id="submit", node=2, kind="click", label="Search", search_input_node=1),
            dict(id="enter", node=1, kind="press", label="Enter", search_input_node=1),
            dict(id="reveal", node=3, kind="click", label="Search"),
        ]
    }


@pytest.mark.parametrize("value", ["", "recommended topic", "Stanford CS336"])
def test_query_must_equal_prepared_value(value):
    values = [TextValue(id="q", field="Video search input", value="Stanford CS336")]
    assert unready_actions(snapshot(value), values, None, []) == (
        set() if value == "Stanford CS336" else {"submit", "enter"}
    )


def test_ambiguous_inputs_and_unrelated_values_are_not_guessed():
    values = [TextValue(id="q", field="Query", value="logic")]
    p = snapshot("")
    p["actions"].append(dict(p["actions"][0], id="other", node=4))
    assert not unready_actions(p, values, None, [])
    assert not unready_actions(snapshot(""), values * 2, None, [])
    assert not unready_actions(snapshot(""), [TextValue(id="x", field="City", value="Kunming")], None, [])


def test_explicit_prerequisites_filter_before_model_selection():
    stage = Stage.model_validate(
        dict(
            goal="Search",
            complete_when=[dict(source="url", expected="https://example.com/results")],
            transitions=[
                dict(
                    after_label="Search",
                    require_before=[dict(source="value", label="Query", expected="logic")],
                    until=[dict(source="text", expected="Results")],
                )
            ],
        )
    )
    p = snapshot("")
    assert unready_actions(p, [], stage, []) == {"submit", "reveal"}
    p["controls"] = [dict(label="Query", value="logic")]
    assert not unready_actions(p, [], stage, [])
