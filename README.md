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

Install all dependencies (Node and Python) from the workspace root:

```bash
pnpm install
```

### Full Pipeline Execution

Run the entire pipeline (Extract → Build Networks → Visualize → Export G6 Data → Build Vite App) in one command:

```bash
pnpm nx run-many -t extract build visualize export-data build
```

### Individual Targets

```bash
# 1. Extract raw WoS data into canonicalized CSVs
pnpm nx run bibliometric-pipeline:extract

# 2. Build institutional, funding, and journal graphs (GraphML, Excel metrics)
pnpm nx run bibliometric-pipeline:build

# 3. Generate static plots and interactive HTML networks
pnpm nx run bibliometric-pipeline:visualize

# 4. Export graph data to JSON for the G6 frontend
pnpm nx run g6-networks:export-data

# 5. Build the Vite frontend application
pnpm nx run g6-networks:build

# 6. Serve the interactive G6 visualization locally
pnpm nx serve g6-networks
```

## Datasets

All datasets reside in `data/` following the raw/intermediate/outputs layout. Due to their size, the raw datasets are hosted on GitHub Releases and are not tracked in the git repository. You must download the required dataset and place it in the `data/raw/` directory before running the pipeline.

| File                                                | Description                                               | Download Link |
| --------------------------------------------------- | --------------------------------------------------------- | ------------- |
| `wos_dataset_blockchain_AI.txt`                     | Raw WoS export of Blockchain and AI literature            | [Download](https://github.com/AminZibayi/ATFC/releases/download/v0.2.0/wos_dataset_blockchain_AI.txt) |

**Note:** The obsolete Additive Manufacturing dataset has been archived to a legacy release. The last commit hash utilizing this legacy dataset and the previous LDA topic modeling pipeline is `0f461ee` (Release `v0.1.0`). You can download it here: [additive_manufacturing_dataset-obsolete.rar](https://github.com/AminZibayi/ATFC/releases/download/v0.1.0/additive_manufacturing_dataset-obsolete.rar).

## Analysis Pipeline

```

WoS Search ──► Data Extraction ──► Network Graph Building ──► Visualization

```

1. **Data Collection** — WoS search for Blockchain and AI literature
2. **Data Extraction** — Cleaned entity lists extracted for institutions, funding organizations, and journals
3. **Graph Building** — Creation of institutional collaboration networks, funding co-occurrence networks, and journal relationship networks
4. **Visualization** — Generation of static plots and interactive G6-based HTML networks

## Available Analyses

With this pipeline, the following analyses are supported:

- **Institutional collaboration networks** — Maps academic relationships and central hubs
- **Funding landscape mapping** — Identifies major funding organizations and co-funding structures
- **Journal relationship networks** — Tracks where the research is primarily published
- **Citation analysis** — Using Times Cited, Cited References, and Cited Reference Count metrics
- **Co-authorship networks** — From Authors, Addresses, and Affiliations fields
- **Keyword co-occurrence networks** — Based on Author Keywords and Keywords Plus
- **Interdisciplinary analysis** — Cross-tabulate research with WoS categories
