import networkx as nx
import pandas as pd
import community as community_louvain
from pathlib import Path

from shared_python.paths import get_intermediate_data_path, get_output_path
from bibliometric_pipeline.layout.forceatlas2 import compute_forceatlas2_layout
from bibliometric_pipeline.io.writers import write_graphml, write_csvs

def process_and_load_graph(name: str):
    in_dir = get_intermediate_data_path("bibliometric-pipeline", "")
    in_path = in_dir / f"edges_{name}.parquet"
    if not in_path.exists():
        print(f"Skipping {name}, edges file not found.")
        return
        
    print(f"\nProcessing {name} graph...")
    edges_df = pd.read_parquet(in_path)
    
    G = nx.Graph()
    # Add weighted edges
    for _, row in edges_df.iterrows():
        G.add_edge(row['source'], row['target'], weight=row['weight'])
        
    # Remove isolates
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    
    if len(G) == 0:
        print(f"  Graph {name} is empty after removing isolates.")
        return
        
    print(f"  Nodes: {G.number_of_nodes():,} | Edges: {G.number_of_edges():,}")
    
    # Metrics
    degrees = dict(G.degree())
    weighted_degrees = dict(G.degree(weight='weight'))
    
    print("  Computing betweenness centrality...")
    # Use k=min(500, len(G)) for faster approximation if graph is large
    k_val = min(500, len(G))
    betweenness = nx.betweenness_centrality(G, weight='weight', k=k_val)
    
    print("  Computing Louvain communities...")
    partition = community_louvain.best_partition(G, weight='weight')
    
    for n in G.nodes():
        G.nodes[n]['degree'] = degrees.get(n, 0)
        G.nodes[n]['weighted_degree'] = weighted_degrees.get(n, 0)
        G.nodes[n]['betweenness_centrality'] = betweenness.get(n, 0.0)
        G.nodes[n]['community'] = partition.get(n, 0)
        G.nodes[n]['label'] = str(n)
        
    # Layout
    compute_forceatlas2_layout(G, iterations=2000)
    
    # Export
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    write_graphml(G, out_dir / f"{name}.graphml")
    write_csvs(G, out_dir / f"{name}_nodes.csv", out_dir / f"{name}_edges.csv")

def run():
    print("=" * 70)
    print(" ETL STAGE 3: LOAD")
    print("=" * 70)
    
    graphs = [
        "co_author",
        "co_funding",
        "co_affiliation",
        "author_keywords",
        "wos_categories",
    ]
    
    for g in graphs:
        process_and_load_graph(g)
        
if __name__ == "__main__":
    run()