from jev_browser.progress import Progress, action_identity, state_identity


def test_round_trip_exhausts_repeated_edge_not_only_noop():
    tracker = Progress()
    opening = dict(kind="click", label="Open guests")
    closing = dict(kind="click", label="Close guests")
    for _ in range(2):
        tracker.record("closed", opening, "open")
        tracker.record("open", closing, "closed")
    assert action_identity(opening) in tracker.exhausted("closed")
    assert action_identity(closing) in tracker.exhausted("open")
    assert not tracker.exhausted("different-state")


def test_quantity_changes_and_rerender_identity():
    def page(value, node=1):
        return dict(
            url="https://example.com",
            text="countdown",
            scroll={"y": 0},
            controls=[dict(node=node, role="spinbutton", label="Adults", value=value)],
            actions=[dict(node=node, kind="click", label="Increase Adults")],
        )

    assert state_identity(page("1"), 0) == state_identity(page("1", 99), 0)
    assert state_identity(page("1"), 0) != state_identity(page("2"), 0)
    assert state_identity(page("1"), 0) != state_identity(page("1"), 1)
    tracker = Progress()
    for i in range(1, 5):
        source = state_identity(page(str(i)), 0)
        action = page(str(i))["actions"][0]
        assert action_identity(action) not in tracker.exhausted(source)
        tracker.record(source, action, state_identity(page(str(i + 1)), 0))
