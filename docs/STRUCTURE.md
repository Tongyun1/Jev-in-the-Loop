# Project structure

`Jev-in-the-Loop` is the umbrella project. Browser is its Codex plugin; Living Melody is its
standalone web playground. Future modules can be added when concrete implementations exist;
empty placeholder modules are omitted.

The repository root owns project identity, contribution guidance, shared notices, CI and source packaging.
`plugins/jev-browser-plugin/` is a self-contained Codex plugin root. It owns its manifest, runtime,
dependencies, lockfile, skill, tests and installation instructions. The folder matches the stable
manifest ID `jev-browser-plugin`; human-facing branding is independent of that ID.

`playgrounds/living-melody/` is a self-contained browser experiment, not a Codex plugin. It owns
its Python local server, static Tone.js/Three.js interface, offline Node tests, documentation and
demo media. It has no runtime dependency on Browser or on another checkout. Its TypeSafe key is
read only from the process environment; starting without one uses local music rules.

The public repository does not contain a parent workspace, development archives, upstream Git clones,
personal skills, translated research notes, local credentials, virtual environments, private recordings or
historical build outputs. Browser uses its lockfile; Living Melody uses Python's standard library
and pinned browser CDN imports.

The browser runtime derives from Jev Ultrafast. Its upstream repository is a reference, not a runtime
dependency on an adjacent checkout. Preserve the MIT attribution in both the repository and plugin package.
