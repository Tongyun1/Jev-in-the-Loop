"""Export an allowlisted Codex plugin source ZIP. Never upload or copy local credentials/artifacts."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    ".gitignore",
    ".env.example",
    ".mcp.json",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "README_ZH.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    "CHANGELOG.md",
}
TREES = {
    "src": {".py", ".js"},
    "tests": {".py", ".json", ".html"},
    "scripts": {".py", ".sh"},
    "skills": {".md", ".yaml"},
    "docs": {".md"},
    ".codex-plugin": {".json"},
    ".github": {".yml"},
}


def release_files(root=ROOT):
    files = [root / name for name in sorted(ROOT_FILES)]
    for tree, suffixes in TREES.items():
        files.extend(
            p
            for p in (root / tree).rglob("*")
            if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts
        )
    for p in files:
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Unsafe or missing release file: {p.name}")
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="release/jev-browser-plugin-alpha-source.zip")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = release_files()
    manifest = {}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            archive.writestr("jev-browser-plugin/" + name, content)
            manifest[name] = hashlib.sha256(content).hexdigest()
        archive.writestr("jev-browser-plugin/SOURCE_MANIFEST.json", json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                "archive": str(output.resolve()),
                "files": len(files),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
