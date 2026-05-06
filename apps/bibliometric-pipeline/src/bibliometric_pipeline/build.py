"""
=============================================================================
Phase 2: Network Construction & Metrics
=============================================================================
Loads the extracted CSV from Phase 1 and builds three co-occurrence
networks with full metrics:

  1. Institutional Collaboration Network (co-occurrence on same paper)
  2. Funding Organization Network (co-funding on same paper)
  3. Journal Relationship Network (shared institutional affiliations)

For each network, computes: degree, weighted degree, betweenness,
eigenvector centrality, clustering coefficient, community detection,
modularity, density, and graph-level summary statistics.

Outputs -> outputs/bibliometric_networks/{institutional,funding,journal}_*.xlsx
=============================================================================
"""

import itertools
import collections
import re
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx

from shared_python.paths import get_intermediate_data_path, get_output_path

# ---------------------------------------------------------------------------
# CONFIGURABLE PARAMETERS -- edit these to adjust the analysis
# ---------------------------------------------------------------------------
CONFIG = {
    "input_dir": get_intermediate_data_path("bibliometric-pipeline", "temp").parent,
    "output_dir": get_output_path("bibliometric-pipeline", "temp").parent,

    "institutional": {
        "min_publications": 5,
        "min_edge_weight": 3,
    },
    "funding": {
        "min_publications": 0,
        "min_edge_weight": 0,
    },
    "journal": {
        "min_publications": 50,
        "min_edge_weight": 20,
    },
}



print("=" * 70)
print(" PHASE 2: NETWORK CONSTRUCTION")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. LOAD EXTRACTED DATA
# ---------------------------------------------------------------------------
print("\n[1/4] Loading extracted data ...")
df = pd.read_csv(CONFIG["input_dir"] / "01_papers_extracted.csv")

# Deserialise list columns from semicolon-joined strings
df["inst_list"] = df["inst_list"].apply(
    lambda x: [] if pd.isna(x) or x == "" else sorted(set(str(x).split(";")))
)
df["funder_list"] = df["funder_list"].apply(
    lambda x: [] if pd.isna(x) or x == "" else sorted(set(str(x).split(";")))
)
df["journal"] = df["journal"].fillna("")

print(f"  Loaded {len(df):,} records")


