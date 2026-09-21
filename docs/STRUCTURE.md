# Project structure

`Jev-in-the-Loop` is the umbrella project. `Jev-in-the-Loop: Browser` is its first implemented module.
Future modules can be added when concrete implementations exist; empty placeholder modules are omitted.

The repository root owns project identity, contribution guidance, shared notices, CI and source packaging.
`plugins/jev-browser-plugin/` is a self-contained Codex plugin root. It owns its manifest, runtime,
dependencies, lockfile, skill, tests and installation instructions. The folder matches the stable
manifest ID `jev-browser-plugin`; human-facing branding is independent of that ID.

The public repository does not contain a parent workspace, development archives, upstream Git clones,
personal skills, translated research notes, local credentials, virtual environments, recordings or
historical build outputs. Dependencies are reproduced through the module's lockfile.

The browser runtime derives from Jev Ultrafast. Its upstream repository is a reference, not a runtime
dependency on an adjacent checkout. Preserve the MIT attribution in both the repository and plugin package.
