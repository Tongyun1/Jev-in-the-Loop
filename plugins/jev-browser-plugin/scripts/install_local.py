"""Install this reviewed local plugin through Codex's personal marketplace helpers."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Developer-only personal-marketplace installation")
    parser.add_argument("--env-file", help="Optional explicit absolute credential-file path; never copied")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    name = "jev-browser-plugin"
    helper = Path.home() / ".codex/skills/.system/plugin-creator/scripts"
    destination = Path.home() / "plugins" / name
    if not (helper / "create_basic_plugin.py").is_file():
        raise SystemExit(
            "Codex plugin-creator helpers unavailable. This developer installer is optional; "
            "see README for Codex plugin packaging and distribution requirements."
        )
    marketplace = subprocess.check_output(
        [sys.executable, str(helper / "read_marketplace_name.py")], text=True
    ).strip()
    subprocess.run([sys.executable, str(helper / "validate_plugin.py"), str(root)], check=True)
    env_file = args.env_file
    if destination.exists():
        marker = destination / ".jev-local-install"
        if not marker.is_file() or marker.read_text().strip() != str(root):
            raise SystemExit("Destination is not managed by this project; nothing overwritten.")
        if not env_file and (destination / ".mcp.json").is_file():
            previous = json.loads((destination / ".mcp.json").read_text())
            env_file = (
                previous.get("mcpServers", {}).get("jev-browser", {}).get("env", {}).get("JEV_ENV_FILE")
            )
    if env_file and (not Path(env_file).is_absolute() or not Path(env_file).is_file()):
        raise SystemExit("Credential file must be an existing absolute path")
    subprocess.run(
        [
            sys.executable,
            str(helper / "create_basic_plugin.py"),
            name,
            "--with-marketplace",
            "--with-skills",
            "--with-mcp",
            "--force",
        ],
        check=True,
    )
    for folder in (".codex-plugin", "skills", "src", "docs"):
        shutil.copytree(
            root / folder,
            destination / folder,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for filename in (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "README_ZH.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "SECURITY.md",
    ):
        shutil.copy2(root / filename, destination / filename)
    (destination / "scripts").mkdir(exist_ok=True)
    shutil.copy2(root / "scripts/launch.sh", destination / "scripts/launch.sh")
    (destination / "scripts/launch.sh").chmod(0o755)
    config = json.loads((root / ".mcp.json").read_text())
    if env_file:
        config["mcpServers"]["jev-browser"]["env"] = {"JEV_ENV_FILE": env_file}
    (destination / ".mcp.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    (destination / ".jev-local-install").write_text(str(root) + "\n")
    subprocess.run([sys.executable, str(helper / "validate_plugin.py"), str(destination)], check=True)
    # Use the helper instead of hand-editing marketplace or config.toml; force new cache pickup.
    subprocess.run(
        [sys.executable, str(helper / "update_plugin_cachebuster.py"), str(destination)],
        check=True,
    )
    subprocess.run(["codex", "plugin", "add", f"{name}@{marketplace}", "--json"], check=True)


if __name__ == "__main__":
    main()
