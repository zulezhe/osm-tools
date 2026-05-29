# Map-first UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the OSM Tool frontend into a readable map-first workbench without changing backend behavior.

**Architecture:** Keep the existing React/Vite/Tailwind structure. Centralize visual tokens and base classes in `frontend/src/index.css`, update the app shell in `frontend/src/App.tsx`, and polish shared controls plus the download page.

**Tech Stack:** React 19, Vite, TypeScript, Tailwind CSS v4, Leaflet, lucide-react.

---

## File Structure

- Modify `frontend/src/index.css`: design tokens, global base styling, Leaflet control polish, reusable utility classes.
- Modify `frontend/src/App.tsx`: navigation labels, icons, active states, and workbench layout.
- Modify `frontend/src/components/FileSelector.tsx`: readable labels, better input/button styling.
- Modify `frontend/src/components/TaskTable.tsx`: readable statuses, progress display, actions, empty state.
- Modify `frontend/src/pages/DownloadPage.tsx`: repair Chinese text, improve map floating panels, tool buttons, settings, and task drawer.
- Optionally touch other pages only to repair broken Chinese labels or JSX syntax if the build requires it.

## Tasks

### Task 1: Establish visual foundation

- [ ] Update `frontend/src/index.css` with neutral workbench colors, font smoothing, focus states, panel shadows, and Leaflet control styling.
- [ ] Run `npm run build` from `frontend`; expect any remaining failures to point to JSX/text issues outside the CSS.

### Task 2: Polish app shell

- [ ] Update `frontend/src/App.tsx` to use readable Chinese navigation labels and lucide icons.
- [ ] Keep page switching state local and preserve all existing page components.
- [ ] Run `npm run build` from `frontend`; expect App shell type checks to pass.

### Task 3: Polish shared controls

- [ ] Update `frontend/src/components/FileSelector.tsx` with readable "浏览" text, icon button styling, placeholder handling, and focus states.
- [ ] Update `frontend/src/components/TaskTable.tsx` with readable status labels, progress bars, compact action buttons, and empty state.
- [ ] Run `npm run build` from `frontend`; expect shared component type checks to pass.

### Task 4: Polish download map workspace

- [ ] Update `frontend/src/pages/DownloadPage.tsx` text, icons, panel styling, download button, query preview, import panel, Geofabrik panel, draw hints, and task drawer.
- [ ] Preserve existing refs, Leaflet drawing behavior, API calls, and task actions.
- [ ] Run `npm run build` from `frontend`; expect the download page to type check.

### Task 5: Repair build blockers in sibling pages

- [ ] If the build reports corrupted JSX or unterminated strings in other frontend pages, repair only the affected labels and syntax.
- [ ] Do not redesign those pages beyond readability and build correctness.
- [ ] Run `npm run build` from `frontend`; expect a successful production build.

### Task 6: Browser verification

- [ ] Start the Vite dev server if needed.
- [ ] Open the app in a browser and capture a screenshot of the download page.
- [ ] Check desktop and a narrower viewport for text overlap, blank map area, and incoherent panel stacking.

### Task 7: Commit and push

- [ ] Review `git status --short`.
- [ ] Stage only the UI polish files, design/plan docs, and any directly required frontend files.
- [ ] Commit with `feat: polish map-first frontend ui`.
- [ ] Push the current branch to its remote upstream, or `origin main` if no upstream is configured.

## Self-review

This plan covers all design requirements: readable text, map-first download workspace, app shell polish, shared controls, build verification, and remote push. It intentionally excludes backend and workflow changes.
