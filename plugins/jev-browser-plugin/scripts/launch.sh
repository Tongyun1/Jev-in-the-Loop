#!/bin/sh
set -eu
runtime=${JEV_RUNTIME_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
if ! command -v uv >/dev/null 2>&1; then
    echo "Jev: install uv and run uv sync --locked --no-dev in the plugin directory." >&2
    exit 1
fi
exec uv run --project "$runtime" --locked --no-dev --no-editable python -m jev_browser.server
