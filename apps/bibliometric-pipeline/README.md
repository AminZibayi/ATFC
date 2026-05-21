# Bibliometric Pipeline

This is the primary Python application in the monorepo responsible for data extraction, graph generation, enrichment, layout computation, and scientific metric calculation.

## Folder Structure

```text
apps/bibliometric-pipeline/
├── config.toml           # Core configuration for graph filtering and layout engines
├── config.schema.json    # JSON Schema definition for config.toml
├── project.json          # Nx targets definition (extract, build-graphs, apply-layout, diversity)
├── pyproject.toml        # uv package definitions
└── src/bibliometric_pipeline/
    ├── etl/              # Entry point scripts for Nx targets
    ├── graphs/           # Graph edge builders (co-occurrence algorithms)
    ├── layout/           # Layout engines (ForceAtlas2, SFDP)
    ├── metrics/          # Scientific indicator calculations (Diversity, etc.)
    └── io/               # Custom GraphML and Parquet parsers
```

## Configuration (`config.toml`)

The graph generation and layout stages are heavily customizable via `config.toml`. It allows setting global defaults and overriding them on a per-graph basis.

### Graph Filtering Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_weight` | `int` | `1` | The minimum weight (co-occurrence count) an edge must have to be kept. Useful for pruning noisy, weak connections. |
| `remove_isolates` | `bool` | `false` | If `true`, removes nodes that have no connecting edges after the pruning step. |

### Layout Engine Options

The pipeline supports multiple layout algorithms. The engine can be configured under the `[layout]` section.

| Engine | Description | Best For |
|--------|-------------|----------|
| `pyforceatlas2` | Cython-compiled ForceAtlas2 engine | Large graphs; extremely fast. |
| `fa2` | Pure Python fallback ForceAtlas2 | When C++ build tools are unavailable. |
| `sfdp` | Graphviz scalable force-directed placement | Aesthetic layouts; avoids node overlap well. Requires Graphviz installed on the OS. |
| `yifan_hu` | Graphviz Yifan Hu layout | Smaller graphs where strict clustering is desired. |

*Note: `iterations` can be set globally or per-graph. If omitted, the pipeline dynamically calculates the iterations based on the number of nodes in the graph to ensure convergence.*

Example `config.toml`:
```toml
[default]
min_weight = 1
remove_isolates = false
layout = { algorithm = "fa2" }

[co_author]
min_weight = 2  # Stricter pruning for noisy author networks
remove_isolates = true

[wos_categories]
# Use SFDP specifically for the categories graph
layout = { algorithm = "sfdp", iterations = 50 } 
```

## Nx Targets (Execution)

Run the following targets from the workspace root:

### `extract`
Parses the raw WOS plain-text export into structured Parquet records.
```bash
pnpm nx run bibliometric-pipeline:extract
```

### `build-graphs`
Extracts nodes and edge pairs for the five distinct graph types based on the `config.toml` filtering rules.
```bash
pnpm nx run bibliometric-pipeline:build-graphs
```

### `enrich-graphs`
Computes Louvain community partitions, betweenness centrality, and weighted degree. Performs in-place updates.
```bash
pnpm nx run bibliometric-pipeline:enrich-graphs
```

### `apply-layout`
Computes physical coordinates using the specified layout engine (ForceAtlas2 or SFDP). Performs in-place updates.
```bash
pnpm nx run bibliometric-pipeline:apply-layout
```

### `diversity`
Computes Interdisciplinarity & Diversity Metrics (Stirling Index) across a specific unit of analysis. 

**Arguments:**
The diversity script accepts additional arguments which can be passed via Nx by appending them to the command:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--group-col` | `string` | `PY` | The column to group the dataset by (the unit of analysis). Default is `PY` (Publication Year). |
| `--n-max` | `int` | `254` | The total theoretical maximum number of categories for normalization. 254 for modern WoS, 175 for the legacy 2006 SCI set. |

**Example usage:**
```bash
pnpm nx run bibliometric-pipeline:diversity -- --group-col=PY --n-max=254
```
*Output is saved to `data/outputs/bibliometric-pipeline/metrics/diversity_metrics.csv` and printed to the console.*