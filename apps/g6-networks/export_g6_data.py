"""
Phase 4a: Export G6 Data
Reads graphml and node metrics, applies layout, and exports to JSON for the G6 frontend.
Pre-filtering is supported via environment variables:
- G6_MAX_NODES (int): Limit to top N nodes by weighted degree.
- G6_MIN_EDGE_WEIGHT (float): Filter out edges below this weight.
"""
import os
import json
import colorsys
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx

from shared_python.paths import get_output_path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = get_output_path("bibliometric-pipeline", "graphs")
OUTPUT_DIR = get_output_path("g6-networks", "")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Environment variables for pre-filtering
MAX_NODES = int(os.environ.get("G6_MAX_NODES", 0)) or None
MIN_EDGE_WEIGHT = float(os.environ.get("G6_MIN_EDGE_WEIGHT", 0.0))

print("=" * 70)
print(" PHASE 4a: EXPORT G6 DATA")
if MAX_NODES: print(f"  Filtering: Max Nodes = {MAX_NODES}")
if MIN_EDGE_WEIGHT > 0: print(f"  Filtering: Min Edge Weight = {MIN_EDGE_WEIGHT}")
print("=" * 70)

def generate_community_colors(n: int) -> dict:
    """Generate n perceptually distinct colors using HSL golden ratio spacing."""
    colors = {}
    golden = 0.618033988749895
    h = 0.1
    for i in range(n):
        h = (h + golden) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, 0.55, 0.75)
        colors[i] = '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
    return colors

def process_network(name, color_by="community"):
    print(f"\nProcessing {name} network...")
    
    # 1. Load data
    graph_file = INPUT_DIR / f"{name}_layout.graphml"
    nodes_file = INPUT_DIR / f"{name}_nodes.parquet"
    
    if not graph_file.exists():
        print(f"  Skipping {name}, graphml not found at {graph_file}.")
        return
        
    G = nx.read_graphml(graph_file)
    
    if not nodes_file.exists():
        print(f"  Skipping {name}, nodes parquet not found at {nodes_file}.")
        return
        
    nodes_df = pd.read_parquet(nodes_file)
    
    print(f"  Original graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 2. Filter nodes and edges
    if MAX_NODES and G.number_of_nodes() > MAX_NODES:
        # Sort nodes by weighted_degree from the dataframe
        if 'weighted_degree' in nodes_df.columns:
            top_nodes = nodes_df.sort_values("weighted_degree", ascending=False).head(MAX_NODES)['id'].astype(str).tolist()
            G = G.subgraph(top_nodes).copy()
        
    if MIN_EDGE_WEIGHT > 0:
        edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if float(d.get("weight", 0)) < MIN_EDGE_WEIGHT]
        G.remove_edges_from(edges_to_remove)
        
    # Remove isolates created by edge filtering
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    
    print(f"  Filtered graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    if G.number_of_nodes() == 0:
        print(f"  Graph {name} is empty after filtering.")
        return

    # Update nodes_df to only include nodes present in the filtered graph
    nodes_df['id'] = nodes_df['id'].astype(str)
    nodes_df = nodes_df[nodes_df['id'].isin(set(G.nodes()))]
    
    # 3. Generate colors
    if color_by == "community":
        comm_values = nodes_df['community'].fillna(0).astype(float).astype(int).tolist()
        n_comm = max(max(comm_values) + 1, 1) if comm_values else 1
        color_map = generate_community_colors(n_comm)
    else:
        color_map = {}
        
    # 4. Build G6 JSON
    g6_data = {"nodes": [], "edges": []}
    
    # Base size scales
    size_scale, edge_scale, max_edge_w = 15, 0.8, 8
    
    community_map = dict(zip(nodes_df['id'].astype(str), nodes_df['community'].fillna(0).astype(int)))

    for _, row in nodes_df.iterrows():
        node_id = str(row['id'])
        # In case node isn't in graph due to filtering
        if not G.has_node(node_id): continue
            
        x = float(row.get('x', np.random.rand()))
        y = float(row.get('y', np.random.rand()))
        
        # We can use paper_count for size if available, otherwise weighted_degree
        if 'paper_count' in row and pd.notnull(row['paper_count']):
            wd = float(row['paper_count'])
        else:
            wd = float(row.get("weighted_degree", 1))
            
        # Size
        size = np.log1p(wd) * size_scale
        size = max(size, 8) # minimum size
        
        # Color
        if color_by == "community":
            c_val = int(float(row.get("community", 0))) if pd.notnull(row.get("community")) else 0
            color = color_map.get(c_val, "#cccccc")
            group_label = f"Community {c_val}"
        else:
            color = "#cccccc"
            group_label = "None"
            
        metrics = {}
        for k, v in row.items():
            if pd.notnull(v):
                if isinstance(v, (int, float, np.integer, np.floating)):
                    metrics[k] = float(v)
                else:
                    metrics[k] = str(v)
                    
        g6_data["nodes"].append({
            "id": node_id,
            "x": float(x * 1000), # Scale up coordinates for G6 canvas
            "y": float(y * 1000),
            "size": float(size),
            "color": color,
            "group_label": group_label,
            "metrics": metrics
        })
        
    for u, v, d in G.edges(data=True):
        weight = float(d.get("weight", 1))
        width = min(np.log1p(weight) * edge_scale, max_edge_w)
        width = max(width, 0.5)
        
        comm_u = community_map.get(str(u), -1)
        comm_v = community_map.get(str(v), -1)
        
        if comm_u == comm_v:
            # Intra-community: use muted version of community color
            base = color_map.get(comm_u, "#cccccc")
            edge_color = base + "99"   # 60% opacity hex
        else:
            # Inter-community: neutral grey
            edge_color = "#cccccc55"
        
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

# Process the new graphs
process_network("co_author", "community")
process_network("co_funding", "community")
process_network("co_affiliation", "community")
process_network("author_keywords", "community")
process_network("wos_categories", "community")

print("\n" + "=" * 70)
print(" PHASE 4a COMPLETE")
print("=" * 70)