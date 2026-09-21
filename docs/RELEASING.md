# Source release preparation

The Git repository root is this project's root, not a surrounding local workspace. The Codex plugin
root is `plugins/jev-browser-plugin/`. Keep that distinction when installing or distributing it.

1. Run the offline checks and build described in the root and Browser READMEs.
2. From the repository root, run `python3 scripts/package_source.py --output /path/outside/repo/source.zip`.
   This exports the project documentation and allowlisted plugin sources with a SHA-256 manifest.
3. For a standalone plugin source ZIP, run the Browser module's `scripts/package_release.py` instead.
4. Inspect the archive and manifest. Check for credentials, private paths, browser captures and local data.
   Keep build products outside the source candidate; never ZIP a surrounding development workspace.
5. Confirm upstream license notices are present. Record what was actually tested.
6. Establish the real hosting URL and distribution mechanism before documenting public install commands.

Neither packaging script uploads, commits, installs, creates a repository or publishes a release.
Existing output files are not overwritten. See the [Browser release checklist](../plugins/jev-browser-plugin/docs/RELEASING.md)
for module-specific limitations.
