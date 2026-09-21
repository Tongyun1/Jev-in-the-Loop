# Jev-in-the-Loop: Browser

**English** · [简体中文](README_ZH.md) · [Watch the demos](https://github.com/Tongyun1/Jev-in-the-Loop#browser-demos)

**A Codex plugin for ultrafast browser actions.** Give it a task, let Jev handle the actions, and take over at the page you asked for.

<a id="安装到-codex"></a>

## Install in Codex

This guide is for macOS. You'll need **Codex with its CLI and plugin support**, **Chrome**, [**uv**](https://docs.astral.sh/uv/getting-started/installation/), and a [**TypeSafe API key**](https://docs.typesafe.ai/introduction). uv manages Python and dependencies; your existing Codex handles text preparation.

### 1. Get the plugin and start setup

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
uv run --locked --no-dev --no-editable python scripts/setup.py
```

Already cloned it? Start from the plugin directory. If you received the maintainer's
`jev-browser-plugin-<version>-codex.zip`, extract it and open
`Jev-in-the-Loop/plugins/jev-browser-plugin` instead, then run the same `uv run` command.

### 2. Follow the prompts

Paste your TypeSafe API key into the hidden terminal prompt, then open Chrome and
follow the connection instructions. Setup prepares Python and runtime dependencies,
saves your key locally with private permissions, and installs the plugin in Codex.
An existing key is reused. Jev usage is billed by TypeSafe; no additional text-model key is needed.

### 3. Give it a task

Open a **new Codex task** with the plugin enabled and say:

```text
Use Jev to search Bilibili in English for Stanford CS336.
Open the first video and leave the page open.
```

Codex starts the plugin for you. From here, just describe the outcome.

The marketplace installs a copy into Codex's plugin cache. Keep the extracted or
cloned folder for future updates. If your CLI does not recognize `codex plugin`,
update Codex first. The developer helper `scripts/install_local.py` is not needed.

## Make it yours

- **Keep a result:** “Leave the page open.”
- **Prepare a booking:** “Choose a room and stop at the booking form. Do not submit an order.”
- **Continue a paused task:** Ask Codex to resume the existing Jev session.

Actions run in local Chrome. The task and visible page data go to TypeSafe, so use public, non-sensitive pages. [Privacy details](SECURITY.md).

---

[Setup help](docs/USAGE.md#setup-help) · [Configuration & tools](docs/USAGE.md) · [Development](docs/RELEASING.md) · [MIT & attribution](THIRD_PARTY_NOTICES.md)
