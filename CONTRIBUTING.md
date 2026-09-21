# Contributing

Browser is the first module of Jev-in-the-Loop. Keep changes scoped to implemented behavior;
new modules should have their own dependencies, usage documentation and verification.

For Browser, work in `plugins/jev-browser-plugin/` and follow its README for environment setup.
Run `uv run ruff check .`, `JEV_TEST_CHROME=0 uv run pytest -q`, and `uv build` before proposing changes.
Offline tests must not require credentials, a browser session or paid model calls.

Keep the existing plugin ID, import package and MCP tool names compatible. Display branding is
`Jev-in-the-Loop: Browser`. Use synthetic fixtures; never add private browser captures, cookies,
credentials, account data, personal paths or raw session transcripts.

Live browser tests require explicit opt-in (`JEV_TEST_CHROME=1`). Provider-backed probe scripts can
incur charges. Report the environment and actual observed outcome; offline success does not establish
real-site reliability. Retain upstream attribution for derived code.

Report reproducible issues at https://github.com/Tongyun1/Jev-in-the-Loop/issues.
Propose changes through pull requests to https://github.com/Tongyun1/Jev-in-the-Loop.
