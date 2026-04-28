# Technology Forecasting — Additive Manufacturing

Bibliometric analysis and technology forecasting of **Additive Manufacturing** using Web of Science publications and patent data. The pipeline covers data collection, NLP preprocessing, LDA topic modeling, trend analysis, and network visualization.

## Enterprise Nx Monorepo Architecture

This project is structured as a strict **Nx Monorepo**, seamlessly combining Python data pipelines and a TypeScript/Vite frontend visualization app.

- **Orchestrator:** Nx
- **Package Managers:** `pnpm` (Node/TypeScript) and `uv` (Python)
- **Data Locality:** Code and data are strictly separated. Raw data lives in `data_source/`, while all generated artifacts are cached and output to `dist/apps/<app-name>/`.

```text
Technology Forecasting/
├── apps/
│   ├── bibliometric-pipeline/    # Python pipeline (Data extraction, graph building, visualization)
│   └── g6-networks/              # TS/Vite frontend (Interactive G6 network visualizations)
├── libs/
│   └── shared-python/            # Shared Python utilities (e.g., dynamic workspace path resolution)
├── data_source/                  # Raw and derived input datasets (not committed by default)
├── dist/                         # Generated artifacts and build outputs (gitignored)
│   └── apps/
│       ├── bibliometric-pipeline/
│       │   ├── data/             # Generated CSV, JSON, GraphML, and Excel files
│       │   └── plots/            # Generated static plots and network HTML files
│       └── g6-networks/          # Compiled Vite frontend and exported G6 JSON data
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
.
├── data_source/                  # All source and derived datasets
│   ├── rename_mapping.yaml       # Original → renamed file mapping
├── scripts/                      # Analysis scripts (placeholder)
├── outputs/                      # Analysis outputs (placeholder)
└──  plots/                        # Generated visualizations
```

## Datasets

All datasets reside in `data_source/`. The project uses **two parallel corpora** — academic publications (Web of Science) and patents — processed through the same topic modeling pipeline.

| File                                                | Description                                               | Rows                    | Key Columns                                                                                                                             |
| --------------------------------------------------- | --------------------------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `wos_raw_bibliography.xlsx`                         | Raw WoS export                                            | 126,001                 | Authors, Article Title, Abstract, Cited References, Times Cited, Publication Year, Keywords, Affiliations, Funding Orgs, WoS Categories |
| `wos_filtered_bibliography.xlsx`                    | Filtered WoS subset (post-2000, with abstracts)           | 93,937                  | Same 73 columns as raw                                                                                                                  |
| `patents_with_dominant_topic.xlsx`                  | Patent abstracts with NLP columns + LDA topic assignments | 30,281                  | abstract_text, year, clean_text, tokens, bigrams, lemmatized, stemmed, Dominant_Topic, Contribution %                                   |
| `publication_stemmed_tokens_for_lda.json`           | Stemmed token lists (LDA input for publications)          | 68,867 docs             | List of token lists                                                                                                                     |
| `publication_lda_topic_keywords.xlsx`               | Top 25 keywords per publication topic (25 topics)         | 25 keywords × 25 topics | Topic 1…Topic 25                                                                                                                        |
| `patent_lda_topic_keywords.xlsx`                    | Top 25 keywords per patent topic (14 topics)              | 25 keywords × 14 topics | Topic 1…Topic 14                                                                                                                        |
| `publication_topic_document_distribution.xlsx`      | Document count & percentage per publication topic         | 25                      | Dominant Topic, Doc_Count, Total_Docs_Perc                                                                                              |
| `patent_topic_document_distribution.xlsx`           | Document count & percentage per patent topic              | 14                      | Dominant Topic, Doc_Count, Total_Docs_Perc                                                                                              |
| `publication_topic_proportions_by_year.xlsx`        | Publication topic proportions over time                   | 25 years                | Year, Topic 1…Topic 25                                                                                                                  |
| `patent_topic_proportions_by_year.xlsx`             | Patent topic proportions over time                        | 54 years                | Year, Topic 1…Topic 14                                                                                                                  |
| `patent_topic_proportions_by_year_no_year_col.xlsx` | Same as above, without Year column                        | 54 rows                 | Topic 1…Topic 14                                                                                                                        |
| `publication_topic_mann_kendall_results.xlsx`       | Mann-Kendall trend test on 25 publication topics          | 26                      | Variable, Trend, h, p-value, Z, Tau, S, Var(S), Sen's Slope, Intercept                                                                  |
| `patent_topic_mann_kendall_results.xlsx`            | Mann-Kendall trend test on 14 patent topics               | 15                      | Same columns as above                                                                                                                   |
| `cross_technology_mann_kendall_trends.xlsx`         | MK trend test across 30 technologies                      | 30                      | Technology, Trend, p-value, Slope                                                                                                       |
| `wos_category_counts.xlsx`                          | WoS category frequency distribution                       | 222                     | Category, Count                                                                                                                         |