# ---------------------------------------------------------------------------
# HELPER: build graph, compute metrics, return DataFrames
# ---------------------------------------------------------------------------
def build_network(
    entity_lists: pd.Series,
    pub_counter: collections.Counter,
    min_publications: int,
    min_edge_weight: int,
    node_col_name: str,
) -> tuple[nx.Graph, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Generic co-occurrence network builder.

    Parameters
    ----------
    entity_lists : pd.Series of list[str]
        Per-paper list of entities (institutions, funders, etc).
    pub_counter : Counter
        Entity -> total publication count.
    min_publications : int
        Minimum papers an entity must appear in to be a node.
    min_edge_weight : int
        Minimum co-occurrence weight to keep an edge.
    node_col_name : str
        Column name for the entity in output DataFrames.

    Returns
    -------
    G, nodes_df, edges_df, metrics_df, extras
    """
    eligible = {e for e, c in pub_counter.items() if c >= min_publications}
    print(f"  Eligible (>={min_publications} pubs): {len(eligible):,}")

    # Build edges
    edge_counter: collections.Counter = collections.Counter()
    for entities in entity_lists:
        filtered = [e for e in entities if e in eligible]
        if len(filtered) < 2:
            continue
        for a, b in itertools.combinations(sorted(filtered), 2):
            edge_counter[(a, b)] += 1

    edges = [
        (a, b, w) for (a, b), w in edge_counter.items() if w >= min_edge_weight
    ]
    print(f"  Raw edges: {len(edge_counter):,}")
    print(f"  Filtered edges (weight >={min_edge_weight}): {len(edges):,}")

    # Build graph
    G = nx.Graph()
    G.add_weighted_edges_from(edges)
    for node in G.nodes():
        G.nodes[node]["pub_count"] = pub_counter.get(node, 0)

    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    print(f"  Removed {len(isolates)} isolates")

    # Centrality metrics
    degree_dict = dict(G.degree())
    weighted_degree_dict = dict(G.degree(weight="weight"))
    betweenness_dict = nx.betweenness_centrality(
        G, weight="weight", k=min(500, len(G))
    )
    eigenvector_dict = {}
    try:
        eigenvector_dict = nx.eigenvector_centrality(
            G, weight="weight", max_iter=500
        )
    except nx.PowerIterationFailedConvergence:
        print("  Eigenvector centrality did not converge -- skipping")

    # Community detection
    communities = list(nx.community.greedy_modularity_communities(G))
    community_map = {}
    for i, comm in enumerate(communities):
        for node in comm:
            community_map[node] = i

    clustering_dict = nx.clustering(G)
    n_communities = len(communities)
    modularity = nx.community.modularity(G, communities)
    density = nx.density(G)
    avg_clustering = (
        np.mean(list(clustering_dict.values())) if clustering_dict else 0
    )

    # Build nodes DataFrame
    nodes_data = []
    for node in G.nodes():
        nodes_data.append({
            node_col_name: node,
            "degree": degree_dict.get(node, 0),
            "weighted_degree": weighted_degree_dict.get(node, 0),
            "betweenness": betweenness_dict.get(node, 0),
            "eigenvector": eigenvector_dict.get(node, 0),
            "clustering_coefficient": clustering_dict.get(node, 0),
            "community": community_map.get(node, -1),
            "pub_count": G.nodes[node].get("pub_count", 0),
        })

    nodes_df = pd.DataFrame(nodes_data).sort_values(
        "weighted_degree", ascending=False
    )

    edges_df = pd.DataFrame(
        edges, columns=["source", "target", "weight"]
    ).sort_values("weight", ascending=False)

    metrics_df = pd.DataFrame([{
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": density,
        "avg_clustering": avg_clustering,
        "num_communities": n_communities,
        "modularity": modularity,
        "max_degree": max(degree_dict.values()) if degree_dict else 0,
        "max_weighted_degree": max(weighted_degree_dict.values()) if weighted_degree_dict else 0,
        "top_hub": nodes_df.iloc[0][node_col_name] if len(nodes_df) > 0 else "",
        "top_betweenness": (
            nodes_df.sort_values("betweenness", ascending=False).iloc[0][node_col_name]
            if len(nodes_df) > 0 else ""
        ),
    }])

    extras = {
        "degree_dict": degree_dict,
        "weighted_degree_dict": weighted_degree_dict,
        "betweenness_dict": betweenness_dict,
        "eigenvector_dict": eigenvector_dict,
        "community_map": community_map,
        "n_communities": n_communities,
        "modularity": modularity,
        "density": density,
        "avg_clustering": avg_clustering,
        "clustering_dict": clustering_dict,
    }

    print(f"  Nodes: {G.number_of_nodes():,} | Edges: {G.number_of_edges():,}")
    print(f"  Communities: {n_communities} | Modularity: {modularity:.4f}")

    return G, nodes_df, edges_df, metrics_df, extras


# ---------------------------------------------------------------------------
# 2a. INSTITUTIONAL COLLABORATION NETWORK
# ---------------------------------------------------------------------------
print("\n[2/4] Building institutional collaboration network ...")

inst_pub_counter: collections.Counter = collections.Counter()
for insts in df["inst_list"]:
    for inst in insts:
        inst_pub_counter[inst] += 1
print(f"  Unique institutions (raw): {len(inst_pub_counter):,}")

(
    inst_G,
    inst_nodes_df,
    inst_edges_df,
    inst_metrics_df,
    inst_extras,
) = build_network(
    df["inst_list"],
    inst_pub_counter,
    CONFIG["institutional"]["min_publications"],
    CONFIG["institutional"]["min_edge_weight"],
    "institution",
)

# ---------------------------------------------------------------------------
# 2b. FUNDING ORGANIZATION NETWORK
# ---------------------------------------------------------------------------
print("\n[3/4] Building funding organization network ...")

fund_pub_counter: collections.Counter = collections.Counter()
for funders in df["funder_list"]:
    for f in funders:
        fund_pub_counter[f] += 1
print(f"  Unique funders (raw): {len(fund_pub_counter):,}")

(
    fund_G,
    fund_nodes_df,
    fund_edges_df,
    fund_metrics_df,
    fund_extras,
) = build_network(
    df["funder_list"],
    fund_pub_counter,
    CONFIG["funding"]["min_publications"],
    CONFIG["funding"]["min_edge_weight"],
    "funding_org",
)

# ---------------------------------------------------------------------------
# 2c. JOURNAL RELATIONSHIP NETWORK (shared institutional affiliations)
# ---------------------------------------------------------------------------
print("\n[4/4] Building journal relationship network ...")

journal_pub_counter: collections.Counter = collections.Counter()
for j in df["journal"]:
    if j:
        journal_pub_counter[j] += 1
print(f"  Unique journals (raw): {len(journal_pub_counter):,}")

# Build institution -> journals inverted index
inst_journals: collections.defaultdict = collections.defaultdict(set)
for _, row in df.iterrows():
    journal = row["journal"]
    if not journal:
        continue
    for inst in row["inst_list"]:
        inst_journals[inst].add(journal)

eligible_journals = {
    j for j, c in journal_pub_counter.items()
    if c >= CONFIG["journal"]["min_publications"]
}
print(f"  Eligible (>={CONFIG['journal']['min_publications']} pubs): {len(eligible_journals):,}")

# Build journal-journal edges from shared institutions
journal_edge_counter: collections.Counter = collections.Counter()
for inst, journals in inst_journals.items():
    filtered = [j for j in journals if j in eligible_journals]
    if len(filtered) < 2:
        continue
    for a, b in itertools.combinations(sorted(filtered), 2):
        journal_edge_counter[(a, b)] += 1

journal_edges = [
    (a, b, w)
    for (a, b), w in journal_edge_counter.items()
    if w >= CONFIG["journal"]["min_edge_weight"]
]
print(f"  Raw edges: {len(journal_edge_counter):,}")
print(f"  Filtered edges (weight >={CONFIG['journal']['min_edge_weight']}): {len(journal_edges):,}")

# Build journal graph
journal_G = nx.Graph()
journal_G.add_weighted_edges_from(journal_edges)
for node in journal_G.nodes():
    journal_G.nodes[node]["pub_count"] = journal_pub_counter.get(node, 0)

journal_isolates = list(nx.isolates(journal_G))
journal_G.remove_nodes_from(journal_isolates)
print(f"  Removed {len(journal_isolates)} isolates")

# Journal metrics
j_degree_dict = dict(journal_G.degree())
j_weighted_degree_dict = dict(journal_G.degree(weight="weight"))
j_betweenness_dict = nx.betweenness_centrality(
    journal_G, weight="weight", k=min(500, len(journal_G))
)
j_eigenvector_dict = {}
try:
    j_eigenvector_dict = nx.eigenvector_centrality(
        journal_G, weight="weight", max_iter=500
    )
except nx.PowerIterationFailedConvergence:
    print("  Eigenvector centrality did not converge -- skipping")

j_communities = list(nx.community.greedy_modularity_communities(journal_G))
j_community_map = {}
for i, comm in enumerate(j_communities):
    for node in comm:
        j_community_map[node] = i

j_clustering_dict = nx.clustering(journal_G)
j_n_communities = len(j_communities)
j_modularity = nx.community.modularity(journal_G, j_communities)
j_density = nx.density(journal_G)
j_avg_clustering = (
    np.mean(list(j_clustering_dict.values())) if j_clustering_dict else 0
)

# Assign primary research area per journal (most frequent WoS Category)
journal_area_counter: collections.defaultdict = collections.defaultdict(
    collections.Counter
)
for _, row in df.iterrows():
    j = row["journal"]
    if j not in journal_G.nodes():
        continue
    if pd.notna(row.get("WoS Categories")):
        cats = [
            c.strip()
            for c in str(row["WoS Categories"]).split(";")
            if c.strip()
        ]
        for cat in cats:
            journal_area_counter[j][cat] += 1

primary_area = {}
for j, area_counts in journal_area_counter.items():
    if area_counts:
        primary_area[j] = area_counts.most_common(1)[0][0]
    else:
        primary_area[j] = "Unclassified"

for node in journal_G.nodes():
    if node not in primary_area:
        primary_area[node] = "Unclassified"

# Build journal nodes DataFrame
journal_nodes_data = []
for node in journal_G.nodes():
    journal_nodes_data.append({
        "journal": node,
        "degree": j_degree_dict.get(node, 0),
        "weighted_degree": j_weighted_degree_dict.get(node, 0),
        "betweenness": j_betweenness_dict.get(node, 0),
        "eigenvector": j_eigenvector_dict.get(node, 0),
        "clustering_coefficient": j_clustering_dict.get(node, 0),
        "community": j_community_map.get(node, -1),
        "pub_count": journal_G.nodes[node].get("pub_count", 0),
        "primary_research_area": primary_area.get(node, "Unclassified"),
    })

journal_nodes_df = pd.DataFrame(journal_nodes_data).sort_values(
    "weighted_degree", ascending=False
)
journal_edges_df = pd.DataFrame(
    journal_edges, columns=["source", "target", "weight"]
).sort_values("weight", ascending=False)

journal_metrics_df = pd.DataFrame([{
    "nodes": journal_G.number_of_nodes(),
    "edges": journal_G.number_of_edges(),
    "density": j_density,
    "avg_clustering": j_avg_clustering,
    "num_communities": j_n_communities,
    "modularity": j_modularity,
    "max_degree": max(j_degree_dict.values()) if j_degree_dict else 0,
    "max_weighted_degree": max(j_weighted_degree_dict.values()) if j_weighted_degree_dict else 0,
    "top_hub": journal_nodes_df.iloc[0]["journal"] if len(journal_nodes_df) > 0 else "",
    "top_betweenness": (
        journal_nodes_df.sort_values("betweenness", ascending=False).iloc[0]["journal"]
        if len(journal_nodes_df) > 0 else ""
    ),
}])

journal_extras = {
    "degree_dict": j_degree_dict,
    "weighted_degree_dict": j_weighted_degree_dict,
    "betweenness_dict": j_betweenness_dict,
    "eigenvector_dict": j_eigenvector_dict,
    "community_map": j_community_map,
    "n_communities": j_n_communities,
    "modularity": j_modularity,
    "density": j_density,
    "avg_clustering": j_avg_clustering,
    "clustering_dict": j_clustering_dict,
    "primary_area": primary_area,
}

print(f"  Nodes: {journal_G.number_of_nodes():,} | Edges: {journal_G.number_of_edges():,}")
print(f"  Communities: {j_n_communities} | Modularity: {j_modularity:.4f}")

# ---------------------------------------------------------------------------
# SAVE ALL OUTPUTS
# ---------------------------------------------------------------------------
print("\nSaving outputs ...")

inst_nodes_df.to_excel(CONFIG["output_dir"] / "institutional_nodes.xlsx", index=False)
inst_edges_df.to_excel(CONFIG["output_dir"] / "institutional_edges.xlsx", index=False)
inst_metrics_df.to_excel(CONFIG["output_dir"] / "institutional_metrics.xlsx", index=False)

fund_nodes_df.to_excel(CONFIG["output_dir"] / "funding_nodes.xlsx", index=False)
fund_edges_df.to_excel(CONFIG["output_dir"] / "funding_edges.xlsx", index=False)
fund_metrics_df.to_excel(CONFIG["output_dir"] / "funding_metrics.xlsx", index=False)

journal_nodes_df.to_excel(CONFIG["output_dir"] / "journal_nodes.xlsx", index=False)
journal_edges_df.to_excel(CONFIG["output_dir"] / "journal_edges.xlsx", index=False)
journal_metrics_df.to_excel(CONFIG["output_dir"] / "journal_metrics.xlsx", index=False)

# Save canonicalisation map as XLSX (for audit)
canon_csv = CONFIG["output_dir"] / "01_funding_canonicalization_map.csv"
if canon_csv.exists():
    canon_df = pd.read_csv(canon_csv)
    canon_df.to_excel(CONFIG["output_dir"] / "funding_canonicalization_map.xlsx", index=False)

# Save graphml files for Phase 3 (so it doesn't need to recompute metrics)
inst_G_save = inst_G.copy()
fund_G_save = fund_G.copy()
journal_G_save = journal_G.copy()

# Add node attributes needed by Phase 3
for node in inst_G_save.nodes():
    inst_G_save.nodes[node].update({
        "degree": inst_extras["degree_dict"].get(node, 0),
        "weighted_degree": inst_extras["weighted_degree_dict"].get(node, 0),
        "betweenness": inst_extras["betweenness_dict"].get(node, 0),
        "eigenvector": inst_extras["eigenvector_dict"].get(node, 0),
        "clustering_coefficient": inst_extras["clustering_dict"].get(node, 0),
        "community": inst_extras["community_map"].get(node, -1),
    })

for node in fund_G_save.nodes():
    fund_G_save.nodes[node].update({
        "degree": fund_extras["degree_dict"].get(node, 0),
        "weighted_degree": fund_extras["weighted_degree_dict"].get(node, 0),
        "betweenness": fund_extras["betweenness_dict"].get(node, 0),
        "eigenvector": fund_extras["eigenvector_dict"].get(node, 0),
        "clustering_coefficient": fund_extras["clustering_dict"].get(node, 0),
        "community": fund_extras["community_map"].get(node, -1),
    })

for node in journal_G_save.nodes():
    journal_G_save.nodes[node].update({
        "degree": j_degree_dict.get(node, 0),
        "weighted_degree": j_weighted_degree_dict.get(node, 0),
        "betweenness": j_betweenness_dict.get(node, 0),
        "eigenvector": j_eigenvector_dict.get(node, 0),
        "clustering_coefficient": j_clustering_dict.get(node, 0),
        "community": j_community_map.get(node, -1),
        "primary_research_area": primary_area.get(node, "Unclassified"),
    })

nx.write_graphml(inst_G_save, CONFIG["output_dir"] / "02_institutional_graph.graphml")
nx.write_graphml(fund_G_save, CONFIG["output_dir"] / "02_funding_graph.graphml")
nx.write_graphml(journal_G_save, CONFIG["output_dir"] / "02_journal_graph.graphml")

print(f"  Saved nodes, edges, metrics XLSX files")
print(f"  Saved graphml files for Phase 3")
print(f"  Saved to {CONFIG['output_dir']}")

print("\n" + "=" * 70)
print(" PHASE 2 COMPLETE")
print("=" * 70)
