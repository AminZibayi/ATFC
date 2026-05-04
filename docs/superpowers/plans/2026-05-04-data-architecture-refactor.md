# Data Directory Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the workspace to a unified `data/` hierarchy and update code and docs to use it.

**Architecture:** Replace the current split between `data_source/` and `dist/`-backed data outputs with a single `data/` root organized into `raw/`, `intermediate/`, and `outputs/`. Keep Nx caching changes out of scope for this pass.

**Tech Stack:** Python 3.11+, Nx, uv, pathlib, Markdown documentation.

---

### Task 1: Refactor Shared Path Helpers

**Files:**
- Modify: `libs/shared-python/src/shared_python/paths.py`
- Modify: `libs/shared-python/tests/test_hello.py`

- [ ] **Step 1: Write the failing test**

Replace the existing hello test with assertions for the new path helpers:

```python
from shared_python.paths import (
    DATA_DIR,
    get_intermediate_data_path,
    get_output_path,
    get_plot_path,
    get_raw_data_path,
)


def test_shared_paths_under_data_root():
    assert str(get_raw_data_path("sample.xlsx")).endswith(r"data\\raw\\sample.xlsx")
    assert str(get_intermediate_data_path("demo", "items.csv")).endswith(r"data\\intermediate\\demo\\items.csv")
    assert str(get_output_path("demo", "result.json")).endswith(r"data\\outputs\\demo\\result.json")
    assert str(get_plot_path("demo", "plot.png")).endswith(r"data\\outputs\\demo\\plots\\plot.png")
    assert DATA_DIR.name == "data"
```

Run: `pnpm nx test shared-python`
Expected: fail because the new functions do not exist yet.

- [ ] **Step 2: Implement the new helpers**

Replace `libs/shared-python/src/shared_python/paths.py` with:

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
    return Path(os.getcwd()).resolve()


WORKSPACE_ROOT = get_workspace_root()
DATA_DIR = WORKSPACE_ROOT / "data"


def get_raw_data_path(filename: str) -> Path:
    return DATA_DIR / "raw" / filename


def get_intermediate_data_path(app_name: str, filename: str) -> Path:
    out_dir = DATA_DIR / "intermediate" / app_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def get_output_path(app_name: str, filename: str) -> Path:
    out_dir = DATA_DIR / "outputs" / app_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def get_plot_path(app_name: str, filename: str) -> Path:
    plot_dir = DATA_DIR / "outputs" / app_name / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir / filename


def get_data_path(filename: str) -> Path:
    return get_raw_data_path(filename)
