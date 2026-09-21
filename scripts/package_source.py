"""Package the Jev-in-the-Loop source tree without local development data."""

import argparse
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/jev-browser-plugin"
PROJECT_FILES = (
    "README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    ".gitignore", ".github/workflows/offline.yml", "docs/STRUCTURE.md", "docs/RELEASING.md",
    "scripts/package_source.py",
)


def source_files():
    spec = importlib.util.spec_from_file_location("browser_release", PLUGIN / "scripts/package_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = [ROOT / name for name in PROJECT_FILES] + module.release_files(PLUGIN)
    for path in files:
        if not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Missing or unsafe source: {path.relative_to(ROOT)}")
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != ROOT.parent):
            raise ValueError(f"Symlink in source: {path.relative_to(ROOT)}")
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New ZIP path outside the source tree")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        parser.error("Keep release artifacts outside the source tree")
    files = source_files()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            archive.writestr("Jev-in-the-Loop/" + name, content)
            manifest[name] = hashlib.sha256(content).hexdigest()
        archive.writestr("Jev-in-the-Loop/SOURCE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(files), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
