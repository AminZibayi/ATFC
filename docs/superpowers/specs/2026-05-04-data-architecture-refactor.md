# Data Directory Architecture Refactoring Spec

## Overview
This specification defines the structural refactoring of the workspace's data directories to align with standard data lake architecture (Bronze/Silver/Gold) while adhering to Nx monorepo best practices. It explicitly separates immutable raw data from pipeline outputs and isolates data from application code and build artifacts.

## Motivation
Currently, the workspace suffers from a scattered data architecture:
- Raw inputs live in `data_source/`
- Pipeline outputs are routed to `dist/apps/<app-name>/data` or `dist/apps/<app-name>/plots` via `paths.py`
- Crawler outputs currently write directly to `data/horizonpulse/`

This mix of paradigms causes several issues:
1. Writing data to `dist/` is an anti-pattern as `dist/` is meant for ephemeral build artifacts (compilation outputs) that can be safely deleted via standard cleanup scripts (`rm -rf dist`). Deleting `dist/` should never destroy hours of NLP processing or scraping data.
2. Lack of a unified top-level data directory makes data lifecycle management and data locality difficult.

## Target Architecture

All data MUST live strictly inside the top-level `data/` directory. The `data/` directory will be structured by processing stages:

```text
data/
├── raw/            (Bronze)  Immutable inputs. (e.g., WoS Excel files, raw web scraping outputs like HTML)
├── intermediate/   (Silver)  Cleaned, parsed, or tokenized data (e.g., extracted WoS entities, parsed Markdown)
└── outputs/        (Gold)    Final aggregations, LDA topic models, plots, and JSONs ready for frontend
```

### Specific Migrations
1. **Raw Data Migration**: Move `data_source/wos_filtered_bibliography.xlsx` to `data/raw/wos_filtered_bibliography.xlsx`. Delete the `data_source/` directory if empty.
2. **Library Update**: Refactor `libs/shared-python/src/shared_python/paths.py` to route paths to the new architecture.

## Implementation Details

### Refactoring `paths.py`

The `shared_python/paths.py` utility must be updated to export the following functions/constants:

- `WORKSPACE_ROOT`: Points to the repository root.
- `DATA_DIR`: `WORKSPACE_ROOT / "data"`
- `get_raw_data_path(filename: str) -> Path`: Routes to `data/raw/{filename}`
- `get_intermediate_data_path(app_name: str, filename: str) -> Path`: Routes to `data/intermediate/{app_name}/{filename}`
- `get_output_path(app_name: str, filename: str) -> Path`: Routes to `data/outputs/{app_name}/{filename}`
- `get_plot_path(app_name: str, filename: str) -> Path`: Routes to `data/outputs/{app_name}/plots/{filename}`

*Note: The old `get_data_path()` should be deprecated or aliased to `get_raw_data_path()` with a warning, but for the immediate refactor, we will update the existing codebase to use the new explicit functions.*

### Updating Existing Apps

1. **`bibliometric-pipeline`**:
   - Update `apps/bibliometric-pipeline/src/bibliometric_pipeline/extract.py` (and any other scripts) to use `get_raw_data_path` for the Excel file.
   - Update intermediate CSV saving to use `get_intermediate_data_path`.
   - Update final outputs to use `get_output_path`.

2. **`horizonpulse-crawler`**:
   - Update `apps/horizonpulse-crawler/src/horizonpulse_crawler/config.py` to map its directories appropriately:
     - HTML files -> `data/raw/horizonpulse_crawler/html/`
     - Markdown files -> `data/intermediate/horizonpulse_crawler/pages/`
     - Summary JSON -> `data/outputs/horizonpulse_crawler/crawl_summary.json`

## Future Considerations (Out of Scope for this Spec)
- **Nx Caching Rules**: Heavy data pipelines (`extract`, `crawl`) should have `"cache": false` in their respective `project.json` files to prevent Nx from caching gigabytes of data into `.nx/cache/`. *This is explicitly postponed and will be addressed in a separate effort.*

---

## AGENTS.md Update

Update the **Data Locality** tenet and related sections:

```diff
- 2. **Data Locality**: Code does not live near data. Code lives in `apps/` and `libs/`. Data lives in `data/`.
+ 2. **Data Locality**: Code does not live near data. Code lives in `apps/` and `libs/`. Data lives in the top-level `data/` directory, structured as a data lake:
+    - `data/raw/` — Immutable raw inputs (Bronze)
+    - `data/intermediate/` — Cleaned/parsed intermediate outputs (Silver)
+    - `data/outputs/` — Final aggregations ready for visualization (Gold)
```

Update the **Workflow Guidance** section:

```diff
- Import `shared_python.paths` (from `libs/shared-python`) to fetch the path to `data/raw` or `data/outputs`.
+ Import `shared_python.paths` (from `libs/shared-python`) to fetch paths using `get_raw_data_path()`, `get_intermediate_data_path()`, or `get_output_path()`.
```

## README.md Update

Update the **Monorepo Architecture** section:

```diff
- **Data Locality:** Code and data are strictly separated. Raw data lives in `data_source/`, while all generated artifacts are cached and output to `dist/apps/<app-name>/`.
+ **Data Locality:** Code and data are strictly separated. All data lives in the top-level `data/` directory, structured by processing stage:
+   - `data/raw/` — Immutable raw inputs (e.g., WoS Excel files, raw HTML scraping)
+   - `data/intermediate/` — Cleaned, parsed, or tokenized data
+   - `data/outputs/` — Final aggregations (plots, LDA JSONs, network JSONs)

- `data_source/`: Raw and derived input datasets (not committed by default)
- `dist/`: Generated artifacts and build outputs (gitignored)
- `dist/apps/<app-name>/data/` (OLD — will be deprecated)
+ `data/outputs/<app-name>/` (NEW — unified outputs)
```

Update the **Datasets** section introduction:

```diff
- All datasets reside in `data_source/`.
+ All datasets reside in the `data/` directory following the Bronze/Silver/Gold structure.
```