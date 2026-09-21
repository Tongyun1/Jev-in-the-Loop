# Jev-in-the-Loop: Browser

**English** · [简体中文](README_ZH.md) · [Watch the demos](https://github.com/Tongyun1/Jev-in-the-Loop#from-a-prompt-to-the-page-you-want)

**Ultrafast browser actions, right inside Codex.** Give it a task, let Jev handle the actions, and take over at the page you asked for.

<a id="安装到-codex"></a>

## Install in Codex

This source-install guide is for macOS. You'll need **Codex with its CLI and plugin-creator helpers**, **Chrome**, [**uv**](https://docs.astral.sh/uv/getting-started/installation/), and a [**TypeSafe API key**](https://docs.typesafe.ai/introduction). uv manages Python and dependencies; your existing Codex handles text preparation.

### 1. Get the plugin

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
uv sync --locked --all-groups --no-editable
```

Already cloned it? Start from the plugin directory.

### 2. Add your Jev key

```sh
mkdir -p ~/.config/jev-browser
cp -n .env.example ~/.config/jev-browser/config.env
chmod 600 ~/.config/jev-browser/config.env
open -e ~/.config/jev-browser/config.env
```

In the file that opens, fill in `TYPESAFE_API_KEY=` and save. Keep this file local. Jev usage is billed by TypeSafe; no additional text-model API key is needed.

### 3. Connect Chrome and install

Open Chrome, then run:

```sh
uv run browser-harness --doctor
```

Follow its connection instructions and allow local remote debugging in Chrome. Then install:

```sh
uv run python scripts/install_local.py
```

### 4. Give it a task

Open a **new Codex task** with the plugin enabled and say:

```text
Use Jev to search Bilibili in English for Stanford CS336.
Open the first video and leave the page open.
```

Codex starts the plugin for you. From here, just describe the outcome.

## Make it yours

- **Keep a result:** “Leave the page open.”
- **Prepare a booking:** “Choose a room and stop at the booking form. Do not submit an order.”
- **Continue a paused task:** Ask Codex to resume the existing Jev session.

Actions run in local Chrome. The task and visible page data go to TypeSafe, so use public, non-sensitive pages. [Privacy details](SECURITY.md).

---

[Setup help](docs/USAGE.md#setup-help) · [Configuration & tools](docs/USAGE.md) · [Development](docs/RELEASING.md) · [MIT & attribution](THIRD_PARTY_NOTICES.md)
