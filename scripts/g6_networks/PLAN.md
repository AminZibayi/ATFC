# Implementation Plan: G6 Interactive Network Visualizations

## Goal
Add AntV G6 v5 interactive HTML network plots for the 3 bibliometric networks (institutional, funding, journal) alongside the existing Plotly and Matplotlib outputs. Use a pnpm-managed TypeScript build pipeline, employing a **Light Theme**, and support environment-variable-based pre-filtering in Python rather than client-side data reduction.

---

## Architecture

```
Phase 2 (existing)            New: Phase 4a                    New: Phase 4b
┌─────────────────┐           ┌─────────────────────┐          ┌──────────────────┐
│ 02_build_*.py   │──graphml─→│ export_g6_data.py   │──JSON──→│ vite build       │
│ *.xlsx outputs  │           │ (pre-compute layout)│          │ (TS + G6 render) │
└─────────────────┘           └─────────────────────┘          └──────────────────┘
                                                                         │
                                                                  plots/g6_networks/
                                                                  ├── institutional.html
                                                                  ├── funding.html
                                                                  └── journal.html
```

**Coexistence rule:** Existing `03_visualize_networks.py` and its `plots/bibliometric_networks/` directory remain untouched. All G6 artifacts live in `scripts/g6_networks/` and `plots/g6_networks/`.

---

## Directory Layout

```
scripts/g6_networks/
├── package.json              # pnpm project manifest
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts            # Multi-page build → ../../plots/g6_networks/
├── export_g6_data.py         # Python: graphml/xlsx → JSON
├── src/
│   ├── lib/
│   │   ├── types.ts          # NetworkData, NodeData, EdgeData
│   │   ├── renderer.ts       # createGraph(container, data, options)
│   │   └── ui.ts             # Search box, legend
│   ├── networks/
│   │   ├── institutional.ts  # Entry: import data, render with #4cc9f0 edges
│   │   ├── funding.ts        # Entry: import data, render with #f72585 edges
│   │   └── journal.ts        # Entry: import data, render with #4361ee edges
│   └── data/                 # Generated JSON (gitignored)
│       ├── institutional.json
│       ├── funding.json
│       └── journal.json
└── pages/
    ├── institutional.html    # Full-screen canvas + controls
    ├── funding.html
    └── journal.html
plots/g6_networks/            # Build output (gitignored)
```

---

## Tech Stack

| Layer | Tech | Purpose |
| --- | --- | --- |
| Package Manager | pnpm | Aligns with project convention |
| Bundler | Vite | Fast builds, multi-page, code-splitting |
| Renderer | @antv/g6 v5 | Canvas-based interactive graph |
| Language | TypeScript | Type safety |
| Data Prep | Python | Read graphml, compute spring layout, export JSON |

---

## Data Flow (`export_g6_data.py`)

For each of the 3 networks:
1. Load `02_*_graph.graphml` with NetworkX
2. Filter the graph based on environment variables (e.g., `G6_MIN_PUB_COUNT`, `G6_MIN_WEIGHTED_DEGREE`, `G6_MIN_EDGE_WEIGHT`) to customize data sizing before export.
3. Compute layout with `nx.spring_layout(seed=42, iterations=150)`.
4. Generate Light Theme node/edge styling. For the Journal network, keep the top 14 research areas and group the remainder into "Other".
5. Export `src/data/<network>.json` containing coordinates, colors, and sizes.

---

## G6 Rendering Spec

- **Preset Layout:** Use pre-computed `x`, `y` from Python.
- **Interactions:** Built-in `zoom-canvas`, `drag-canvas`, `drag-node`.
- **Node Size:** Proportional to `log1p(weighted_degree)`.
- **Node Color:** Pre-computed light theme friendly palettes.
- **Tooltip:** HTML tooltip showing rich metrics (Papers, Degree, Betweenness, etc.).
- **Search:** DOM search box mapping to `graph.focusItem()`.
- **Theme:** Clean Light Theme (white/light-grey background, `#333` labels, pastel-accented communities).

---

## Build Pipeline

The `vite.config.ts` handles the multi-page output to `plots/g6_networks/`.

```json
{
  "scripts": {
    "export-data": "python export_g6_data.py",
    "build": "vite build",
    "dev": "vite"
  }
}
```