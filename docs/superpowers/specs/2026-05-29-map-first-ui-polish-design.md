# Map-first UI Polish Design

## Goal

Improve the OSM Tool frontend UI while preserving the current map-first workflow and backend API contracts.

## Scope

- Fix corrupted Chinese UI text in the React frontend.
- Keep the download page as a full-screen map workspace.
- Polish floating map controls, download settings, import and region panels, and the task drawer.
- Improve the global app shell with clearer navigation, icons, active state, and a restrained workbench look.
- Unify common controls such as file selectors, task tables, progress bars, status labels, and empty states.

## Out of Scope

- Backend API changes.
- New download, extraction, conversion, processing, splitting, or publishing behavior.
- New UI frameworks.
- Large information architecture changes.

## Architecture

The frontend remains a Vite React app using Tailwind CSS and `lucide-react`. The UI polish is implemented with local component and page changes instead of introducing a design system package. Shared visual behavior lives in `frontend/src/index.css`, `frontend/src/App.tsx`, `frontend/src/components/FileSelector.tsx`, and `frontend/src/components/TaskTable.tsx`.

## User Experience

The app opens into a compact desktop workbench. The left navigation gives each workflow a recognizable icon and a clear active state. The download page uses the map as the main canvas, with floating panels for tool selection, region/import details, download configuration, and task status. Panels use consistent spacing, shadows, borders, button states, and readable Chinese labels.

## Error Handling

Existing API error handling stays in place. User-facing alert text is repaired so failures are understandable. Disabled buttons and helper text explain when required inputs are missing.

## Testing

Run the frontend build to catch TypeScript and JSX issues. If the backend server is not running, browser verification can still validate static layout through the Vite dev server; API-backed content may remain empty.
