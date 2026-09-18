# Phase completion and verification

The five phases were implemented in order in a new workspace; no legacy source was provided.

| Phase | Status | Acceptance evidence |
|---|---|---|
| 1. Foundation | Complete | Windows uv installation, local NiceGUI shell, actual subprocess worker, valid block, browser preview and STEP download |
| 2. Geometry library | Complete | Six defaults and all presets valid; STEP reimport dimensions/volumes; explicit 2D profile with SVG/DXF; invalid input tests |
| 3. Workspace | Complete | Native Python-authored controls, fit/standard views, automatic updates, cancellation, retained preview, stale-result browser test |
| 4. Persistence | Complete | SQLite revisions, project duplication, import/export recipes, restore after reconnect, new service instance restores artifacts after cache deletion |
| 5. Verification | Complete | 41 geometry/application tests and 9 browser workflows passed; lint and locked install passed; screenshot and benchmark included |

## Evidence

- `uv sync --locked`: succeeded with Python 3.13.7 on Windows.
- Geometry/application suite: 40 passed in 38.59 seconds, followed by the additional default-Windows-path regression and overlap check (2 passed; one existing, one new). Total distinct geometry/application cases: 41.
- Browser suite: 9 passed in 91.67 seconds using installed Chrome. Captured page errors: none.
- `ruff check src tests`: passed.
- `workspace.png`: visually inspected after correcting ground-plane clipping and glTF's default metallic material.
- `benchmark.json`: measured timings and sampled memory, reproducible via `tests/benchmark.py`.

Browser workflows exercise all six models, STEP download, saved revision restoration after reload, recipe import, capability-aware 2D exports, stale jobs, automatic updates, cancellation, and small-screen controls. The data/service test also reconstructs the project service from disk and regenerates a recipe after deleting the cache.

## Practical boundaries

- Only Windows / Python 3.13.7 / Chrome have been verified.
- Side panels wrap and are manually collapsible on narrow screens.
- NACA boundaries use a cosine-sampled polygon, documented in README; smooth spline and aerodynamic verification are not included.
- The cache protects active results, so its target size may be exceeded while those results are displayed. Saved artifacts have no automatic retention policy.
- Memory measurements are short diagnostic samples, not a sustained soak test.
- Forced OS termination may leave unpublished staging directories. Normal cancellation, timeouts, and shutdown clean up workers.
- No custom JavaScript is maintained. NiceGUI supplies browser internals; GLB material adjustment is written in Python.
- No legacy cleanup was possible or necessary in the supplied empty workspace.

## Viewer refresh follow-up

The viewer now awaits GLB readiness, retains the previous result during asset loading, refreshes the drawing surface, and guards against stale results during that loading step. Fit on update is optional; the scene targets 60 FPS. All 12 distinct browser workflows were verified (11 passed in the broader run; the corrected new refresh regression plus three related workflows passed in the targeted run). Ruff passed. See `VIEWER.md` for the VTK assessment.
