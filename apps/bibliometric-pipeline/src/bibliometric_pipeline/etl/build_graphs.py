import networkx as nx
import pandas as pd
import community as community_louvain
from pathlib import Path

from shared_python.paths import get_intermediate_data_path, get_output_path
from bibliometric_pipeline.graphs.builders import (
    build_co_author_edges,
    build_co_funding_edges,
    build_co_affiliation_edges,
    build_author_keywords_edges,
    build_wos_categories_edges,
)
from bibliometric_pipeline.io.writers import write_graphml

def process_and_build_graph(df: pd.DataFrame, builder_fn, name: str, min_weight: int = 2):
    print(f"\nBuilding {name} graph...")
    
    # 1. Call builder
    nodes_df, edges_df = builder_fn(df)
    
    if edges_df.empty:
        print(f"  Graph {name} has no edges.")
        return
        
    # 2. Filter edges strictly by min_edge_weight
    edges_df = edges_df[edges_df['weight'] >= min_weight]
    
    # 3. Initialize NetworkX Graph
    G = nx.Graph()
    
    # Add nodes and edges
    # Add paper_count as node attribute
    nodes_dict = nodes_df.set_index('id')[['paper_count']].to_dict('index')
    G.add_nodes_from((node_id, attrs) for node_id, attrs in nodes_dict.items())
    
    # Add edges
    G.add_edges_from((row.source, row.target, {'weight': row.weight}) for row in edges_df.itertuples(index=False))
    
    # 4. Remove isolates
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    
    if len(G) == 0:
        print(f"  Graph {name} is empty after removing isolates.")
        return
        
    print(f"  Generated Nodes: {G.number_of_nodes():,} | Edges: {G.number_of_edges():,} (min_weight={min_weight})")
    
    # Compute Metrics
    degrees = dict(G.degree())
    weighted_degrees = dict(G.degree(weight='weight'))
    
    print("  Computing betweenness centrality...")
    k_val = min(500, len(G))
    betweenness = nx.betweenness_centrality(G, weight='weight', k=k_val, seed=42)
    
    print("  Computing Louvain communities...")
    partition = community_louvain.best_partition(G, weight='weight')
    
    import numpy as np
    
    for n in G.nodes():
        G.nodes[n]['degree'] = degrees.get(n, 0)
        G.nodes[n]['weighted_degree'] = weighted_degrees.get(n, 0)
        G.nodes[n]['betweenness_centrality'] = betweenness.get(n, 0.0)
        G.nodes[n]['community'] = partition.get(n, 0)
        G.nodes[n]['label'] = str(n)
        
        # Add a default 'size' attribute so graph viewers (like Gephi) can render nodes with varying sizes immediately
        wd = float(G.nodes[n].get('paper_count', 1))
        # Log scaling to prevent massive nodes from dwarfing the rest
        G.nodes[n]['size'] = max(np.log1p(wd) * 10, 5.0)
        
    # Persist Artifacts
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save GraphML (no layout yet)
    write_graphml(G, out_dir / f"{name}.graphml")
    
    # Save Parquet for rich metadata
    final_nodes = pd.DataFrame.from_dict(dict(G.nodes(data=True)), orient='index')
    final_nodes.index.name = 'id'
    final_nodes.reset_index(inplace=True)
    final_nodes.to_parquet(out_dir / f"{name}_nodes.parquet")

def run():
    print("=" * 70)
    print(" ETL STAGE 2: BUILD GRAPHS")
    print("=" * 70)
    
    in_dir = get_intermediate_data_path("bibliometric-pipeline", "")
    in_path = in_dir / "records.parquet"
    if not in_path.exists():
        raise FileNotFoundError(f"Missing input records at {in_path}")
        
    df = pd.read_parquet(in_path)
    
    process_and_build_graph(df, build_co_author_edges, "co_author", min_weight=2)
    process_and_build_graph(df, build_co_funding_edges, "co_funding", min_weight=2)
    process_and_build_graph(df, build_co_affiliation_edges, "co_affiliation", min_weight=2)
    process_and_build_graph(df, build_author_keywords_edges, "author_keywords", min_weight=2)
    process_and_build_graph(df, build_wos_categories_edges, "wos_categories", min_weight=1)

if __name__ == "__main__":
    run()