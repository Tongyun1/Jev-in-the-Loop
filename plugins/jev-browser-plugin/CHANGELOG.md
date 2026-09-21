# Unreleased — 0.1.0 Alpha candidate

- Distinguish inferred search, clear and close icons; preserve explicit accessible labels.
- Stop repeated fill/clear cycles even when unrelated page text changes, after checking completion evidence.

- Public identity: Jev-in-the-Loop: Browser, the first module of Jev-in-the-Loop.
- Self-contained plugin under `plugins/jev-browser-plugin/`; existing technical identifiers retained.

- Codex plugin package now contains its runtime; no sibling project or fixed developer directory is required.
- Shared user config location and an empty credential template; preserve explicit developer overrides.
- Default real-window viewport; fixed dimensions are an opt-in request setting.
- Default `keep_open: false`; explicitly retain a task for handoff/resume.
- Skill UI now describes the fast executor rather than the obsolete suggestion-only mode.
- Local evidence verification, bounded re-observation/scroll, search Enter, and pointer-control heuristics.
- MIT license, privacy notes, offline CI and allowlisted source packaging.

Known limitations: repeated text filling can still stall; browser IPC can time out; real sites have
both successful and failed runs. No published speed guarantee. This release-preparation pass does
not include browser testing. macOS is the only previously exercised desktop platform.