## Analysis Pipeline

```
WoS Search (126K) ──► Filter (94K) ──► NLP Preprocessing ──► LDA (25 topics) ──► Trend Computation ──► Mann-Kendall Test
Patent Search (30K) ─────────────► NLP Preprocessing ──► LDA (14 topics) ──► Trend Computation ──► Mann-Kendall Test
                                                                                                    │
                                                                              Cross-technology MK test (30 technologies)
```

1. **Data Collection** — WoS search for Additive Manufacturing literature (126K records); patent database search (30K patents)
2. **Filtering** — Removed pre-2000 records, documents without abstracts, non-article types → 94K records
3. **NLP Preprocessing** — Text cleaning, tokenization, bigram extraction, lemmatization, stemming
4. **LDA Topic Modeling** — 25 publication topics, 14 patent topics (Gensim)
5. **Topic Assignment** — Each document assigned a dominant topic + contribution percentage
6. **Trend Computation** — Topic proportions calculated by year for both corpora
7. **Statistical Testing** — Mann-Kendall trend test with Sen's Slope on all topic time series

## Key Findings (from Mann-Kendall Tests)

| Dimension         | Publications (WoS)      | Patents |
| ----------------- | ----------------------- | ------- |
| Increasing topics | 9 of 25                 | 6 of 14 |
| Decreasing topics | 6 of 25                 | 1 of 14 |
| No trend          | 10 of 25                | 7 of 14 |
| Top WoS category  | Materials Science (29K) | N/A     |

All 30 cross-technology trends show "decreasing" patterns, consistent with post-peak Hype Cycle behavior.

## Topic Themes

### Publication Topics (25)

Medical/surgical AM, lattice/metamaterial design, microfluidics, bioprinting/hydrogel, WAAM/laser metal, directed energy deposition, FDM/PLA, powder bed fusion/ceramic, flexible electronics, tissue engineering scaffolds, and more.

### Patent Topics (14)

Metal powder/sintering, FDM nozzle/extruder, medical/bone fabrication, general layer deposition, SLM/SLS laser, structural/cavity/scaffold, microfluidics, and more.

## Available Analyses

With these datasets, the following analyses are supported:

- **Topic evolution visualization** — Stacked area charts / streamgraphs from topic proportion time series
- **Emerging vs. declining topic identification** — From Mann-Kendall results + Sen's Slope magnitude
- **Science-technology linkage** — Compare publication vs. patent topic landscapes
- **Technology life cycle modeling** — S-curve, logistic, or Bass diffusion fitting
- **Citation analysis** — Times Cited, Cited References, Cited Reference Count available
- **Co-authorship / collaboration networks** — From Authors, Addresses, Affiliations fields
- **Keyword co-occurrence networks** — Author Keywords + Keywords Plus for 108K/83K records
- **Interdisciplinary analysis** — Cross-tabulate topics with 222 WoS categories
- **Funding landscape mapping** — Funding Orgs available for ~71K records
- **Hype Cycle positioning** — Cross-technology MK results for 30 technologies
