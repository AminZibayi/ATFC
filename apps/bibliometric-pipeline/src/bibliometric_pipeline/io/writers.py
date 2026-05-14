import networkx as nx
import pandas as pd
from pathlib import Path

def write_graphml(G: nx.Graph, out_path: Path):
    print(f"  Writing GraphML to {out_path.name}")
    # NetworkX automatically serializes node/edge attributes in graphml
    nx.write_graphml(G, out_path)

def write_csvs(G: nx.Graph, nodes_path: Path, edges_path: Path):
    print(f"  Writing CSVs to {nodes_path.name} and {edges_path.name}")
    
    # Write nodes
    nodes_data = []
    for n, attrs in G.nodes(data=True):
        row = {'id': n}
        row.update(attrs)
        nodes_data.append(row)
        
    df_nodes = pd.DataFrame(nodes_data)
    df_nodes.to_csv(nodes_path, index=False)
    
    # Write edges
    edges_data = []
    for u, v, attrs in G.edges(data=True):
        row = {'source': u, 'target': v}
        row.update(attrs)
        edges_data.append(row)
        
    df_edges = pd.DataFrame(edges_data)
    df_edges.to_csv(edges_path, index=False)
