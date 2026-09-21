"""Track observed state transitions, not decorative DOM mutations or goal completion.

An edge is (observable state, semantic action, resulting state). Replaying the same
edge twice exhausts that action at that source state, including A -> B -> A cycles.
Changing a quantity, navigating, revealing new controls or advancing a stage gives
the action a new context. Completion remains the caller's independently checked evidence.
"""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field


def action_identity(action):
    return tuple(action.get(k) for k in ("kind", "role", "label", "href", "value", "key", "context"))


def state_identity(page, stage):
    controls = [
        {k: c.get(k) for k in ("label", "value", "checked", "selected", "expanded")}
        for c in page.get("controls", [])
        if c.get("role") in {"textbox", "searchbox", "combobox", "spinbutton"}
        or any(c.get(k) not in (None, "") for k in ("value", "checked", "selected", "expanded"))
    ]
    # Node IDs change on re-render. Action labels/context identify the offered surface.
    surface = sorted(
        json.dumps(action_identity(a), ensure_ascii=False)
        for a in page.get("actions", [])
        if a["kind"] not in {"scroll", "wait"}
    )
    payload = json.dumps(
        [
            stage,
            page["url"],
            page.get("scroll", {}).get("y"),
            sorted(controls, key=lambda c: json.dumps(c, sort_keys=True)),
            surface,
        ],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class Progress:
    edges: Counter = field(default_factory=Counter)
    seen: set = field(default_factory=set)

    def exhausted(self, source):
        return {action for (start, action, _), count in self.edges.items() if start == source and count >= 2}

    def record(self, source, action, destination):
        self.seen.add(source)
        transition = (
            "unchanged" if source == destination else "revisited" if destination in self.seen else "new"
        )
        self.seen.add(destination)
        edge = (source, action_identity(action), destination)
        # WAIT is bounded by the decision budget; it must remain available for delayed results.
        if action["kind"] != "wait":
            self.edges[edge] += 1
        return {"state_transition": transition, "repeated_edge": self.edges[edge] > 1}
