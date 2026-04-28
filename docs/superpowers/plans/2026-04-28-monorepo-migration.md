# Monorepo Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the Technology Forecasting analysis pipeline into an Enterprise Nx Monorepo with `@nxlv/python` and `@nx/vite` without losing history or breaking existing outputs.

**Architecture:** We use an integrated Nx monorepo where Python packages are managed by `uv` and frontend by `pnpm`. `libs/shared-python` will hold workspace-aware path resolution to eliminate `../../` relative path hacks. The `scripts/` directory will be dismantled into two apps: `apps/bibliometric-pipeline` (pure Python) and `apps/g6-networks` (hybrid Python/TS).

**Tech Stack:** Nx, pnpm, uv, Python 3.11+, TypeScript, Vite, Plotly, Matplotlib, NetworkX.

---

### Task 1: Create `libs/shared-python`

**Files:**
- Create: `libs/shared-python/src/shared_python/paths.py`
- Modify: `libs/shared-python/pyproject.toml`
- Modify: `pnpm-workspace.yaml` (ensure libs/* is included)

- [ ] **Step 1: Generate the shared-python library**

```bash
pnpm nx generate @nxlv/python:uv-project shared-python --projectType=library --directory=libs/shared-python --srcDir=true --buildSystem=uv --linter=ruff
```

- [ ] **Step 2: Implement dynamic path resolution**

Use the `write` tool to create `libs/shared-python/src/shared_python/paths.py`:

```python
import os
from pathlib import Path

def get_workspace_root() -> Path:
    """Find the root of the workspace by looking for nx.json."""
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "nx.json").exists():
            return current
        current = current.parent
    # Fallback if somehow not found
    return Path(os.getcwd()).resolve()

WORKSPACE_ROOT = get_workspace_root()
DATA_SOURCE_DIR = WORKSPACE_ROOT / "data_source"
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
PLOTS_DIR = WORKSPACE_ROOT / "plots"

def get_data_path(filename: str) -> Path:
    return DATA_SOURCE_DIR / filename

def get_output_path(app_name: str, filename: str) -> Path:
    out_dir = OUTPUTS_DIR / app_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename

def get_plot_path(app_name: str, filename: str) -> Path:
    plot_dir = PLOTS_DIR / app_name
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir / filename
```

- [ ] **Step 3: Update `pyproject.toml` for the library**

Use the `bash` tool to append dependencies to `libs/shared-python/pyproject.toml` using `uv add` (note: `uv add` must run in the project dir):

```bash
cd libs/shared-python && uv add pandas openpyxl
```

- [ ] **Step 4: Commit**

```bash
git add libs/shared-python
git commit -m "feat: create shared-python library with path resolution"
```

---

### Task 2: Create `apps/bibliometric-pipeline`

**Files:**
- Create: `apps/bibliometric-pipeline/project.json` (modified targets)
- Modify: `apps/bibliometric-pipeline/pyproject.toml`
- Move: `scripts/bibliometric_networks/*.py` -> `apps/bibliometric-pipeline/src/bibliometric_pipeline/`

- [ ] **Step 1: Generate the bibliometric-pipeline app**

```bash
pnpm nx generate @nxlv/python:uv-project bibliometric-pipeline --projectType=application --directory=apps/bibliometric-pipeline --srcDir=true --buildSystem=uv --linter=ruff
```

- [ ] **Step 2: Add dependencies**

Run these commands to add dependencies and the local workspace reference to `shared-python`.
*(Note: `@nxlv/python` supports workspace dependencies natively through the nx workspace).*

```bash
cd apps/bibliometric-pipeline && uv add pandas numpy networkx matplotlib plotly openpyxl && uv add --editable ../../libs/shared-python
```

- [ ] **Step 3: Move Python scripts**

```bash
mv scripts/bibliometric_networks/01_extract_data.py apps/bibliometric-pipeline/src/bibliometric_pipeline/extract.py
mv scripts/bibliometric_networks/02_build_networks.py apps/bibliometric-pipeline/src/bibliometric_pipeline/build.py
mv scripts/bibliometric_networks/03_visualize_networks.py apps/bibliometric-pipeline/src/bibliometric_pipeline/visualize.py
```

- [ ] **Step 4: Refactor `extract.py` imports and paths**

Use the `edit` tool on `apps/bibliometric-pipeline/src/bibliometric_pipeline/extract.py`.

Replace this block:
```python
# ---------------------------------------------------------------------------
# CONFIGURABLE PARAMETERS
# ---------------------------------------------------------------------------
CONFIG = {
    "data_path": Path("../../data_source/wos_filtered_bibliography.xlsx"),
    "output_dir": Path("../../outputs/bibliometric_networks"),
}

# ---------------------------------------------------------------------------
# Resolve paths -- data_source/ lives in the main repo root (gitignored,
# so it is NOT present in worktrees). Walk up from script to find root.
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
_repo_root = SCRIPT_DIR
while not (_repo_root / "data_source").exists() and _repo_root.parent != _repo_root:
    _repo_root = _repo_root.parent
if not (_repo_root / "data_source").exists():
    raise FileNotFoundError("Cannot locate data_source/ -- run from the main repo or a worktree that has access to it")

CONFIG["data_path"] = (_repo_root / "data_source" / "wos_filtered_bibliography.xlsx").resolve()
CONFIG["output_dir"] = (SCRIPT_DIR / CONFIG["output_dir"]).resolve()
CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)
```

With this block:
```python
from shared_python.paths import get_data_path, get_output_path

CONFIG = {
    "data_path": get_data_path("wos_filtered_bibliography.xlsx"),
    "output_dir": get_output_path("bibliometric_networks", "").parent,
}
```

- [ ] **Step 5: Apply similar path refactoring to `build.py` and `visualize.py`**

For both `build.py` and `visualize.py`, use the `edit` tool to replace their manual path resolution (`_repo_root` walking) with imports from `shared_python.paths` as done in Step 4. Ensure `data_path` and `output_dir` use `get_data_path` and `get_output_path`/`get_plot_path`.

*(If the agent needs to read them first, use the `read` tool to find the exact old string to replace).*

- [ ] **Step 6: Update Nx targets in `project.json`**

Use the `edit` tool or a python script to modify `apps/bibliometric-pipeline/project.json`. Ensure the `targets` block includes:
```json
    "extract": {
      "command": "uv run python -m bibliometric_pipeline.extract",
      "options": { "cwd": "apps/bibliometric-pipeline" }
    },
    "build": {
      "command": "uv run python -m bibliometric_pipeline.build",
      "dependsOn": ["extract"],
      "options": { "cwd": "apps/bibliometric-pipeline" }
    },
    "visualize": {
      "command": "uv run python -m bibliometric_pipeline.visualize",
      "dependsOn": ["build"],
      "options": { "cwd": "apps/bibliometric-pipeline" }
    }
```

- [ ] **Step 7: Commit**

```bash
git add apps/bibliometric-pipeline
git rm scripts/bibliometric_networks/01_extract_data.py scripts/bibliometric_networks/02_build_networks.py scripts/bibliometric_networks/03_visualize_networks.py
git commit -m "feat: migrate bibliometric_networks scripts to bibliometric-pipeline app"
```

---

### Task 3: Create `apps/g6-networks`

**Files:**
- Create: `apps/g6-networks/project.json`
- Move: `scripts/g6_networks/*` -> `apps/g6-networks/`

- [ ] **Step 1: Generate the g6-networks Python app**

```bash
pnpm nx generate @nxlv/python:uv-project g6-networks --projectType=application --directory=apps/g6-networks --srcDir=false --buildSystem=uv --linter=ruff
```

*(Note: `--srcDir=false` so the root of the app can easily house the Vite frontend).*

- [ ] **Step 2: Move existing frontend and export script**

```bash
mv scripts/g6_networks/export_g6_data.py apps/g6-networks/export_g6_data.py
mv scripts/g6_networks/src apps/g6-networks/src
mv scripts/g6_networks/pages apps/g6-networks/pages
mv scripts/g6_networks/vite.config.ts apps/g6-networks/vite.config.ts
mv scripts/g6_networks/tsconfig.json apps/g6-networks/tsconfig.json
```

- [ ] **Step 3: Setup Node dependencies**

Use `write` to create `apps/g6-networks/package.json`:

```json
{
  "name": "g6-networks",
  "version": "1.0.0",
  "scripts": {
    "build": "vite build",
    "dev": "vite"
  },
  "devDependencies": {
    "typescript": "^6.0.3",
    "vite": "^8.0.10"
  },
  "dependencies": {
    "@antv/g6": "^5.1.0"
  }
}
```

Run `pnpm install` in the workspace root.

- [ ] **Step 4: Refactor Python dependencies & script**

```bash
cd apps/g6-networks && uv add pandas networkx numpy matplotlib && uv add --editable ../../libs/shared-python
```

Use `edit` to refactor `apps/g6-networks/export_g6_data.py` to use `shared_python.paths` for resolving `outputs/bibliometric_networks` (input data) and `apps/g6-networks/src/data` (output data), replacing relative path walking.

- [ ] **Step 5: Update `project.json`**

Use `edit` to add these targets to `apps/g6-networks/project.json`:
```json
    "export-data": {
      "command": "uv run python export_g6_data.py",
      "dependsOn": ["bibliometric-pipeline:build"],
      "options": { "cwd": "apps/g6-networks" }
    },
    "build": {
      "executor": "@nx/vite:build",
      "dependsOn": ["export-data"],
      "options": {
        "outputPath": "dist/apps/g6-networks"
      }
    }
```

- [ ] **Step 6: Commit**

```bash
git add apps/g6-networks pnpm-lock.yaml
git commit -m "feat: migrate g6_networks to hybrid app"
```

---

### Task 4: Clean up & Verify

- [ ] **Step 1: Clean root directory**

```bash
rm -rf scripts/bibliometric_networks scripts/g6_networks
git add scripts
git commit -m "chore: remove old scripts directory"
```

- [ ] **Step 2: Verify pipeline**

```bash
pnpm nx run bibliometric-pipeline:extract
pnpm nx run g6-networks:build
```
Ensure there are no errors. Fix any missing imports if they arise during execution.
