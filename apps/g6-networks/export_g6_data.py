"""
Phase 4a: Export G6 Data
Reads graphml and node metrics, applies layout, and exports to JSON for the G6 frontend.
Pre-filtering is supported via environment variables:
- G6_MAX_NODES (int): Limit to top N nodes by weighted degree.
- G6_MIN_EDGE_WEIGHT (float): Filter out edges below this weight.
"""
import os
import json
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from shared_python.paths import get_output_path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = get_output_path("bibliometric_networks", "temp").parent
OUTPUT_DIR = (SCRIPT_DIR / "src/data").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Environment variables for pre-filtering
MAX_NODES = int(os.environ.get("G6_MAX_NODES", 0)) or None
MIN_EDGE_WEIGHT = float(os.environ.get("G6_MIN_EDGE_WEIGHT", 0.0))

print("=" * 70)
print(" PHASE 4a: EXPORT G6 DATA")
if MAX_NODES: print(f"  Filtering: Max Nodes = {MAX_NODES}")
if MIN_EDGE_WEIGHT > 0: print(f"  Filtering: Min Edge Weight = {MIN_EDGE_WEIGHT}")
print("=" * 70)

def hex_color(color_tuple, alpha=1.0):
    return mcolors.to_hex(color_tuple)

def process_network(name, node_col, color_by="community"):
    print(f"\nProcessing {name} network...")
    
    # 1. Load data
    graph_file = INPUT_DIR / f"02_{name}_graph.graphml"
    nodes_file = INPUT_DIR / f"{name}_nodes.xlsx"
    
    G = nx.read_graphml(graph_file)
    nodes_df = pd.read_excel(nodes_file)
    
    print(f"  Original graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 2. Filter nodes and edges
    if MAX_NODES and G.number_of_nodes() > MAX_NODES:
        # Sort nodes by weighted degree
        top_nodes = nodes_df.sort_values("weighted_degree", ascending=False).head(MAX_NODES)[node_col].tolist()
        G = G.subgraph(top_nodes).copy()
        
    if MIN_EDGE_WEIGHT > 0:
        edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d.get("weight", 0) < MIN_EDGE_WEIGHT]
        G.remove_edges_from(edges_to_remove)
        
    # Remove isolates created by edge filtering
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    
    print(f"  Filtered graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 3. Compute layout
    pos = nx.spring_layout(G, seed=42, iterations=150, k=1.5 / np.sqrt(max(G.number_of_nodes(), 1)))
    
    # 4. Generate colors
    if color_by == "community":
        comm_values = [int(float(G.nodes[n].get("community", 0))) for n in G.nodes()]
        n_comm = max(max(comm_values) + 1, 1) if comm_values else 1
        comm_colors = plt.cm.tab20(np.linspace(0, 1, max(n_comm, 1)))
        color_map = {c: hex_color(comm_colors[c % 20]) for c in set(comm_values)}
    elif color_by == "research_area":
        # Group top 14 areas, others to "Other"
        areas = [str(G.nodes[n].get("primary_research_area", "Unclassified")) for n in G.nodes()]
        area_counts = pd.Series(areas).value_counts()
        top_areas = area_counts.head(14).index.tolist()
        
        area_cmap = plt.cm.Set3(np.linspace(0, 1, 15))
        color_map = {area: hex_color(area_cmap[i]) for i, area in enumerate(top_areas)}
        color_map["Other"] = hex_color((0.8, 0.8, 0.8, 1.0)) # Gray for other
    else:
        color_map = {}
        
    # 5. Build G6 JSON
    g6_data = {"nodes": [], "edges": []}
    
    # Collect node degrees for scaling
    wd_values = [float(G.nodes[n].get("weighted_degree", 1)) for n in G.nodes()]
    max_wd = max(wd_values) if wd_values else 1
    
    # Base size scales (adjusted for light theme and better visibility)
    if name == "institutional": size_scale, edge_scale, max_edge_w = 40, 0.8, 8
    elif name == "funding": size_scale, edge_scale, max_edge_w = 30, 0.8, 8
    else: size_scale, edge_scale, max_edge_w = 10, 0.4, 6 # Journal
    
    for n in G.nodes():
        node_data = dict(G.nodes[n])
        x, y = pos[n]
        wd = float(node_data.get("weighted_degree", 1))
        
        # Size
        size = np.log1p(wd) * size_scale
        size = max(size, 8) # minimum size
        
        # Color
        if color_by == "community":
            c_val = int(float(node_data.get("community", 0)))
            color = color_map.get(c_val, "#cccccc")
            group_label = f"Community {c_val}"
        elif color_by == "research_area":
            area = str(node_data.get("primary_research_area", "Unclassified"))
            mapped_area = area if area in color_map else "Other"
            color = color_map.get(mapped_area, "#cccccc")
            group_label = mapped_area
            node_data["primary_research_area_mapped"] = mapped_area
        else:
            color = "#cccccc"
            group_label = "None"
            
        g6_data["nodes"].append({
            "id": str(n),
            "x": float(x * 1000), # Scale up coordinates for G6 canvas
            "y": float(y * 1000),
            "size": float(size),
            "color": color,
            "group_label": group_label,
            "metrics": {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else str(v)) for k, v in node_data.items()}
        })
        
    for u, v, d in G.edges(data=True):
        weight = float(d.get("weight", 1))
        width = min(np.log1p(weight) * edge_scale, max_edge_w)
        width = max(width, 0.5)
        
        if name == "institutional": edge_color = "#4cc9f0"
        elif name == "funding": edge_color = "#f72585"
        else: edge_color = "#4361ee"
        
        g6_data["edges"].append({
            "source": str(u),
            "target": str(v),
            "width": float(width),
            "color": edge_color,
            "weight": weight
        })
        
    out_file = OUTPUT_DIR / f"{name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(g6_data, f, indent=2)
        
    print(f"  Exported to {out_file}")

process_network("institutional", "institution", "community")
process_network("funding", "funding_org", "community")
process_network("journal", "journal", "research_area")

print("\n" + "=" * 70)
print(" PHASE 4a COMPLETE")
print("=" * 70)
