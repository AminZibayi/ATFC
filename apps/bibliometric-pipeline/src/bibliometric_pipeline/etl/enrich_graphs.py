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

    # Metrics are already computed during graph building and persisted to GraphML
    # and parquet. Reuse those values here instead of recomputing them.
    graph_attrs = {str(node_id): attrs for node_id, attrs in G.nodes(data=True)}

    # Write back to parquet
    nodes_df['id'] = nodes_df['id'].astype(str)

    community_map = {node_id: attrs.get('community') for node_id, attrs in graph_attrs.items()}
    weighted_degree_map = {node_id: attrs.get('weighted_degree') for node_id, attrs in graph_attrs.items()}
    betweenness_map = {
        node_id: attrs.get('betweenness_centrality', attrs.get('betweenness'))
        for node_id, attrs in graph_attrs.items()
    }

    if 'community' in nodes_df.columns:
        nodes_df['community'] = nodes_df['community'].fillna(nodes_df['id'].map(community_map)).fillna(0).astype(int)
    else:
        nodes_df['community'] = nodes_df['id'].map(community_map).fillna(0).astype(int)

    if 'weighted_degree' in nodes_df.columns:
        nodes_df['weighted_degree'] = nodes_df['weighted_degree'].fillna(nodes_df['id'].map(weighted_degree_map)).fillna(0)
    else:
        nodes_df['weighted_degree'] = nodes_df['id'].map(weighted_degree_map).fillna(0)

    # Keep the legacy parquet column name for compatibility, but source it from
    # the already-persisted canonical betweenness_centrality metric.
    if 'betweenness' in nodes_df.columns:
        nodes_df['betweenness'] = nodes_df['betweenness'].fillna(nodes_df['id'].map(betweenness_map)).fillna(0)
    elif 'betweenness_centrality' in nodes_df.columns:
        nodes_df['betweenness'] = nodes_df['betweenness_centrality'].fillna(nodes_df['id'].map(betweenness_map)).fillna(0)
    else:
        nodes_df['betweenness'] = nodes_df['id'].map(betweenness_map).fillna(0)

    nodes_df.to_parquet(parquet_path, index=False)

    n_communities = len({value for value in community_map.values() if value is not None})
    print(f"  {name}: {len(G)} nodes, {n_communities} communities detected")

def run():
    print("=" * 70)
    print(" ETL STAGE: ENRICH GRAPHS (Community + Centrality)")
    print("=" * 70)
    for name in GRAPH_NAMES:
        enrich(name)

if __name__ == "__main__":
    run()
