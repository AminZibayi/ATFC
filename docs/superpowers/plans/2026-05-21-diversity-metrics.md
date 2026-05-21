# Implementation Plan: Interdisciplinarity & Diversity Metrics (Stirling Index)

## Overview
This document outlines the plan to implement a reproducible Python pipeline in `apps/bibliometric-pipeline` that computes diversity metrics (Variety, Shannon, Simpson, and Stirling indices) using WoS Subject Categories (`WC`). This addresses the requirement to calculate interdisciplinarity as defined by Rafols & Meyer (2008). 

Since we currently only have Web of Science (WoS) data and no patent dataset, this implementation will focus on computing these metrics using WoS Subject Categories. The architecture will be designed to easily accommodate IPC codes once patent data becomes available.

## 1. Unit of Analysis
Because we do not have patent citation data (ref-of-refs) at this moment, our default units of analysis will be based on the metadata available in the WoS dataset.
- **Primary approach**: Compute diversity distributions across **publication years** (or year-windows) to show how interdisciplinarity evolves over time.
- **Alternative approach**: Compute distributions across thematic clusters if topic modeling or community detection is applied to the graph.

## 2. Processing Steps Implementation

### Step 1: Category Co-occurrence Graph
- **Existing Infrastructure**: We will leverage the `build_wos_categories_edges(df)` function already implemented in `src/bibliometric_pipeline/graphs/builders.py`. 
- **Action**: Extract nodes (category counts) and edges (co-occurrence weights) from the parsed records. 

### Step 2: Compute Category Distributions ($p_i$)
- Group the dataset by the chosen unit of analysis (e.g., `PY` - Publication Year).
- For each group, calculate the relative frequency ($p_i$) of each WoS Subject Category.
- Ensure $\sum_i p_i = 1$ for each unit.

### Step 3 & 4: Compute & Normalise Diversity Indices
Create a new module `src/bibliometric_pipeline/metrics/diversity.py`. 

Implementation will include parameters for $N_{max}$ (total theoretical categories). For WoS, the typical $N_{max}$ is roughly 254 (based on the modern WoS schema) or 175 (based on the 2006 SCI set used by Rafols & Meyer). We will make $N_{max}$ configurable.

The calculation module will implement:
- **Variety (N)**: Count of active categories in the unit / $N_{max}$ (Captures: Variety only)
- **Balance (H - Shannon)**: $(-\sum p_i \ln p_i) / \ln(N_{max})$ (Captures: Variety + Balance)
- **Balance (I - Simpson)**: $1 - \sum p_i^2$ (Captures: Variety + Balance)
- **Integration ($\Delta$ - Stirling)**: $1 - \sum_{i,j} s_{ij} \cdot p_i \cdot p_j$ (Captures: Variety + Balance + Disparity)

### Step 5: Handling the Global Similarity Matrix ($s_{ij}$) - The Tricky Point
To correctly calculate the Stirling index ($\Delta$) and not have it collapse into the Simpson index, we require a similarity matrix ($s_{ij}$) representing cognitive distance.

- **Option A (Preferred/Academic standard)**: Allow the pipeline to load a pre-existing, global WoS similarity matrix (e.g., Leydesdorff & Rafols 2009 Pajek file) if placed in `data/raw/` or `data/inputs/`.
  - **Handling Unknown Categories**: The Leydesdorff matrix covers 175 categories, but modern WoS has ~254. If a category exists in our data but not in the global matrix, we will assign a similarity of $s_{ij} = 0$ (maximum distance, $d_{ij} = 1$) for unknown category pairs, and explicitly log a warning listing the unmapped categories.
- **Option B (Proxy/Fallback)**: If the global matrix is not provided, dynamically compute a proxy similarity matrix from our own dataset using Salton's cosine.
  - Using the outputs from `build_wos_categories_edges(df)`, we have the co-occurrence weight $c_{ij}$. The denominator requires the self-similarity counts $c_{ii}$ and $c_{jj}$, which correspond to `nodes_df["paper_count"]` for each respective node.
  - Compute Salton's cosine: $s_{ij} = \frac{c_{ij}}{\sqrt{c_{ii} \cdot c_{jj}}}$.
  - The pipeline will default to Option B if a global matrix is missing, printing a documented warning that a proxy is being used.

*Note on Stirling Calculation*: The formula $\Delta = 1 - \sum_{i,j} s_{ij} \cdot p_i \cdot p_j$ relies on the diagonal having perfect self-similarity ($s_{ii} = 1$). To ensure floating-point imprecision doesn't corrupt $\Delta$, the implementation will explicitly enforce `np.fill_diagonal(s_matrix, 1.0)` before computing the vectorized formula.

### Step 6: Output Table Generation
- Construct a final Pandas DataFrame consolidating $N$, $H$, $I$, and $\Delta$ for each unit of analysis.
- Output this table to `data/outputs/diversity_metrics.csv`.
- Implement a script or Nx target to print the table in a pretty CLI format mapping exactly to the structure required.

## 3. Integration with Nx Monorepo
- **Code Location**: Logic will reside in `apps/bibliometric-pipeline/src/bibliometric_pipeline/metrics/diversity.py`.
- **Target**: We will create a new Nx target in `apps/bibliometric-pipeline/project.json` (e.g., `pnpm nx run bibliometric-pipeline:diversity`).
- This target will read from `data/intermediate/` (parsed WoS data) and write to `data/outputs/`.

## 4. Future Proofing for Patent Data
- When patent data (IPC codes) are introduced, the module will only need a new builder (e.g., `build_ipc_edges()`) and a corresponding $N_{max}$ for the IPC taxonomy. The mathematical formulations and metric standardisations will remain identical.
