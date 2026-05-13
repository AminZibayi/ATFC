import networkx as nx
import pandas as pd
import community as community_louvain  # pip: python-louvain
from pathlib import Path
from shared_python.paths import get_output_path

GRAPH_NAMES = ["co_author", "co_funding", "co_affiliation", "author_keywords", "wos_categories"]

def enrich(name: str):
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    graphml_path = out_dir / f"{name}.graphml"
    parquet_path = out_dir / f"{name}_nodes.parquet"

    if not graphml_path.exists() or not parquet_path.exists():
        print(f"  Skipping {name}, files not found.")
        return

    G = nx.read_graphml(graphml_path)
    nodes_df = pd.read_parquet(parquet_path)

    # Louvain community detection
    partition = community_louvain.best_partition(G, weight='weight', random_state=42)
    
    # Betweenness centrality (sampled for speed on large graphs)
    k = min(500, len(G))
    betweenness = nx.betweenness_centrality(G, k=k, weight='weight', normalized=True)
    
    # Weighted degree
    weighted_deg = dict(G.degree(weight='weight'))

    # Write back to parquet
    nodes_df['id'] = nodes_df['id'].astype(str)
    nodes_df['community'] = nodes_df['id'].map(partition).fillna(0).astype(int)
    nodes_df['betweenness'] = nodes_df['id'].map(betweenness).fillna(0)
    nodes_df['weighted_degree'] = nodes_df['id'].map(weighted_deg).fillna(0)
    nodes_df.to_parquet(parquet_path, index=False)
    
    n_communities = len(set(partition.values()))
    print(f"  {name}: {len(G)} nodes, {n_communities} communities detected")

def run():
    print("=" * 70)
    print(" ETL STAGE: ENRICH GRAPHS (Community + Centrality)")
    print("=" * 70)
    for name in GRAPH_NAMES:
        enrich(name)

if __name__ == "__main__":
    run()
