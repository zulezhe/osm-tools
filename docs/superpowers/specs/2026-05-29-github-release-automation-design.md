# GitHub Release Automation Design

## Goal

Add GitHub Actions automation that builds OSM Tool for Windows and macOS on every `main` commit and publishes a GitHub Release when a `v*` tag is pushed.

## Release Rules

- Push to `main`: build Windows and macOS packages and upload them as workflow artifacts.
- Manual workflow dispatch: build Windows and macOS packages and upload them as workflow artifacts.
- Push tag matching `v*`: build Windows and macOS packages, create a GitHub Release for that tag, and attach both platform packages.

## Build Strategy

Each platform builds on its native GitHub-hosted runner. The workflow installs Python, Node, and `uv`, restores npm cache via `setup-node`, installs Python dependencies with the dev group, builds the Vite frontend, then runs PyInstaller.

## Packaging Strategy

The PyInstaller spec is made cross-platform by using `os.path.join` paths, platform-specific pywebview hidden imports, and optional UPX only when the local UPX directory exists. The workflow renames outputs to stable release asset names:

- `osm-tool-windows-x64.exe`, zipped as `osm-tool-windows-x64.zip`
- `osm-tool-macos-x64`, archived as `osm-tool-macos-x64.tar.gz`

## Permissions

The workflow uses GitHub's built-in token. It grants `contents: write` so the tag job can create releases and upload assets.

## Out of Scope

- Code signing or notarization.
- Auto-generating semantic version numbers.
- Publishing on every non-tag commit as a formal Release.
- Changing application runtime behavior.

## Verification

Local verification checks YAML syntax structurally, validates the PyInstaller spec can be compiled by Python, and confirms frontend production build still succeeds. Full Windows/macOS packaging is verified by GitHub Actions after pushing.
