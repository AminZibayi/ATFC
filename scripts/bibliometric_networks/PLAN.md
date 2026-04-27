# Bibliometric Network Analysis Plan

## Overview

Build three co-occurrence networks from the WoS filtered bibliography (93,937 records):

1. **Institutional Collaboration Network** — institutions co-appearing on the same paper
2. **Funding Organization Network** — funding orgs co-funding the same paper
3. **Journal Relationship Network** — journals linked by shared institutional affiliations

## Architecture: 3-Phase Pipeline

The analysis is split into three phases so that the expensive raw data parsing
(Phase 1) and metric computation (Phase 2) are cached as intermediate files.
Phase 3 (visualization) can be re-run with different plot parameters without
re-extracting or re-computing anything.

```
Phase 1: Extract          Phase 2: Build             Phase 3: Visualize
(Load WoS, clean, save)   (Graphs + metrics, save)   (Plots from cached data)
    01_extract_data.py  -->  02_build_networks.py  -->  03_visualize_networks.py
         |                        |                         |
    01_papers_extracted.csv   *.xlsx + *.graphml         *.png + *.html
    01_*_summary.json
```

**Benefits:**
- Phase 1 loads the ~94K-row Excel file only once (slow) and caches cleaned data as CSV.
- Phase 2 does all heavy graph computation (centrality, community detection) once and saves graphml + XLSX.
- Phase 3 can be re-run with different visual parameters (colors, layouts, label counts) instantly.
- Any single phase can be re-run independently if only that step needs changes.

## Data Source

`data_source/wos_filtered_bibliography.xlsx` — 93,937 records, 73 columns

Key columns:

| Column | Use | Quality |
|--------|-----|---------|
| `Affiliations` | Institution nodes | Truncated at 72 chars — supplemented, not primary (see ISSUES_LOG.md Issue 1) |
| `Addresses` | Institution nodes (primary) | NOT truncated — WoS-abbreviated names, complete |
| `Funding Orgs` | Funder nodes | Poor — grant numbers embedded, abbreviations, fragments, 70,965 non-NaN |
| `Source Title` | Journal nodes | Good — all uppercase, 93,937 non-NaN, ~47 duplicate pairs |
| `Publication Year` | Temporal filtering | Clean |
| `WoS Categories` | Research area labeling | Clean |

## Phase 1: Data Extraction

**File:** `scripts/bibliometric_networks/01_extract_data.py`

Loads the raw WoS Excel once, extracts and cleans all three entity types, and
saves a lightweight CSV of per-paper entity lists (no re-loading of the heavy
Excel file in later phases).

### Processing

1. Load all needed columns at once from `wos_filtered_bibliography.xlsx`
2. **Institutions:** Extract from `Addresses` column (primary, not truncated) using regex `[Authors]` bracket parsing. Supplement with non-truncated entries from `Affiliations`. Apply canonicalisation map (~100 entries). Detect and discard truncated fragments (suffix heuristic) and generic names (blacklist).
3. **Funding Orgs:** Strip grant numbers with regex `\s*\[[^\]]*\]`. Apply canonicalisation map (~100 entries). Filter fragments (blacklist + single-word check + truncation suffix heuristic).
4. **Journals:** Normalise to uppercase, replace `&` with `AND`, collapse known duplicate pairs.
5. Serialise per-paper entity lists as semicolon-joined strings for CSV round-trip.

### Outputs

| File | Contents |
|------|----------|
| `outputs/bibliometric_networks/01_papers_extracted.csv` | UT (Unique WOS ID), Publication Year, inst_list, funder_list, journal, WoS Categories |
| `outputs/bibliometric_networks/01_funding_canonicalization_map.csv` | original -> canonical mapping (audit trail) |
| `outputs/bibliometric_networks/01_extraction_summary.json` | Counts and statistics |

---

## Phase 2: Network Construction & Metrics

**File:** `scripts/bibliometric_networks/02_build_networks.py`

Loads the extracted CSV, builds all three co-occurrence graphs, computes full
metrics, and saves XLSX tables + graphml files (with node attributes embedded)
for Phase 3.

### Configurable Parameters

```python
CONFIG = {
    "institutional": {
        "min_publications": 5,     # min papers an institution must appear in
        "min_edge_weight": 3,      # min co-occurrences to keep an edge
    },
    "funding": {
        "min_publications": 10,    # min papers a funder must appear in
        "min_edge_weight": 3,
    },
    "journal": {
        "min_publications": 50,    # min papers a journal must have
        "min_edge_weight": 20,     # min shared institutions for a journal pair
    },
}
```

### Processing

**Institutional & Funding networks** (generic co-occurrence builder):
1. Count publications per entity, filter by `min_publications`
2. Build edges: for each paper, all pairwise combinations of eligible entities -> increment edge weight
3. Filter edges by `min_edge_weight`, remove isolates
4. Compute: degree, weighted degree, betweenness centrality (approximated for large graphs), eigenvector centrality (with convergence fallback), clustering coefficient, greedy modularity communities, modularity, density

