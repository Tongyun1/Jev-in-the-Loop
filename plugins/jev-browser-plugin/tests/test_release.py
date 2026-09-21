import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

from jev_browser.browser import Browser
from jev_browser.config import Settings
from jev_browser.models import RunRequest, Viewport


def test_defaults_are_native_window_and_ephemeral_tabs():
    request = RunRequest(url="https://example.com/", goal="Inspect")
    assert request.visible and request.viewport is None and not request.keep_open
    with pytest.raises(ValueError):
        Viewport(width=0, height=780)


def test_native_window_does_not_override_metrics():
    browser = Browser.__new__(Browser)
    browser.viewport = None
    browser.call = Mock()
    browser.configure_viewport()
    browser.call.assert_not_called()
    browser.viewport = Viewport(width=1440, height=900)
    browser.configure_viewport()
    browser.call.assert_called_once_with(
        "Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False
    )


def test_cleanup_only_owned_tabs(monkeypatch):
    browser = Browser.__new__(Browser)
    browser.target = "child"
    browser.owned_targets = {"parent", "child"}
    cdp = Mock(return_value={"success": True})
    monkeypatch.setattr("jev_browser.browser.cdp", cdp)
    browser.close()
    assert {c.kwargs["targetId"] for c in cdp.call_args_list} == {"parent", "child"}
    assert browser.target is None


def test_config_default_and_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for key in ("TYPESAFE_API_KEY", "TYPESAFE_MODEL", "JEV_ENV_FILE"):
        monkeypatch.delenv(key, raising=False)
    assert not Settings.load().api_key
    config = tmp_path / ".config/jev-browser/config.env"
    config.parent.mkdir(parents=True)
    config.write_text("TYPESAFE_API_KEY=fixture-only\nTYPESAFE_MODEL=fixture-model\n")
    assert Settings.load().api_key == "fixture-only"
    monkeypatch.setenv("TYPESAFE_API_KEY", "fixture-override")
    assert Settings.load().api_key == "fixture-override"
    assert "fixture-override" not in repr(Settings.load())
    monkeypatch.setenv("JEV_ENV_FILE", str(tmp_path / "missing.env"))
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert Settings.load().configuration_error


def test_release_allowlist_excludes_local_data():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("package_release", root / "scripts/package_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = [p.relative_to(root).as_posix() for p in module.release_files(root)]
    assert ".env.example" in names and "LICENSE" in names and ".codex-plugin/plugin.json" in names
    assert "src/jev_browser/snapshot.js" in names and ".mcp.json" in names
    assert not any(n.startswith(("artifacts/", ".venv/", "dist/", "release/")) for n in names)
    assert ".env" not in names and not any("__pycache__" in n for n in names)