```

- [ ] **Step 3: Run the test again**

Run: `pnpm nx test shared-python`
Expected: pass.

- [ ] **Step 4: Commit**

```bash
rtk git add libs/shared-python/src/shared_python/paths.py libs/shared-python/tests/test_hello.py
rtk git commit -m "feat: unify shared data paths under data root"
```

### Task 2: Migrate Raw Data Files

**Files:**
- Move: `data_source/*`
- Create: `data/raw/`

- [ ] **Step 1: Create the target directory**

Run: `rtk ls -la data`
Expected: confirm the parent `data/` directory exists before creating `data/raw/`.

- [ ] **Step 2: Move the files**

Move every existing raw/derived dataset from `data_source/` into `data/raw/`.

Expected layout:
```text
data/raw/
├── cross_technology_mann_kendall_trends.xlsx
├── patents_with_dominant_topic.xlsx
├── patent_lda_topic_keywords.xlsx
├── patent_topic_document_distribution.xlsx
├── patent_topic_mann_kendall_results.xlsx
├── patent_topic_proportions_by_year.xlsx
├── patent_topic_proportions_by_year_no_year_col.xlsx
├── publication_lda_topic_keywords.xlsx
├── publication_stemmed_tokens_for_lda.json
├── publication_topic_document_distribution.xlsx
├── publication_topic_mann_kendall_results.xlsx
├── publication_topic_proportions_by_year.xlsx
├── rename_mapping.yaml
├── wos_category_counts.xlsx
├── wos_filtered_bibliography.xlsx
├── wos_raw_bibliography.xlsx
└── wos_raw_bibliography_fixed.xlsx
```

- [ ] **Step 3: Delete empty source directory**

Remove `data_source/` only after every file has been moved.

- [ ] **Step 4: Commit**

```bash
rtk git add data/raw data_source
rtk git commit -m "chore: relocate raw datasets into data root"
```

### Task 3: Update Bibliometric Pipeline Paths

**Files:**
- Modify: `apps/bibliometric-pipeline/src/bibliometric_pipeline/extract.py`
- Modify: `apps/bibliometric-pipeline/src/bibliometric_pipeline/build.py`
- Modify: `apps/bibliometric-pipeline/src/bibliometric_pipeline/visualize.py`
- Test: `pnpm nx run bibliometric-pipeline:extract`
- Test: `pnpm nx run bibliometric-pipeline:build`
- Test: `pnpm nx run bibliometric-pipeline:visualize`

- [ ] **Step 1: Update the path imports and config**

Replace `get_data_path("wos_filtered_bibliography.xlsx")` with `get_raw_data_path("wos_filtered_bibliography.xlsx")` in `extract.py`, and use `get_intermediate_data_path()` / `get_output_path()` / `get_plot_path()` where the pipeline writes generated files.

- [ ] **Step 2: Implement the refactor**

Use this pattern in `extract.py`:

```python
from shared_python.paths import get_intermediate_data_path, get_raw_data_path

CONFIG = {
    "data_path": get_raw_data_path("wos_filtered_bibliography.xlsx"),
    "output_dir": get_intermediate_data_path("bibliometric-pipeline", "temp").parent,
}
```

Then update file writes:

```python
df_out.to_csv(CONFIG["output_dir"] / "01_papers_extracted.csv", index=False)
```

For `build.py` and `visualize.py`, update any references to output or plot directories to use the new helpers instead of hardcoded `dist/` paths.

- [ ] **Step 3: Run the pipeline targets**

Run:
```bash
pnpm nx run bibliometric-pipeline:extract
pnpm nx run bibliometric-pipeline:build
pnpm nx run bibliometric-pipeline:visualize
```
Expected: each target resolves the new `data/` layout and writes outputs to `data/intermediate` or `data/outputs`.

- [ ] **Step 4: Commit**

```bash
rtk git add apps/bibliometric-pipeline/src/bibliometric_pipeline/extract.py apps/bibliometric-pipeline/src/bibliometric_pipeline/build.py apps/bibliometric-pipeline/src/bibliometric_pipeline/visualize.py
rtk git commit -m "feat: update bibliometric pipeline to new data layout"
```

### Task 4: Update Horizonpulse Crawler Paths

**Files:**
- Modify: `apps/horizonpulse-crawler/src/horizonpulse_crawler/config.py`
- Modify: `apps/horizonpulse-crawler/src/horizonpulse_crawler/crawl.py`
- Test: `pnpm nx run horizonpulse-crawler:crawl`

- [ ] **Step 1: Update the config module**

Set paths to the new layout:

```python
from shared_python.paths import get_workspace_root

WORKSPACE_ROOT = get_workspace_root()

CONFIG = {
    "BASE_URL": "https://www.horizonpulse.ir",
    "MAX_DEPTH": 5,
    "MAX_PAGES": 200,
    "WAIT_FOR_MS": 2000,
    "HTML_DIR": WORKSPACE_ROOT / "data" / "raw" / "horizonpulse_crawler" / "html",
    "PAGES_DIR": WORKSPACE_ROOT / "data" / "intermediate" / "horizonpulse_crawler" / "pages",
    "SUMMARY_PATH": WORKSPACE_ROOT / "data" / "outputs" / "horizonpulse_crawler" / "crawl_summary.json",
}
```

- [ ] **Step 2: Update crawl.py to use the new config keys**

Change file saves to use `CONFIG["PAGES_DIR"]`, `CONFIG["HTML_DIR"]`, and `CONFIG["SUMMARY_PATH"]`.

- [ ] **Step 3: Run the crawler**

Run: `pnpm nx run horizonpulse-crawler:crawl`
Expected: crawl succeeds and writes outputs into the new `data/` hierarchy.

- [ ] **Step 4: Commit**

```bash
rtk git add apps/horizonpulse-crawler/src/horizonpulse_crawler/config.py apps/horizonpulse-crawler/src/horizonpulse_crawler/crawl.py
rtk git commit -m "feat: move crawler outputs into data hierarchy"
```

### Task 5: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update the data locality rules**

Replace the current `Data Locality` rule with the Bronze/Silver/Gold layout described in the spec.

- [ ] **Step 2: Update workflow guidance**

Replace the existing `shared_python.paths` guidance so it explicitly points to `get_raw_data_path()`, `get_intermediate_data_path()`, and `get_output_path()`.

- [ ] **Step 3: Commit**

```bash
rtk git add AGENTS.md
rtk git commit -m "docs: clarify unified data directory policy"
```

### Task 6: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the architecture section**

Replace the references to `data_source/` and `dist/apps/<app-name>/` with the new `data/raw`, `data/intermediate`, and `data/outputs` layout.

- [ ] **Step 2: Update dataset descriptions**

Replace the statement that all datasets reside in `data_source/` with a statement that they reside in `data/` following the Bronze/Silver/Gold structure.

- [ ] **Step 3: Commit**

```bash
rtk git add README.md
rtk git commit -m "docs: document unified data directory layout"
```

### Task 7: Verify the Refactor

**Files:**
- No new files

- [ ] **Step 1: Run targeted checks**

Run:
```bash
pnpm nx test shared-python
pnpm nx run bibliometric-pipeline:extract
pnpm nx run horizonpulse-crawler:crawl
```

Expected: the shared path helpers pass, bibliometric extraction resolves the new raw data location, and the crawler writes to the new directory structure.

- [ ] **Step 2: Review remaining gaps**

Confirm the only intentionally postponed item is Nx caching cleanup for heavy data targets.

- [ ] **Step 3: Final commit if needed**

If verification required any follow-up fixes, commit them separately.
