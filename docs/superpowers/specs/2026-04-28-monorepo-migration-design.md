# Monorepo Migration Design

## Goal
Rewrite and restructure the Technology Forecasting repository into an enterprise-grade Nx monorepo using `@nxlv/python` for Python support and `@nx/vite` for the TypeScript frontend.

## Scope
1. **Initialize Workspace**: pnpm, Nx, and plugins (`@nxlv/python`, `@nx/vite`, `@nx/js`).
2. **Library Extraction**: Create `libs/shared-python` for dynamic path resolution and data loading helpers.
3. **Application Refactoring**:
   - `apps/bibliometric-pipeline` (Python): Consolidate Phase 1, 2, and 3 extraction/building/visualization scripts.
   - `apps/g6-networks` (Hybrid Python/TS): Consolidate the python export script and the Vite TS frontend.
4. **Data Preservation**: Keep `data_source/`, `outputs/`, and `plots/` at root to minimize git history churn and avoid large file migrations.

## Architecture

### 1. Workspace Configuration
- **Package Managers**: `pnpm` (Node/TS workspace) and `uv` (Python fast environment).
- **Core Manifests**: `package.json`, `pnpm-workspace.yaml`, `nx.json`.

### 2. Core Components
#### `libs/shared-python`
- Exposes `get_workspace_root()` dynamically derived from the `.git` or `nx.json` directory.
- Exposes `data.py` (canonical dataset loaders) and `canonical.py` (canonicalization maps).
- Fixes all `../../` relative path hacks currently used in scripts.

#### `apps/bibliometric-pipeline`
- Python application managed by `uv`.
- Consolidates `01_extract_data.py`, `02_build_networks.py`, and `03_visualize_networks.py` under `src/bibliometric_pipeline/`.
- Nx targets: `extract`, `build`, `visualize` mapping to `uv run python -m bibliometric_pipeline.<module>`.

#### `apps/g6-networks`
- Hybrid app with Python and TypeScript.
- **Python Target**: `export-data` runs `export_g6_data.py`. Depends on `bibliometric-pipeline:build`.
- **TypeScript Targets**: `build` (Vite build) and `serve`. Depends on `export-data`.

### 3. Dependencies
```
apps/g6-networks (TS/Python) -> apps/bibliometric-pipeline (Python) -> libs/shared-python (Python)
```

## Data Flow
- **Input**: Scripts read from `data_source/` (e.g., `wos_filtered_bibliography.xlsx`).
- **Output**: Scripts write to `outputs/bibliometric_networks/` and `plots/`.
- **G6 Data**: The `export_g6_data.py` script reads from `outputs/bibliometric_networks/` and writes `.json` files to `apps/g6-networks/src/data/`.

## Validation
- Ensure `nx run-many --target=build` correctly builds the pipeline and UI.
- No loose scripts in the root directory. All logic encapsulated within `apps/` or `libs/`.