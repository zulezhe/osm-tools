# GitHub Release Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure GitHub Actions to build Windows/macOS packages on `main` commits and publish GitHub Releases from `v*` tags.

**Architecture:** Add one workflow at `.github/workflows/release.yml` with a matrix build job and a tag-only release job. Update `osm-tool.spec` so PyInstaller packaging works on Windows and macOS from the same spec file.

**Tech Stack:** GitHub Actions, GitHub CLI, Python 3.12, uv, Node 24, npm, Vite, PyInstaller.

---

## File Structure

- Create `.github/workflows/release.yml`: CI build and release workflow.
- Modify `osm-tool.spec`: cross-platform PyInstaller paths, platform-specific hidden imports, optional UPX.
- Create `docs/superpowers/specs/2026-05-29-github-release-automation-design.md`: release automation design record.
- Create `docs/superpowers/plans/2026-05-29-github-release-automation.md`: implementation plan.

## Tasks

### Task 1: Configure remote

- [ ] Run `git remote add origin https://github.com/zulezhe/osm-tools.git`.
- [ ] Run `git remote -v` and confirm fetch and push URLs use `https://github.com/zulezhe/osm-tools.git`.

### Task 2: Add GitHub Actions workflow

- [ ] Create `.github/workflows/release.yml`.
- [ ] Trigger on `push` to `main`, `push` tags matching `v*`, and `workflow_dispatch`.
- [ ] Add a matrix build job for `windows-latest` and `macos-13`.
- [ ] Install Python 3.12, Node 24, uv, npm dependencies, and Python dev dependencies.
- [ ] Build the frontend with `npm run build`.
- [ ] Build the app with `uv run pyinstaller osm-tool.spec --noconfirm --clean`.
- [ ] Package Windows output as `osm-tool-windows-x64.zip`.
- [ ] Package macOS output as `osm-tool-macos-x64.tar.gz` or zip the `.app` if PyInstaller emits one.
- [ ] Upload platform packages as artifacts.
- [ ] Add a release job that only runs for `refs/tags/v*`, downloads artifacts, and runs `gh release create`.

### Task 3: Make PyInstaller spec cross-platform

- [ ] Replace Windows-only script path `src\\osm_tool\\main.py` with `os.path.join('src', 'osm_tool', 'main.py')`.
- [ ] Add hidden imports conditionally based on `sys.platform`.
- [ ] Add optional hidden imports only when modules exist, so missing uncommitted feature modules do not break package analysis.
- [ ] Use `upx_dir=None` when `tools/upx` is not present on the runner.

### Task 4: Verify locally

- [ ] Run `python -m py_compile osm-tool.spec`; expect exit code 0.
- [ ] Run `npm run build` in `frontend`; expect exit code 0.
- [ ] Run `git diff --check -- .github/workflows/release.yml osm-tool.spec`; expect exit code 0.

### Task 5: Commit and push

- [ ] Stage only `.github/workflows/release.yml`, `osm-tool.spec`, the two release automation docs, and remote config is not staged because it lives in Git config.
- [ ] Commit with `ci: add github release automation`.
- [ ] Push `main` to `origin`.

## Self-review

The plan covers artifact builds for regular commits, tag-based formal releases, Windows/macOS native packaging, release permissions, cross-platform PyInstaller changes, and local verification. It excludes signing, notarization, and version generation by design.
