# Security and privacy (Alpha)

This is a local Codex plugin, not a sandbox or a universal transaction-safety system.
Chrome remote debugging gives broad access to that browser profile. Keep it local, never expose
the debugging port to a network, and preferably use a dedicated profile without private accounts.
The plugin does not automatically enable remote debugging or grant Chrome permissions.

The goal, caller-supplied text, visible page text, control labels/values, and recent action labels
are sent to TypeSafe at `https://api.typesafe.ai/v1/systemone`. The core does not send screenshots.
Do not use private email, financial/medical data, passwords, OTPs, or personal identifiers.
Sensitive-form and action-label heuristics can miss data or actions and can also false-positive.
Page instructions are untrusted, but prompt-injection resistance is not guaranteed.

`keep_open` defaults to false and closes only run-owned tabs. Set it true for a visible handoff or
resumable pause. Do not interact with run-owned tabs during a run: automatic cleanup may close them.
There is no dedicated cancel tool; release only forgets paused state. A soft time budget does not
interrupt an already pending provider/browser request. Retained tabs survive server restart.

Keep keys outside the repository in `~/.config/jev-browser/config.env` with user-only read/write
permissions, or use explicit environment variables. Do not upload `.env`, screenshots, browser
state, traces, cookies, or local config files. `.gitignore` does not protect a manually made ZIP.
Use the allowlisted release script and inspect its manifest before publishing.

Do not include secrets in public issues. If a secret leaks, revoke it at the provider; removing it
from the current Git tree is insufficient. No dedicated security-reporting address is configured yet.
