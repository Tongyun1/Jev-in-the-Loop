"""One TypeSafe request chooses the operation, target, and prepared text value."""

import math
import time

import httpx

from .questions import NEXT_ACTION, TARGET, TEXT_VALUE

CLIENT = httpx.Client(http2=True, timeout=25)


def _validate(answer, ids):
    try:
        probabilities = answer["probabilities"]
        numbers = [*probabilities.values(), answer["confidence"]]
        valid = (
            answer["choice"] in ids
            and set(probabilities) == set(ids)
            and all(
                type(number) in (int, float) and math.isfinite(number) and 0 <= number <= 1
                for number in numbers
            )
            and abs(sum(probabilities.values()) - 1) < 0.02
            and probabilities[answer["choice"]] >= max(probabilities.values()) - 1e-6
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("Invalid TypeSafe response")
    return answer


def _post(url, key, body, timeout):
    for attempt in range(3):
        try:
            response = CLIENT.post(
                url, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=timeout
            )
        except httpx.HTTPError:
            raise RuntimeError("TypeSafe connection failed") from None
        if response.status_code in {429, 503, 529} and attempt < 2:
            time.sleep(0.25 * 2**attempt)
            continue
        if response.is_error:
            raise RuntimeError(f"TypeSafe returned HTTP {response.status_code}")
        return response.json()
    raise RuntimeError("TypeSafe unavailable")


def action_space(actions):
    elements, indices, targets, controls = [], {}, {}, {}
    operations = {"click": "CLICK", "fill": "TYPE_TEXT", "select": "SELECT", "press": "PRESS_ENTER"}
    for action in actions:
        kind = action["kind"]
        if kind not in operations:
            controls[action["id"].upper()] = action
            continue
        node = action["node"]
        if node not in indices:
            index = str(len(elements) + 1)
            indices[node] = index
            element = {
                key: action[key]
                for key in ("role", "value", "checked", "selected", "expanded")
                if key in action
            }
            element.update(index=index, label=action["label"].split(" → ")[0], operations=[])
            if kind == "select":
                element["value"] = action.get("current_value", "")
                element["options"] = []
            elements.append(element)
        index = indices[node]
        operation = operations[kind]
        group = targets.setdefault(operation, {})
        element = elements[int(index) - 1]
        if operation not in element["operations"]:
            element["operations"].append(operation)
        target = index
        if kind == "select":
            target = f"{index}:{len(element['options']) + 1}"
            element["options"].append({"index": target, "label": action["label"], "value": action["value"]})
        group[target] = action
    return elements, targets, controls


def choose(page, goal, history, text_values, settings):
    elements, targets, controls = action_space(page["actions"])
    labels = {
        "CLICK": "Click an element, menu option, autocomplete suggestion, or calendar day.",
        "TYPE_TEXT": "Replace text in an editable field with one supplied value.",
        "SELECT": "Select an observed native dropdown value.",
        "PRESS_ENTER": "Submit the current query using Enter on an observed search field.",
    }
    operations = {key: labels[key] for key in targets}
    operations.update({key: value["label"] for key, value in controls.items()})
    operations.update(
        DONE="Every requirement is visibly satisfied.", BLOCKED="No supported operation can progress."
    )
    questions = {
        "operation": {
            "type": "choice",
            "criteria": operations,
            "instructions": {"goal": goal, "rules": NEXT_ACTION},
        }
    }
    for operation, candidates in targets.items():
        questions[operation.lower() + "_target"] = {
            "type": "choice",
            "criteria": {
                index: {
                    "element": f"[{index}] {action['label']}",
                    "current_value": action.get("current_value", action.get("value", "")),
                    **{
                        key: action[key]
                        for key in ("role", "checked", "selected", "expanded")
                        if key in action
                    },
                }
                for index, action in candidates.items()
            },
            "instructions": {"goal": goal, "operation": operation, "rules": [NEXT_ACTION, TARGET]},
        }
    values = {item.id: {"field": item.field, "value": item.value} for item in text_values}
    if values:
        questions["type_text_value"] = {
            "type": "choice",
            "criteria": values,
            "instructions": {"goal": goal, "rules": TEXT_VALUE},
        }
    body = {
        "model": settings.model,
        "state": {
            "page": {key: page.get(key) for key in ("url", "title", "text", "scroll")},
            "elements": elements,
            "recent_actions": [
                {key: item.get(key) for key in ("action", "kind", "text", "page_changed")}
                for item in history[-10:]
            ],
        },
        "questions": questions,
    }
    started = time.perf_counter()
    result = _post("https://api.typesafe.ai/v1/systemone", settings.api_key, body, settings.timeout_seconds)
    operation_answer = _validate(result["answers"].get("operation", {}), operations)
    operation = operation_answer["choice"]
    target = None
    target_answer = None
    text_choice = None
    if operation in targets:
        target_answer = _validate(
            result["answers"].get(operation.lower() + "_target", {}), targets[operation]
        )
        target = target_answer["choice"]
        action = targets[operation][target]
        if operation == "TYPE_TEXT" and values:
            text_choice = _validate(result["answers"].get("type_text_value", {}), values)["choice"]
    else:
        action = controls[operation] if operation in controls else None
    return {
        "operation": operation,
        "action": action,
        "target": target,
        "text_choice": text_choice,
        "confidence": operation_answer["confidence"],
        "target_confidence": target_answer["confidence"] if target_answer else None,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "model": result.get("model"),
        "usage": result.get("usage") or {},
    }
