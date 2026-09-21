# Configuration and troubleshooting

[Installation guide](../README.md) · [中文安装指南](../README_ZH.md) · [Skill reference](../skills/jev-browser/SKILL.md)

## Setup help

Run commands from `plugins/jev-browser-plugin/` in the cloned repository.

| Symptom | Next step |
| --- | --- |
| `uv: command not found` | [Install uv](https://docs.astral.sh/uv/getting-started/installation/) and restart the terminal. |
| `codex: command not found` | Install or enable the Codex CLI. Check `codex plugin --help` before running the installer. |
| `plugin-creator helpers unavailable` | This message belongs to the optional developer installer. Use `uv run --locked --no-dev --no-editable python scripts/setup.py` for normal installation. |
| Chrome is not connected | Run `uv run browser-harness --doctor`, follow its instructions, and approve local remote debugging in Chrome. |
| Jev reports a configuration error | Check that `~/.config/jev-browser/config.env` contains your TypeSafe key. Restart the plugin service after changing it. |
| Plugin is not visible in the current task | Start a new Codex task after installation. |
| “Destination is not managed by this project” | The installer found another plugin at `~/plugins/jev-browser-plugin`. Inspect its origin before updating it; the installer leaves it untouched. |

The setup wizard registers the repository's `jev-in-the-loop` marketplace and
installs through the Codex CLI. Run it again to continue an interrupted setup;
an existing key is preserved. The key is stored at `~/.config/jev-browser/config.env`.
Python and runtime dependencies are prepared by uv. Codex also prepares the installed
copy's runtime automatically on first launch. Developer/test dependencies are omitted.

For manual installation, run `codex plugin marketplace add ../..` followed by
`codex plugin add jev-browser-plugin@jev-in-the-loop` from the plugin directory.
The older `scripts/install_local.py` is a developer-only personal-marketplace helper.

## Configuration

The default key file is `~/.config/jev-browser/config.env`, outside the repository.

- `TYPESAFE_API_KEY`: required.
- `TYPESAFE_MODEL`: optional; defaults to `jev-1.13.0`.
- `JEV_ENV_FILE`: optional absolute path to another key file.
- `JEV_RUNTIME_ROOT`: optional runtime-directory override for development.

Values are resolved from process environment, then the selected config file.
The plugin does not search the current working directory for `.env`.
Use file permissions `600` and restart the plugin service after configuration changes.

## Task controls

| Setting | Default |
| --- | --- |
| Browser | Visible local Chrome at its real window size |
| `keep_open` | `false`; closes run-owned tabs when the call ends |
| `viewport` | Unset; override only for a fixed-size task |
| `max_steps` | 40; maximum 60 |
| Time budget | 150 seconds, soft limit |
| Paused sessions | Process-local; expire after 30 idle minutes |

Set `keep_open: true` for handoff or continuation. Each run owns its own tabs;
resume an existing paused session to continue its task. Avoid manually editing
its tab during execution.

## Tools and results

- `jev_run`: run a multi-step task with prepared text, stages, and completion conditions.
- `jev_resume`: continue a paused session with additional non-sensitive text.
- `jev_release`: forget a paused session without closing its tabs.
- `jev_health`: check configuration and dependencies; it does not connect to Chrome.

`done` means the supplied completion conditions were locally verified.
`unverified` means that evidence is missing. `needs_text` or `blocked` can
retain a session for continuation; `safety_stop` hands control back at a boundary.
An execution error may leave an uncertain action outcome; inspect before retrying.

For exact conditions, stage transitions, loop handling, and request examples,
see the [skill reference](../skills/jev-browser/SKILL.md). For data flow, browser
permissions, and unsupported interfaces, see [Security & privacy](../SECURITY.md).

## Development

```sh
uv sync --locked --all-groups --no-editable
uv run ruff check .
JEV_TEST_CHROME=0 uv run pytest -q
uv build
```

Offline tests do not launch Chrome or call a paid model. Opt-in Chrome fixture
tests use `JEV_TEST_CHROME=1`. Live probes and recordings can make paid API calls.
Keep recordings, credentials, logs, and build artifacts outside the source tree.
Use the allowlisted [release workflow](RELEASING.md) for distribution.
