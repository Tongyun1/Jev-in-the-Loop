"""Local prerequisites for submission; elapsed time is not readiness evidence."""

import re

from .workflow import satisfied


def unready_actions(page, text_values, stage, history):
    blocked = set()
    for action in page.get("actions", []):
        if stage:
            transition = next((t for t in stage.transitions if t.after_label == action["label"]), None)
            if (
                transition
                and transition.require_before
                and not satisfied(transition.require_before, page, history)
            ):
                blocked.add(action["id"])

    # Only infer the trivial, unambiguous single-query case. Multi-field workflows
    # use explicit stage prerequisites, not a blanket "fill everything" rule.
    if len(text_values) != 1 or not re.search(
        r"search|query|搜索|查询|关键字|关键词", text_values[0].field, re.I
    ):
        return blocked
    inputs = [a for a in page.get("actions", []) if a.get("search_input") and a["kind"] == "fill"]
    if len(inputs) != 1:
        return blocked
    field = inputs[0]
    if field.get("value") != text_values[0].value:
        blocked.update(
            a["id"] for a in page.get("actions", []) if a.get("search_input_node") == field["node"]
        )
    return blocked
