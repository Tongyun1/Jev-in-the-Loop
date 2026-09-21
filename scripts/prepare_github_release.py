"""Prepare (never publish) a Codex marketplace ZIP, checksums and release notes."""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/jev-browser-plugin"


def prepare(output):
    output = output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Keep release artifacts outside the repository")
    spec = importlib.util.spec_from_file_location("release", PLUGIN / "scripts/package_release.py")
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    metadata = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    version = metadata["version"]
    if not re.fullmatch(r"[0-9A-Za-z.-]+", version):
        raise ValueError("Unsafe version")
    catalog_path = ROOT / ".agents/plugins/marketplace.json"
    catalog = json.loads(catalog_path.read_text())
    entry = next(p for p in catalog["plugins"] if p["name"] == metadata["name"])
    assert catalog["name"] == "jev-in-the-loop"
    assert entry["source"] == {"source": "local", "path": "./plugins/jev-browser-plugin"}
    paths = [catalog_path, *release.release_files(PLUGIN)]
    contents = {}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Unsafe source: {path.name}")
        data = path.read_bytes()
        # Refuse common credential signatures and author-local absolute paths.
        patterns = [rb"gh[pousr]_[A-Za-z0-9]{20,}", rb"github_pat_[A-Za-z0-9_]{20,}",
                    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                    rb"/Users/zmm/", rb"TYPESAFE_API_KEY\s*=\s*['\"]?(?!your|example)[A-Za-z0-9_-]{20,}"]
        if any(re.search(pattern, data) for pattern in patterns):
            raise ValueError(f"Possible private data in {path.relative_to(ROOT)}")
        contents[path.relative_to(ROOT).as_posix()] = data
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    build = {"version": version, "base_commit": commit, "uncommitted_changes": dirty,
             "status": "release candidate; not published", "files": manifest}
    contents["SOURCE_MANIFEST.json"] = (json.dumps(build, indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=False)
    archive = output / f"jev-browser-plugin-{version}-codex.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo("Jev-in-the-Loop/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for name, digest in manifest.items():
            assert hashlib.sha256(bundle.read("Jev-in-the-Loop/" + name)).hexdigest() == digest
        assert all(n.startswith("Jev-in-the-Loop/") and ".." not in Path(n).parts for n in bundle.namelist())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    notes = f"""# Jev-in-the-Loop: Browser {version} (Alpha)

A Codex plugin for ultrafast browser interaction, powered by Jev and local Chrome.
Browser is the first module of Jev-in-the-Loop.

## Install

1. Download `{archive.name}` and `SHA256SUMS` from this release.
2. On macOS, verify with `shasum -a 256 -c SHA256SUMS`, then extract the ZIP.
3. Follow `Jev-in-the-Loop/plugins/jev-browser-plugin/README.md` (or `README_ZH.md`).
   The bundle includes a Codex marketplace catalog; no developer helpers are required.

Requires macOS, Codex with CLI plugin support, Chrome, uv, and your own TypeSafe API key.
The archive contains plugin source, not Python, installed dependencies, or credentials.
First launch needs network access to obtain the locked runtime dependencies.
Jev API usage is billed by TypeSafe; tasks and visible page data are sent to TypeSafe.
Use public, non-sensitive pages and stop before irreversible actions.

## Release checklist (maintainer: complete before publishing)

- [ ] Commit the distribution files and rebuild from a clean checkout.
- [ ] Record offline test results and package verification.
- [ ] Verify fresh-profile Codex installation and a public-page smoke test on macOS.
- [ ] Create a version tag pointing at that exact commit and upload ZIP + SHA256SUMS.

Candidate base commit: `{commit}`; uncommitted changes: `{str(dirty).lower()}`.
This file and archive are prepared locally. Nothing has been published by the packaging script.
"""
    (output / "release-notes.md").write_text(notes)
    print(json.dumps({"archive": str(archive), "sha256": digest, "files": len(manifest),
                      "base_commit": commit, "uncommitted_changes": dirty}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory outside repo")
    prepare(parser.parse_args().output_dir)
