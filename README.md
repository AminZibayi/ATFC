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
