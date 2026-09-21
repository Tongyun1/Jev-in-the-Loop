"""Local evidence evaluation. Never asks the action model to certify its own success."""


def normalize(value):
    return " ".join(str(value).casefold().split())


def matches(condition, page, history):
    source = condition.source
    if source in {"url", "title", "text"}:
        values = [page.get(source, "")]
    elif source == "action":
        values = [h["action"] for h in history if h.get("executed")]
    else:
        # Do not conflate duplicate labels from unrelated controls.
        controls = [
            c for c in page.get("controls", []) if normalize(c["label"]) == normalize(condition.label)
        ]
        if len(controls) != 1:
            return False
        values = [controls[0].get(source, "")]
    expected = normalize(condition.expected)
    return any(
        expected == normalize(v) if condition.match == "exact" else expected in normalize(v) for v in values
    )


def satisfied(conditions, page, history):
    return bool(conditions) and all(matches(c, page, history) for c in conditions)


def safety_boundary(page, stop_when):
    if page.get("sensitive_fields"):
        return "sensitive form detected locally; page withheld from model"
    if any(matches(c, page, []) for c in stop_when):
        return "caller page boundary reached"
    return None
