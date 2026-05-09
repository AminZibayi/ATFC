"""
=============================================================================
Phase 3: Network Visualization
=============================================================================
Loads the graphml files and node/edge XLSX files from Phase 2 and generates
all visualizations:

  For each network:
    - Static network graph (dark-themed matplotlib)
    - Interactive Plotly HTML
    - Bar chart of top hubs / funders / journals

  Additional for institutional & funding:
    - Bar chart of top betweenness brokers

  Additional for journal:
    - Bar chart colored by research area

Plots -> plots/bibliometric_networks/*.png, *.html
=============================================================================
"""

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.graph_objects as go
from matplotlib.collections import LineCollection

from shared_python.paths import get_output_path, get_plot_path

# ---------------------------------------------------------------------------
# CONFIGURABLE PARAMETERS -- edit these to adjust the visualizations
# ---------------------------------------------------------------------------
CONFIG = {
    "input_dir": get_output_path("bibliometric-pipeline", "temp").parent,
    "plot_dir": get_plot_path("bibliometric-pipeline", "temp").parent,

    "institutional": {
        "top_n_labels": 30,
        "top_n_bar": 20,
        "layout_seed": 42,
        "layout_iterations": 20,
        "figure_dpi": 100,
        "figure_size": (16, 12),
        "node_size_scale": 80,
        "edge_width_scale": 0.6,
        "max_edge_width": 6,
    },
    "funding": {
        "top_n_labels": 30,
        "top_n_bar": 20,
        "layout_seed": 42,
        "layout_iterations": 20,
        "figure_dpi": 100,
        "figure_size": (16, 12),
        "node_size_scale": 60,
        "edge_width_scale": 0.6,
        "max_edge_width": 6,
    },
    "journal": {
        "top_n_labels": 30,
        "top_n_bar": 30,
        "layout_seed": 42,
        "layout_iterations": 20,
        "figure_dpi": 100,
        "figure_size": (16, 12),
        "node_size_scale": 15,
        "edge_width_scale": 0.3,
        "max_edge_width": 5,
    },
}



print("=" * 70)
print(" PHASE 3: NETWORK VISUALIZATION")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------
print("\n[1/3] Loading graph data ...")

inst_G = nx.read_graphml(CONFIG["output_dir"] / "02_institutional_graph.graphml")
fund_G = nx.read_graphml(CONFIG["output_dir"] / "02_funding_graph.graphml")
journal_G = nx.read_graphml(CONFIG["output_dir"] / "02_journal_graph.graphml")

inst_nodes_df = pd.read_excel(CONFIG["output_dir"] / "institutional_nodes.xlsx")
inst_edges_df = pd.read_excel(CONFIG["output_dir"] / "institutional_edges.xlsx")
fund_nodes_df = pd.read_excel(CONFIG["output_dir"] / "funding_nodes.xlsx")
fund_edges_df = pd.read_excel(CONFIG["output_dir"] / "funding_edges.xlsx")
journal_nodes_df = pd.read_excel(CONFIG["output_dir"] / "journal_nodes.xlsx")
journal_edges_df = pd.read_excel(CONFIG["output_dir"] / "journal_edges.xlsx")

print(f"  Institutional: {inst_G.number_of_nodes()} nodes, {inst_G.number_of_edges()} edges")
print(f"  Funding:       {fund_G.number_of_nodes()} nodes, {fund_G.number_of_edges()} edges")
print(f"  Journal:       {journal_G.number_of_nodes()} nodes, {journal_G.number_of_edges()} edges")


# ---------------------------------------------------------------------------
# HELPER: extract node attributes into dicts
# ---------------------------------------------------------------------------
def node_attr_dict(G, attr: str) -> dict:
    return {n: G.nodes[n].get(attr, 0) for n in G.nodes()}


