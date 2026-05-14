# Technology Forecasting — Blockchain and AI

Bibliometric analysis and technology forecasting of **Blockchain and AI** using Web of Science publications. The pipeline covers data collection, entity extraction, bibliometric network analysis, and interactive visualization.

## Monorepo Architecture

This project is structured as a strict **Monorepo**, seamlessly combining Python data pipelines and a TypeScript/Vite frontend visualization app.

- **Data Locality:** Code and data are strictly separated. Raw data lives in `data/raw`, intermediate artifacts live in `data/intermediate`, and final outputs live in `data/outputs`.

```text
Technology Forecasting/
├── apps/
│   ├── bibliometric-pipeline/    # Python pipeline (Data extraction, graph building, visualization)
│   └── g6-networks/              # TS/Vite frontend (Interactive G6 network visualizations)
├── libs/
│   └── shared-python/            # Shared Python utilities (e.g., dynamic workspace path resolution)
├── data/
│   ├── raw/                      # Immutable raw inputs and crawler HTML
│   ├── intermediate/             # Cleaned, parsed, or staged pipeline outputs
│   └── outputs/                  # Final aggregations, plots, and app exports
│       ├── bibliometric-pipeline/
│       └── g6-networks/
├── package.json                  # Root Node.js manifest and Nx plugins
├── pnpm-workspace.yaml           # pnpm workspace definition
└── nx.json                       # Nx configuration and caching rules
```

## Running the Pipeline

All tasks must be run through Nx to ensure proper caching and dependency resolution. Do not run `uv` or `pnpm` directly inside the app directories.

### Setup

1. **Install Base Dependencies:** Install all Node.js and Python packages via the workspace root:

   ```bash
   pnpm install
   ```

2. **System Requirements (Graphviz):** If you intend to use the Yifan Hu / SFDP layout algorithms (`algorithm = "sfdp"` or `"yifan_hu"`), you must install the Graphviz system binaries. Python's `pydot` cannot run these layouts without the underlying OS executables:

   - **Windows:** `winget install Graphviz.Graphviz`
   - **macOS:** `brew install graphviz`
   - **Linux:** `sudo apt-get install graphviz`

   *(Note: The pipeline automatically attempts to locate `C:\Program Files\Graphviz\bin` on Windows. Ensure it is added to your PATH if installed elsewhere).*

### Troubleshooting

- **`FileNotFoundError: [WinError 2] "sfdp" not found in path`**: Your system is missing Graphviz or it is not in your environment's PATH. See step 2 above.
- **`pyforceatlas2 not found. Falling back to fa2-modified`**: The fast Cython-compiled `pyforceatlas2` engine could not be installed/loaded (often due to missing C++ build tools on Windows). The pipeline will safely fall back to the slower pure-Python `fa2-modified` engine.
- **Pydot Encoding Errors**: Older Graphviz binaries sometimes crash with Unicode node names (like `charmap codec can't encode character`). The layout pipeline handles this automatically by isolating topological data with ASCII-safe node aliases before calling SFDP.

### Full Pipeline Execution

Run the entire ETL pipeline:

```bash
pnpm nx run bibliometric-pipeline:run
```

### Individual Targets

```bash
# 1. Extract raw WoS plain-text into Parquet format
pnpm nx run bibliometric-pipeline:extract

# 2. Build 5 graph types, compute metrics, and export GraphML/Parquet
# You can configure graph pruning via apps/bibliometric-pipeline/config.toml
# You can adjust min_weight and remove_isolates for each graph independently in that file.
pnpm nx run bibliometric-pipeline:build-graphs

# 3. Enrich graphs with additional metrics (in-place update, not cached)
pnpm nx run bibliometric-pipeline:enrich-graphs

# 4. Apply graph layout (ForceAtlas2 or Yifan Hu / SFDP)
# You can customize the engine (pyforceatlas2, sfdp, etc) and iterations
# via apps/bibliometric-pipeline/config.toml
# This stage performs in-place updates and is not cached to prevent Nx cache conflicts.
pnpm nx run bibliometric-pipeline:apply-layout
```

**Note on Nx Caching:** The `enrich-graphs` and `apply-layout` stages perform in-place updates on files created by `build-graphs`. To prevent Nx cache restoration from overwriting these updates, caching is disabled for these two stages.

## Datasets

All datasets reside in `data/` following the raw/intermediate/outputs layout. Due to their size, the raw datasets are hosted on GitHub Releases and are not tracked in the git repository. You must download the required dataset and place it in the `data/raw/` directory before running the pipeline.

