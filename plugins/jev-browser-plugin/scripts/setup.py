"""Interactive end-user setup: run through uv with locked runtime dependencies."""

import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def configure_key(path):
    """Preserve existing settings and collect a missing key without echoing it."""
    if path.is_symlink():
        raise ValueError("The key file must be a regular file, not a symbolic link.")
    if path.exists() and dotenv_values(path).get("TYPESAFE_API_KEY"):
        path.chmod(0o600)
        print(f"Using existing key file: {path}")
        return
    key = getpass.getpass("TypeSafe API key (hidden input): ").strip()
    if not key or not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
        raise ValueError("Enter a non-empty API key using letters, numbers, _, . or -.")
    original = path.read_text() if path.exists() else ""
    lines = original.splitlines(keepends=True)
    lines = [line for line in lines if not re.match(r"\s*(?:export\s+)?TYPESAFE_API_KEY\s*=", line)]
    text = "".join(lines)
    if text and not text.endswith("\n"):
        text += "\n"
    text += f"TYPESAFE_API_KEY={key}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Set private permissions before writing any credential bytes.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(text)
    print(f"Key saved locally: {path}")


def main():
    if sys.platform != "darwin":
        raise ValueError("This setup wizard currently supports macOS.")
    codex = shutil.which("codex")
    if not codex:
        raise ValueError("Enable/install the Codex CLI, then run this command again.")
    marketplace = ROOT.parents[1]
    if not (marketplace / ".agents/plugins/marketplace.json").is_file():
        raise ValueError("Use the full repository or the *-codex.zip release bundle.")
    subprocess.run([codex, "plugin", "add", "--help"], check=True, stdout=subprocess.DEVNULL)
    print("Jev-in-the-Loop: Browser — Codex plugin setup")
    print("Jev usage is billed by TypeSafe. Task and page data are sent to TypeSafe.")
    configure_key(Path.home() / ".config/jev-browser/config.env")
    print("\nOpen Chrome and follow the connection instructions below.")
    doctor = Path(sys.executable).parent / "browser-harness"
    if not doctor.is_file():
        raise ValueError("Run this wizard through uv as shown in the installation guide.")
    subprocess.run([str(doctor), "--doctor"], check=True, cwd=ROOT)
    subprocess.run([codex, "plugin", "marketplace", "add", str(marketplace)], check=True)
    subprocess.run([codex, "plugin", "add", "jev-browser-plugin@jev-in-the-loop"], check=True)
    print("\nInstalled. Start a new Codex task with the plugin enabled and say: Use Jev to…")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Setup stopped: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled. Run the same command to continue.", file=sys.stderr)
        sys.exit(1)
