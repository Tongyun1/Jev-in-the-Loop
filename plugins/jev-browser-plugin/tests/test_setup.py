import importlib.util
import stat
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values


@pytest.fixture
def setup_module():
    source = Path(__file__).resolve().parents[1] / "scripts/setup.py"
    spec = importlib.util.spec_from_file_location("jev_setup", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_key_is_private_and_preserves_settings(setup_module, tmp_path, monkeypatch, capsys):
    config = tmp_path / "config.env"
    config.write_text("# retain this\nTYPESAFE_API_KEY=\nTYPESAFE_MODEL=custom\n")
    monkeypatch.setattr(setup_module.getpass, "getpass", lambda _: "test-key")
    setup_module.configure_key(config)
    assert dotenv_values(config)["TYPESAFE_API_KEY"] == "test-key"
    assert dotenv_values(config)["TYPESAFE_MODEL"] == "custom"
    assert config.read_text().startswith("# retain this")
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert "test-key" not in capsys.readouterr().out
    monkeypatch.setattr(setup_module.getpass, "getpass", lambda _: pytest.fail("Prompted twice"))
    setup_module.configure_key(config)


def test_key_rejects_symlink_and_invalid_input(setup_module, tmp_path, monkeypatch):
    original = tmp_path / "original"
    original.write_text("keep")
    link = tmp_path / "link"
    link.symlink_to(original)
    with pytest.raises(ValueError):
        setup_module.configure_key(link)
    monkeypatch.setattr(setup_module.getpass, "getpass", lambda _: "bad\nINJECTED=value")
    with pytest.raises(ValueError):
        setup_module.configure_key(original)
    assert original.read_text() == "keep"


@pytest.mark.parametrize("doctor_fails", [False, True])
def test_install_sequence_without_real_side_effects(
    setup_module, tmp_path, monkeypatch, doctor_fails
):
    repo = tmp_path / "repo"
    root = repo / "plugins/jev-browser-plugin"
    (repo / ".agents/plugins").mkdir(parents=True)
    (repo / ".agents/plugins/marketplace.json").write_text("{}")
    root.mkdir(parents=True)
    (tmp_path / "browser-harness").touch()
    monkeypatch.setattr(setup_module, "ROOT", root)
    monkeypatch.setattr(setup_module.sys, "platform", "darwin")
    monkeypatch.setattr(setup_module.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(setup_module.shutil, "which", lambda _: "/mock/codex")
    monkeypatch.setattr(setup_module, "configure_key", lambda _: None)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if "--doctor" in args and doctor_fails:
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(setup_module.subprocess, "run", run)
    if doctor_fails:
        with pytest.raises(subprocess.CalledProcessError):
            setup_module.main()
        assert len(calls) == 2
    else:
        setup_module.main()
        assert calls[-2] == ["/mock/codex", "plugin", "marketplace", "add", str(repo)]
        assert calls[-1] == ["/mock/codex", "plugin", "add", "jev-browser-plugin@jev-in-the-loop"]
