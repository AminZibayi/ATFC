# Bibliometric Network Analysis Plan

## Overview

Build three co-occurrence networks from the WoS filtered bibliography (93,937 records):

1. **Institutional Collaboration Network** — institutions co-appearing on the same paper
2. **Funding Organization Network** — funding orgs co-funding the same paper
3. **Journal Relationship Network** — journals linked by shared institutional affiliations

## Data Source

`data_source/wos_filtered_bibliography.xlsx` — 93,937 records, 73 columns

Key columns:

| Column | Use | Quality |
|--------|-----|---------|
| `Affiliations` | Institution nodes | Good — clean names, `;`-separated, 91,708 non-NaN |
| `Funding Orgs` | Funder nodes | Poor — grant numbers embedded, abbreviations, fragments, 70,965 non-NaN |
| `Source Title` | Journal nodes | Good — all uppercase, 93,937 non-NaN, ~47 duplicate pairs |
| `Publication Year` | Temporal filtering | Clean |
| `WoS Categories` | Research area labeling | Clean |

## Configurable Parameters

All tunable variables are at the top of each script as a `CONFIG` dict for easy manipulation:

```python
CONFIG = {
    "min_publications": 5,       # min papers an entity must appear in to be a node
    "min_edge_weight": 3,        # min co-occurrences to keep an edge
    "top_n_labels": 30,          # how many nodes to label in static plots
    "top_n_bar": 20,             # how many nodes in bar charts
    "layout_seed": 42,           # spring layout reproducibility
    "layout_iterations": 100,    # spring layout quality
    "figure_dpi": 200,           # output resolution
    "figure_size": (20, 16),     # figure dimensions
}
```

## Script 1: Institutional Collaboration Network

**File:** `scripts/bibliometric_networks/01_institutional_collaboration.py`

### Processing

1. Load `Affiliations` + `Publication Year` + `UT (Unique WOS ID)`
2. Split each paper's affiliations on `;`, strip whitespace, remove trailing semicolons
3. Deduplicate within-paper (same institution listed twice → count once)
4. Filter: keep institutions with ≥ `CONFIG.min_publications` papers
5. Build edges: for each paper, all pairwise combinations of its institutions → increment edge weight
6. Filter edges: keep edges with weight ≥ `CONFIG.min_edge_weight`
7. Compute network metrics + community detection

### Outputs

| File | Contents |
|------|----------|
| `outputs/bibliometric_networks/institutional_nodes.xlsx` | institution, degree, weighted_degree, betweenness, eigenvector, community, pub_count |
| `outputs/bibliometric_networks/institutional_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/institutional_metrics.xlsx` | graph-level summary stats |

### Plots

| File | Type |
|------|------|
| `plots/bibliometric_networks/institutional_collaboration_network.png` | Static network graph |
| `plots/bibliometric_networks/institutional_collaboration_network.html` | Interactive Plotly |
| `plots/bibliometric_networks/institutional_top20_hubs.png` | Bar chart by weighted degree |
| `plots/bibliometric_networks/institutional_top20_betweenness.png` | Bar chart by betweenness |

---

## Script 2: Funding Organization Network

**File:** `scripts/bibliometric_networks/02_funding_network.py`

### Processing

1. Load `Funding Orgs` + `Publication Year` + `UT (Unique WOS ID)`
2. Split on `; `, strip whitespace
3. **Grant number stripping:** regex `\s*\[[^\]]*\]` → remove `[grant-number]` patterns
4. **Fragment filtering:** drop orgs ≤2 words that match blacklist (National, Natural Science, Fundamental, Key, China, Science, Research, Technology, Projekt DEAL, etc.)
5. **Canonicalization** (moderate — ~25 abbreviation groups):
   - NSF / National Science Foundation → `National Science Foundation`
   - NSFC / NNSFC → `National Natural Science Foundation of China`
   - DOE / Department of Energy / U.S. Department of Energy → `U.S. Department of Energy`
   - NIH → `National Institutes of Health`
   - NASA → `National Aeronautics and Space Administration`
   - DFG / German Research Foundation → `German Research Foundation (DFG)`
   - EPSRC → `Engineering and Physical Sciences Research Council (EPSRC)`
   - NSERC → `Natural Sciences and Engineering Research Council of Canada (NSERC)`
   - NRF → `National Research Foundation of Korea`
   - CNPq → `National Council for Scientific and Technological Development (CNPq)`
   - CAPES → `Coordination for the Improvement of Higher Education Personnel (CAPES)`
   - etc.
6. Deduplicate within-paper
7. Filter: keep orgs with ≥ `CONFIG.min_publications` (default 10 for funding); edges ≥ `CONFIG.min_edge_weight`

### Outputs

| File | Contents |
|------|----------|
| `outputs/bibliometric_networks/funding_nodes.xlsx` | org, degree, weighted_degree, betweenness, eigenvector, community, pub_count |
| `outputs/bibliometric_networks/funding_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/funding_metrics.xlsx` | graph-level summary |
| `outputs/bibliometric_networks/funding_canonicalization_map.xlsx` | original → canonical mapping |

### Plots

| File | Type |
|------|------|
| `plots/bibliometric_networks/funding_co_funding_network.png` | Static network graph |
| `plots/bibliometric_networks/funding_co_funding_network.html` | Interactive Plotly |
| `plots/bibliometric_networks/funding_top20_funders.png` | Bar chart by weighted degree |

---

## Script 3: Journal Relationship Network

**File:** `scripts/bibliometric_networks/03_journal_network.py`

### Processing

1. Load `Source Title` + `Affiliations` + `Publication Year` + `WoS Categories` + `UT (Unique WOS ID)`
2. **Journal normalization:** uppercase, strip whitespace, replace `&` ↔ `AND`, collapse known duplicate pairs
3. Parse institutions per paper (from `Affiliations`, same as Script 1)
4. **Edge construction:** build institution→journals inverted index. For each institution, collect all journals it published in. For each pair of journals sharing ≥1 institution, edge weight = number of shared institutions.
5. Filter: journals with ≥ `CONFIG.min_publications` (default 50 for journals); edges ≥ `CONFIG.min_edge_weight` (default 5)
6. Assign primary research area per journal (most frequent WoS Category)
7. Compute metrics + community detection

### Outputs

| File | Contents |
|------|----------|
| `outputs/bibliometric_networks/journal_nodes.xlsx` | journal, degree, weighted_degree, betweenness, eigenvector, community, pub_count, primary_research_area |
| `outputs/bibliometric_networks/journal_edges.xlsx` | source, target, weight |
| `outputs/bibliometric_networks/journal_metrics.xlsx` | graph-level summary |

### Plots

| File | Type |
|------|------|
| `plots/bibliometric_networks/journal_relationship_network.png` | Static network, color = research area |
| `plots/bibliometric_networks/journal_relationship_network.html` | Interactive Plotly |
| `plots/bibliometric_networks/journal_top30_journals.png` | Bar chart by pub count, color = research area |

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

## Key Design Decisions

- **Affiliations over Addresses:** The `Affiliations` column has clean institution names only (no streets, ZIP codes, or author names mixed in). The `Addresses` column requires complex bracket parsing.
- **Moderate canonicalization for funding:** Strips grant numbers and maps ~25 common abbreviation groups. Does NOT attempt fuzzy matching or country-prefix normalization beyond the defined map — avoids false merges.
- **Shared affiliations for journal edges:** Per user choice. Captures institutional breadth across journals (which institutions bridge which journals).
- **No external community detection package:** Uses `networkx.community.greedy_modularity_communities()` which is built-in and works well.
