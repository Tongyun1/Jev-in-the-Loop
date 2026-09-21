# Source release preparation

## GitHub plugin distribution

The repository catalog is `.agents/plugins/marketplace.json`, named `jev-in-the-loop`.
It exposes `plugins/jev-browser-plugin` using a relative path. Keep that layout in
the distribution ZIP. It is a Codex plugin source bundle, not a standalone app.

From the repository root:

```sh
python3 scripts/prepare_github_release.py --output-dir /path/outside/repo/new-release
```

The new output directory contains a versioned `*-codex.zip`, `SHA256SUMS`, and
`release-notes.md`. The builder verifies per-file hashes, the marketplace target,
archive integrity, and common credential/author-path signatures. Manually review
the source too; signature checks are not a comprehensive secret scanner.

Before publishing, commit the distribution changes and regenerate from a clean
checkout, run offline tests, and test installation in a fresh Codex profile on
macOS. Create a matching version tag at the tested commit, then create a GitHub
pre-release and attach the ZIP plus `SHA256SUMS`. Complete the checklist in the
generated notes before using them as public release text. Never ship a candidate
with uncommitted changes recorded in its manifest.

Once the catalog is pushed, Git users can register the GitHub marketplace:

```sh
codex plugin marketplace add Tongyun1/Jev-in-the-Loop
codex plugin add jev-browser-plugin@jev-in-the-loop
```

For a versioned release, pass `--ref <published-tag>` to the first command.
ZIP users register the extracted `Jev-in-the-Loop` directory instead. The bilingual
plugin READMEs cover TypeSafe credentials, Chrome setup, and local installation.
GitHub's automatic source archives and the older standalone `*-source.zip` are not
the curated `*-codex.zip`: keep those names distinct in release instructions.

References: [official plugin documentation](https://developers.openai.com/plugins/build/plugins).

## Full project source archive

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