**Journal network** (shared institutional affiliations):
1. Count publications per journal, filter by `min_publications`
2. Build institution -> journals inverted index
3. For each institution, all pairwise journal combinations -> edge weight = number of shared institutions
4. Filter edges by `min_edge_weight`, remove isolates
5. Assign primary research area per journal (most frequent WoS Category)
6. Compute all metrics as above

### Outputs

| File | Contents |
|------|----------|
| `outputs/bibliometric_networks/institutional_nodes.xlsx` | institution, degree, weighted_degree, betweenness, eigenvector, clustering_coefficient, community, pub_count |
| `outputs/bibliometric_networks/institutional_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/institutional_metrics.xlsx` | graph-level summary stats |
| `outputs/bibliometric_networks/funding_nodes.xlsx` | funding_org, degree, weighted_degree, betweenness, eigenvector, clustering_coefficient, community, pub_count |
| `outputs/bibliometric_networks/funding_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/funding_metrics.xlsx` | graph-level summary |
| `outputs/bibliometric_networks/funding_canonicalization_map.xlsx` | original -> canonical mapping |
| `outputs/bibliometric_networks/journal_nodes.xlsx` | journal, degree, weighted_degree, betweenness, eigenvector, clustering_coefficient, community, pub_count, primary_research_area |
| `outputs/bibliometric_networks/journal_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/journal_metrics.xlsx` | graph-level summary |
| `outputs/bibliometric_networks/02_institutional_graph.graphml` | Full graph with all node attributes embedded |
| `outputs/bibliometric_networks/02_funding_graph.graphml` | Full graph with all node attributes embedded |
| `outputs/bibliometric_networks/02_journal_graph.graphml` | Full graph with all node attributes embedded |

---

## Phase 3: Visualization

**File:** `scripts/bibliometric_networks/03_visualize_networks.py`

Loads the graphml files and XLSX tables from Phase 2. Generates all
visualizations. Can be re-run independently with different plot parameters
without re-extracting data or re-computing metrics.

### Configurable Parameters

```python
CONFIG = {
    "institutional": {
        "top_n_labels": 30,       # nodes to label in static plots
        "top_n_bar": 20,          # nodes in bar charts
        "layout_seed": 42,        # spring layout reproducibility
        "layout_iterations": 150, # spring layout quality
        "figure_dpi": 200,        # output resolution
        "figure_size": (22, 18),  # figure dimensions
        "node_size_scale": 80,
        "edge_width_scale": 0.6,
        "max_edge_width": 6,
    },
    "funding": { ... },  # similar, node_size_scale=60
    "journal": { ... },  # similar, node_size_scale=15, top_n_bar=30
}
```

### Plots

| File | Type | Network |
|------|------|---------|
| `institutional_collaboration_network.png` | Static network (dark theme, community-colored) | Institutional |
| `institutional_collaboration_network.html` | Interactive Plotly | Institutional |
| `institutional_top20_hubs.png` | Bar chart by weighted degree | Institutional |
| `institutional_top20_betweenness.png` | Bar chart by betweenness | Institutional |
| `funding_co_funding_network.png` | Static network (dark theme, community-colored) | Funding |
| `funding_co_funding_network.html` | Interactive Plotly | Funding |
| `funding_top20_funders.png` | Bar chart by weighted degree | Funding |
| `journal_relationship_network.png` | Static network (dark theme, research-area-colored) | Journal |
| `journal_relationship_network.html` | Interactive Plotly | Journal |
| `journal_top30_journals.png` | Bar chart by pub count, color = research area | Journal |

---

## Visualization Design

| Element | Encoding |
|---------|----------|
| Node size | Weighted degree (log-scaled for readability) |
| Node color | Community (institutional/funding) or research area (journal) |
| Edge width | Weight, log-scaled |
| Labels | Top N nodes by centrality |
| Layout | Fruchterman-Reingold (spring) for static; Plotly force-directed for interactive |
| Palettes | tab20 for communities, Set3 for research areas |
| Theme | Dark (#0e1117 background) |

## Key Design Decisions

- **Addresses over Affiliations (primary):** The `Affiliations` column is truncated at 72 chars by the WoS Excel export. The `Addresses` column is NOT truncated and contains complete (but WoS-abbreviated) institution names. Affiliations is used as a supplement only — its non-truncated entries help recover full names.
- **Moderate canonicalization for funding:** Strips grant numbers and maps ~100 common abbreviation groups. Does NOT attempt fuzzy matching or country-prefix normalization beyond the defined map — avoids false merges.
- **Shared affiliations for journal edges:** Captures institutional breadth across journals (which institutions bridge which journals).
- **No external community detection package:** Uses `networkx.community.greedy_modularity_communities()` which is built-in and works well.
- **3-phase pipeline:** Separates extraction (slow I/O), computation (heavy graph algorithms), and visualization (fast, iteratable) into independent steps with cached intermediate files.
