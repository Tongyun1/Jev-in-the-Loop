#!/bin/sh
set -eu
runtime=${JEV_RUNTIME_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
if ! command -v uv >/dev/null 2>&1; then
    # Desktop launches may not inherit the user's interactive shell PATH.
    for uv_dir in "$HOME/.local/bin" /opt/homebrew/bin /usr/local/bin; do
        if [ -x "$uv_dir/uv" ]; then
            PATH="$uv_dir:$PATH"
            export PATH
            break
        fi
    done
    if ! command -v uv >/dev/null 2>&1; then
        echo "Jev: install uv from https://docs.astral.sh/uv/getting-started/installation/ and restart Codex." >&2
        exit 1
    fi
fi
exec uv run --project "$runtime" --locked --no-dev --no-editable python -m jev_browser.server