| File                                                | Description                                               | Download Link |
| --------------------------------------------------- | --------------------------------------------------------- | ------------- |
| `wos_dataset_blockchain_AI.txt`                     | Raw WoS export of Blockchain and AI literature            | [Download](https://github.com/AminZibayi/ATFC/releases/download/v0.2.0/wos_dataset_blockchain_AI.txt) |

**Note:** The obsolete Additive Manufacturing dataset has been archived to a legacy release. The last commit hash utilizing this legacy dataset and the previous LDA topic modeling pipeline is `0f461ee` (Release `v0.1.0`). You can download it here: [additive_manufacturing_dataset-obsolete.rar](https://github.com/AminZibayi/ATFC/releases/download/v0.1.0/additive_manufacturing_dataset-obsolete.rar).

### Data Collection Methodology

The recent dataset on Blockchain and Artificial Intelligence was prepared following a structured approach:

1. **Emerging Technologies Analysis:** Based on recent research analyzing the "Emerging Technologies" page on Wikipedia, a crawl up to a specific depth yielded about 50,000 articles. After tagging, roughly 20,000 pages were identified as technologies, leading to the creation of the "momentum 100" list of top emerging technologies.
2. **Domain Selection:** Referencing this research, Machine Learning and Blockchain were identified as the hottest fields, with Reinforcement Learning (RL) and Blockchain ranking first and second, respectively.
3. **Query Formulation:** A highly optimized search string was formulated to maximize both accuracy and comprehensiveness. 
4. **Filtering & Extraction:** The query initially returned about 8,500 articles. After applying specific filters, the final dataset was narrowed down to approximately 6,500 records.

**Web of Science Search Query:**

```text
TS=(
  (
    (
      "blockchain" OR "distributed ledger*" OR "distributed ledger technolog*" OR DLT OR "smart contract*" OR Web3 OR "decentralized finance" OR DeFi OR "decentralized autonomous organization*" OR DAO* OR "decentralized identity" OR "self-sovereign identity" OR SSI OR "verifiable credential*" OR "soulbound token*"
    )
    AND
    (
      "artificial intelligence" OR "machine learning" OR "deep learning" OR "reinforcement learning" OR "federated learning" OR "large language model*" OR LLM* OR "AI agent*" OR "autonomous agent*" OR "agentic AI" OR "multi-agent system*" OR "neural network*" OR "knowledge graph*"
    )
  )
  OR
  (
    "blockchain-enabled federated learning" OR "blockchain federated learning" OR "decentralized federated learning" OR "decentralized AI" OR "verifiable AI" OR "on-chain AI" OR zkML OR opML OR "optimistic machine learning" OR "zero-knowledge machine learning" OR "Web3 AI agent*" OR "blockchain autonomous agent*" OR "smart contract agent*"
  )
)
```

**Applied Filters:**
- **Document Type:** Article or Early Access
- **Web of Science Index:** SCI-EXPANDED
- **Date:** 2017-2026
- **Language:** English

## Analysis Pipeline

```
WoS Plain-Text Export ──► EXTRACT ──► BUILD GRAPHS ──► ENRICH GRAPHS ──► APPLY LAYOUT ──► EXPORT G6 DATA
```

1. **Extract** — Parse raw WOS plain-text export into structured records (handling continuation lines and split fields).
2. **Build Graphs** — Fast, vectorized extraction of nodes (including `paper_count`) and edge pairs (filtered by minimum weight) for five distinct graph types.
3. **Enrich Graphs** — Perform deeper statistical analysis on the built networks. Computes Louvain community partitions, betweenness centrality (sampled for large graphs), and weighted degree.
4. **Apply Layout** — Isolate the heavy layout computation. Computes physical coordinates using either ForceAtlas2 (`pyforceatlas2` / `fa2`) or Graphviz's SFDP / Yifan Hu algorithm. Configurable via `config.toml`.
   - **Dynamic Iterations:** Automatically scales iteration count based on graph size if not explicitly set.
   - **Warm Starts:** Loads existing coordinates from previous runs as a starting position to accelerate convergence by up to 10x.
   - **Isolate Handling:** Strips disconnected nodes before layout to optimize performance and reattaches them at fixed positions afterward.
   - **Per-Graph Overrides:** Allows independent algorithm and iteration settings for each graph type.
5. **Export G6 Data** — Prepare optimized JSON files for the interactive frontend.
   - **Community Merging:** Merges micro-communities (size < 5) into an "Other Clusters" category to ensure a legible visualization and legend.
   - **Compact JSON:** Exports minified JSON artifacts to reduce bundle size by ~75% and improve browser parsing performance.

## Interactive Visualization (G6)

The project includes a high-performance interactive visualization dashboard powered by **AntV G6 v5** and **WebGL**.

- **WebGL Rendering:** Native WebGL support allows for fluid interaction with networks exceeding 4,000 nodes and 10,000 edges at 60fps.
- **Level-of-Detail (LOD):** Labels are automatically hidden when zoomed out and fade in as you zoom into specific clusters, preventing visual clutter.
- **Interactive Highlighting:** Click any node to instantly highlight its 1-hop neighborhood and filter out non-neighboring elements.
- **Community Hulls:** Automatically generates convex shapes around major communities to visualize cluster boundaries.
- **Search & Filter:** Find specific entities (authors, institutions, keywords) instantly and focus the camera on their position in the network.
- **Static Export:** Integrated high-resolution PNG export for generating figures for research publications.


## Available Analyses

With this pipeline, the following analyses are supported:

- **Co-authorship networks** (`co_author`)
- **Funding landscape mapping** (`co_funding`)
- **Institutional collaboration networks** (`co_affiliation`)
- **Keyword co-occurrence networks** (`author_keywords`)
- **Interdisciplinary analysis** (`wos_categories`)
