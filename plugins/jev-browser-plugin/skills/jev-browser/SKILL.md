---
name: jev-browser
description: Run public, non-sensitive browser tasks at high speed in Chrome using Jev and a persistent Browser Harness CDP loop. Supports staged search, filtering, navigation, and form preparation with local outcome checks.
---

# Fast browser workflow

Use `jev_run` for the safe multi-step portion in one call. Do not reproduce individual actions
with a slow browser-tool loop. Unsupported interactions return control with retained tab context.
Use visible Chrome by default; never imply that an operation occurred in Safari or the app browser.
The default viewport follows the real window. Set `viewport: {width, height}` only for an explicitly
fixed-size task or benchmark. `keep_open` defaults to false: run-owned tabs close on exit.
For user inspection, checkout handoff, or resumable tasks, explicitly set `keep_open: true`.
Do not start repeated fresh runs to recover a pause. Resume the returned session instead.
Retained tabs are not automatically reused across independent tasks; never silently overwrite them.

## Prepare the request

Provide the starting `url`, full `goal`, allowed hostname families in `allowed_domains`, and
task-specific control label phrases in `stop_before`. Supply exact non-sensitive strings in
`text_values`, each with a stable `id`, precise `field` description, and `value`.
Never supply passwords, OTPs, contact details, government IDs, financial data, or other secrets.
Goals, supplied values, visible text, and control state go to TypeSafe. Use public/non-sensitive pages.

For multi-stage tasks, supply `stages`: each has a current `goal`, nonempty `complete_when`,
and optional `transitions`. The core contains no site-specific business logic.

Conditions have `source`, `expected`, optional `label`, and `match` (`exact` default, `contains`,
or `line`). `line` applies only to page text and matches a complete normalized text line.
Sources: `url`, `title`, `text`, `value`, `checked`, `selected`, `action`.
Control state conditions require the exact accessible `label` and fail if that label is ambiguous.
`checked`/`selected` use string values such as `"true"`. `action` matches an actually executed label;
in stage conditions it only considers that stage's history. Never use action history alone as proof
of outcome. Prefer exact control values plus result URL/title over broad keyword matches.
Stage completion and final success must contain URL/control evidence or exact/line text evidence;
text/title substrings and action history alone are rejected. A `Guest` substring also matches
`Guest Reviews` and does not prove a reservation page. Use an observed reservation URL or a
specific heading such as `Guest details` with `match: "line"`; stop before transmitting form data.
Use separate search/detail/room-selection stages so completed searches are not replayed.

A transition has `after_label` (exact action label), optional `require_before` (all must match before
execution), `until` (all must match afterward), and `timeout_ms` (100–10000, default 3000).
Use this for delayed results, autocomplete, validation, and navigation. A timeout preserves the
pending transition; resuming checks it again without replaying the action. Normal DOM quiet waits
are short and cannot establish that an asynchronous business operation has finished.

Provide `success_when` for final independent verification. All stages and all final conditions must
pass. If final conditions are omitted, completing all configured stages suffices. With neither,
the model can only report `unverified`, never verified `done`.
`stop_when` is a list of page conditions; ANY match stops before the next model request.
Use it for the user-requested preparation boundary, such as entering an information-entry page.

Example stage for a public catalog (adapt labels to the observed site, do not guess selectors):

```json
{
  "goal": "Search the catalog for logic",
  "complete_when": [
    {"source": "text", "expected": "Results for logic", "match": "line"},
    {"source": "action", "expected": "Search"}
  ],
  "transitions": [{
    "after_label": "Search",
    "require_before": [{"source": "value", "label": "Query", "expected": "logic"}],
    "until": [{"source": "text", "expected": "Results for logic", "match": "contains"}]
  }]
}
```

## Results and continuation

- `done`: caller-specified local evidence passed; report what was actually verified.
- `unverified`: model claimed completion without sufficient local evidence; do not claim success.
- `needs_text` / `blocked`: use `jev_resume` with returned `session_id` and additional safe
  `text_values` when this resolves the pause. Same tab, stages, domains and boundaries are retained.
  Repeated state/action/result paths are excluded at that state, including open/close cycles;
  the model can choose alternatives or scroll. Numeric stepper controls include their group context
  and current value. Do not interpret decorative text changes or a return to an old state as progress.
- `safety_stop`: return control to the user; do not bypass through another tool or fresh run.
- `error`: execution may be uncertain. Inspect before retrying; no automatic replay/resume.

Sessions are process-local, expire after 30 idle minutes, and disappear on restart.
`jev_release` forgets a paused session without closing tabs; it does not cancel active runs.
`keep_open: false` closes only run-owned tabs and disables continuation.
Setup does not depend on prior conversation: install uv/Python dependencies per the repository README,
provide a TypeSafe API key through environment variables or `~/.config/jev-browser/config.env`, and
enable local Chrome remote debugging. `jev_health` does not connect to Chrome (`browser_connected: null`).

Safety guards use labels and form metadata, not a universal side-effect classifier. Detected
sensitive forms stop before model transmission, but unlabelled private text cannot reliably be
detected. Top-level standard DOM controls are supported; cross-origin frames, closed shadow roots,
canvas interfaces, upload and drag/drop are not guaranteed. Do not promise arbitrary-site coverage.
New direct child tabs are adopted; unrelated tabs are never selected, and ambiguous children stop.

The fast path derives from `browser-use/jev-ultrafast` under MIT; retain upstream attribution.