# ---------------------------------------------------------------------------
# HELPER: static dark-themed network plot
# ---------------------------------------------------------------------------
def make_static_network(
    G,
    nodes_df,
    cfg: dict,
    edge_color: str,
    title: str,
    filename: str,
    node_col: str,
    color_by: str = "community",
    color_map_dict: dict | None = None,
):
    print(f"  Static network -> {filename} ...")
    pos = nx.spring_layout(
        G,
        seed=cfg["layout_seed"],
        iterations=cfg["layout_iterations"],
        k=1.5 / np.sqrt(G.number_of_nodes()) if G.number_of_nodes() > 0 else 1,
    )

    wd_dict = node_attr_dict(G, "weighted_degree")
    comm_dict = node_attr_dict(G, "community")

    node_sizes = [
        np.log1p(wd_dict.get(n, 1)) * cfg["node_size_scale"] for n in G.nodes()
    ]

    if color_by == "community":
        n_comm = max(int(max(comm_dict.values())) + 1, 1) if comm_dict else 1
        comm_colors = plt.cm.tab20(np.linspace(0, 1, max(n_comm, 1)))
        node_colors = [comm_colors[int(comm_dict.get(n, 0)) % 20] for n in G.nodes()]
    elif color_by == "research_area" and color_map_dict is not None:
        node_colors = [color_map_dict.get(n, (0.7, 0.7, 0.7, 1.0)) for n in G.nodes()]
    else:
        node_colors = [comm_colors[0]] * G.number_of_nodes()

    edge_list = list(G.edges())
    edge_weights = [G[u][v]["weight"] for u, v in edge_list]
    max_w = max(edge_weights) if edge_weights else 1
    edge_widths = [
        min(np.log1p(w) * cfg["edge_width_scale"], cfg["max_edge_width"])
        for w in edge_weights
    ]

    fig, ax = plt.subplots(figsize=cfg["figure_size"])
    ax.set_facecolor("#0e1117")
    fig.set_facecolor("#0e1117")

    lines = [[pos[u], pos[v]] for u, v in edge_list]
    lc = LineCollection(
        lines,
        linewidths=edge_widths,
        colors=edge_color,
        alpha=0.3,
        zorder=1
    )
    ax.add_collection(lc)

    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
        edgecolors="white", linewidths=0.3, alpha=0.9,
    )

    top_label_nodes = nodes_df.head(cfg["top_n_labels"])[node_col].tolist()
    label_map = {n: n for n in top_label_nodes if n in pos}
    nx.draw_networkx_labels(
        G, {k: pos[k] for k in label_map}, labels=label_map, ax=ax,
        font_size=7, font_color="white", font_weight="bold",
    )

    ax.set_title(title, color="white", fontsize=16, fontweight="bold", pad=20)
    ax.axis("off")

    # Research area legend (journal only)
    if color_by == "research_area" and color_map_dict is not None:
        all_areas = sorted(set(G.nodes[n].get("primary_research_area", "") for n in G.nodes()))
        area_cmap = plt.cm.Set3(np.linspace(0, 1, max(len(all_areas), 1)))
        area_color_map = {area: area_cmap[i % len(area_cmap)] for i, area in enumerate(all_areas)}
        legend_handles = []
        for area, color in list(area_color_map.items())[:15]:
            legend_handles.append(
                plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=area[:40])
            )
        ax.legend(
            handles=legend_handles, loc="lower left", fontsize=7,
            facecolor="#1a1a2e", edgecolor="#333", labelcolor="white",
            title="Research Area", title_fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(
        CONFIG["plot_dir"] / filename,
        dpi=cfg["figure_dpi"],
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    return pos, comm_dict, wd_dict, max_w, top_label_nodes


# ---------------------------------------------------------------------------
# HELPER: interactive Plotly HTML
# ---------------------------------------------------------------------------
def make_interactive_html(
    G,
    pos,
    top_label_nodes,
    node_col,
    edge_color,
    title,
    filename,
    size_attr="weighted_degree",
):
    print(f"  Interactive HTML -> {filename} ...")
    wd_dict = node_attr_dict(G, size_attr)
    comm_dict = node_attr_dict(G, "community")
    pub_count_dict = node_attr_dict(G, "pub_count")
    btwn_dict = node_attr_dict(G, "betweenness")

    edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w = max(edge_weights) if edge_weights else 1

    # Group edges by weight bins to reduce the number of traces (performance)
    n_bins = 5
    if max_w > 1:
        bins = np.linspace(min(edge_weights), max_w, n_bins + 1)
    else:
        bins = [0, 1]
    
    edge_traces = []
    for i in range(len(bins)-1):
        b_low = bins[i]
        b_high = bins[i+1]
        
        edge_x = []
        edge_y = []
        count = 0
        for u, v in G.edges():
            w = G[u][v]["weight"]
            if b_low <= w <= b_high:
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                count += 1
        
        if count > 0:
            avg_w = (b_low + b_high) / 2
            width = max(np.log1p(avg_w) * 0.5, 0.5)
            opacity = min(0.15 + 0.5 * avg_w / max_w, 0.7)
            
            edge_traces.append(go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=width, color=edge_color),
                hoverinfo="skip",
                mode="lines",
                opacity=opacity,
                showlegend=False
            ))

    x_nodes = [pos[n][0] for n in G.nodes()]
    y_nodes = [pos[n][1] for n in G.nodes()]

    area_info = ""
    if "primary_research_area" in list(G.nodes(data=True))[0][1]:
        area_dict = node_attr_dict(G, "primary_research_area")
        area_info = "<br>Area: {area}"

    hover_text = [
        f"<b>{n}</b><br>"
        f"Papers: {pub_count_dict.get(n, 0)}<br>"
        f"Weighted Degree: {wd_dict.get(n, 0)}<br>"
        f"Community: {comm_dict.get(n, 0)}"
        + (f"<br>Betweenness: {btwn_dict.get(n, 0):.4f}" if btwn_dict.get(n, 0) else "")
        + (f"<br>Area: {area_dict.get(n, '')}" if "primary_research_area" in list(G.nodes(data=True))[0][1] else "")
        for n in G.nodes()
    ]

    node_trace = go.Scatter(
        x=x_nodes, y=y_nodes, mode="markers+text",
        text=[n if n in top_label_nodes else "" for n in G.nodes()],
        textposition="top center", textfont=dict(size=9, color="white"),
        hoverinfo="text", hovertext=hover_text,
        marker=dict(
            size=[max(np.log1p(wd_dict.get(n, 1)) * 3, 4) for n in G.nodes()],
            color=[comm_dict.get(n, 0) for n in G.nodes()],
            colorscale="Turbo",
            line=dict(width=0.5, color="white"),
            opacity=0.9,
        ),
        showlegend=False,
    )

    layout = go.Layout(
        title=dict(text=title, font=dict(size=18)),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        hovermode="closest", margin=dict(b=20, l=5, r=5, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        dragmode="pan",
    )

    fig_p = go.Figure(data=edge_traces + [node_trace], layout=layout)
    fig_p.write_html(str(CONFIG["plot_dir"] / filename))


# ---------------------------------------------------------------------------
# HELPER: bar chart
# ---------------------------------------------------------------------------
def make_bar_chart(
    nodes_df,
    value_col: str,
    node_col: str,
    xlabel: str,
    title: str,
    filename: str,
    cfg: dict,
    color_attr: str = "community",
    G: nx.Graph | None = None,
    area_color_map: dict | None = None,
):
    print(f"  Bar chart -> {filename} ...")
    n = cfg.get("top_n_bar", 20)
    top = nodes_df.sort_values(value_col, ascending=False).head(n)

    if color_attr == "community" and G is not None:
        comm_dict = node_attr_dict(G, "community")
        n_comm = max(int(max(comm_dict.values())) + 1, 1) if comm_dict else 1
        comm_colors = plt.cm.tab20(np.linspace(0, 1, max(n_comm, 1)))
        c_colors = [
            mcolors.to_hex(comm_colors[int(comm_dict.get(n, 0)) % 20])
            for n in top[node_col]
        ]
    elif color_attr == "research_area" and area_color_map is not None:
        c_colors = [
            mcolors.to_hex(area_color_map.get(n, (0.7, 0.7, 0.7, 1.0)))
            for n in top[node_col]
        ]
    else:
        c_colors = ["#4cc9f0"] * len(top)

    figsize = (14, 12) if n > 20 else (12, 8)
    fig, ax = plt.subplots(figsize=figsize)
    fig.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    ax.barh(
        range(len(top)), top[value_col].values,
        color=c_colors[::-1], edgecolor="white", linewidth=0.3,
    )
    ax.set_yticks(range(len(top)))

    # For journal bar chart, append research area to label
    if "primary_research_area" in top.columns:
        labels = [
            f"{j} [{str(a)[:30]}]"
            for j, a in zip(top[node_col].values, top["primary_research_area"].values)
        ]
    else:
        labels = top[node_col].values

    ax.set_yticklabels(
        labels[::-1] if len(top) > 1 else labels,
        fontsize=9 if n <= 20 else 8,
        color="white",
    )
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, color="white", fontsize=11)
    ax.set_title(title, color="white", fontsize=14, fontweight="bold")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#333")
    plt.tight_layout()
    fig.savefig(
        CONFIG["plot_dir"] / filename,
        dpi=cfg["figure_dpi"],
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2a. INSTITUTIONAL COLLABORATION NETWORK VISUALIZATIONS
# ---------------------------------------------------------------------------
print("\n[2/3] Institutional collaboration network ...")

inst_cfg = CONFIG["institutional"]

inst_pos, inst_comm_dict, inst_wd_dict, inst_max_w, inst_top_labels = make_static_network(
    inst_G, inst_nodes_df, inst_cfg,
    edge_color="#4cc9f0",
    title="Institutional Collaboration Network\n(Additive Manufacturing -- WoS Publications)",
    filename="institutional_collaboration_network.png",
    node_col="institution",
)

make_interactive_html(
    inst_G, inst_pos, inst_top_labels, "institution",
    edge_color="#4cc9f0",
    title="Institutional Collaboration Network -- Interactive",
    filename="institutional_collaboration_network.html",
)

make_bar_chart(
    inst_nodes_df, "weighted_degree", "institution",
    xlabel="Weighted Degree (co-occurrence strength)",
    title="Top 20 Institutional Hubs by Collaborative Weight",
    filename="institutional_top20_hubs.png",
    cfg=inst_cfg, G=inst_G,
)

make_bar_chart(
    inst_nodes_df, "betweenness", "institution",
    xlabel="Betweenness Centrality",
    title="Top 20 Institutional Brokers by Betweenness Centrality",
    filename="institutional_top20_betweenness.png",
    cfg=inst_cfg, G=inst_G,
)

# ---------------------------------------------------------------------------
# 2b. FUNDING ORGANIZATION NETWORK VISUALIZATIONS
# ---------------------------------------------------------------------------
print("\n[2/3] Funding organization network ...")

fund_cfg = CONFIG["funding"]

fund_pos, fund_comm_dict, fund_wd_dict, fund_max_w, fund_top_labels = make_static_network(
    fund_G, fund_nodes_df, fund_cfg,
    edge_color="#f72585",
    title="Funding Organization Co-Funding Network\n(Additive Manufacturing -- WoS Publications)",
    filename="funding_co_funding_network.png",
    node_col="funding_org",
)

make_interactive_html(
    fund_G, fund_pos, fund_top_labels, "funding_org",
    edge_color="#f72585",
    title="Funding Organization Co-Funding Network -- Interactive",
    filename="funding_co_funding_network.html",
)

make_bar_chart(
    fund_nodes_df, "weighted_degree", "funding_org",
    xlabel="Weighted Degree (co-funding strength)",
    title="Top 20 Funding Organizations by Co-Funding Weight",
    filename="funding_top20_funders.png",
    cfg=fund_cfg, G=fund_G,
)

# ---------------------------------------------------------------------------
# 2c. JOURNAL RELATIONSHIP NETWORK VISUALIZATIONS
# ---------------------------------------------------------------------------
print("\n[3/3] Journal relationship network ...")

journal_cfg = CONFIG["journal"]

# Build research area colour map for journal nodes
all_areas = sorted(set(
    journal_G.nodes[n].get("primary_research_area", "Unclassified")
    for n in journal_G.nodes()
))
area_cmap = plt.cm.Set3(np.linspace(0, 1, max(len(all_areas), 1)))
area_color_map = {area: area_cmap[i % len(area_cmap)] for i, area in enumerate(all_areas)}

journal_pos, journal_comm_dict, journal_wd_dict, journal_max_w, journal_top_labels = make_static_network(
    journal_G, journal_nodes_df, journal_cfg,
    edge_color="#4361ee",
    title="Journal Relationship Network (Shared Institutional Affiliations)\n(Additive Manufacturing -- WoS Publications)",
    filename="journal_relationship_network.png",
    node_col="journal",
    color_by="research_area",
    color_map_dict=area_color_map,
)

make_interactive_html(
    journal_G, journal_pos, journal_top_labels, "journal",
    edge_color="#4361ee",
    title="Journal Relationship Network -- Interactive",
    filename="journal_relationship_network.html",
)

make_bar_chart(
    journal_nodes_df, "pub_count", "journal",
    xlabel="Number of Publications",
    title="Top 30 Journals by Publication Count (colored by Research Area)",
    filename="journal_top30_journals.png",
    cfg=journal_cfg,
    color_attr="research_area",
    area_color_map=area_color_map,
)

print("\n" + "=" * 70)
print(" PHASE 3 COMPLETE")
print("=" * 70)
