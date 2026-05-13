import networkx as nx
import pandas as pd
import argparse
from pathlib import Path

from shared_python.paths import get_output_path
from bibliometric_pipeline.layout.compute import compute_layout
from bibliometric_pipeline.io.writers import write_graphml

def process_and_apply_layout(name: str, algorithm: str = None, iterations: int = None):
    print(f"\nApplying layout to {name} graph...")
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    
    graphml_path = out_dir / f"{name}.graphml"
    parquet_path = out_dir / f"{name}_nodes.parquet"
    
    if not graphml_path.exists():
        print(f"  Skipping {name}, graphml not found.")
        return
        
    G = nx.read_graphml(graphml_path)
    
    print("  Computing layout...")
    compute_layout(G, algorithm=algorithm, iterations=iterations)
    
    # Save the updated GraphML with x and y coordinates
    layout_graphml_path = out_dir / f"{name}_layout.graphml"
    write_graphml(G, layout_graphml_path)
    
    # Update the parquet nodes file with x and y coordinates
    if parquet_path.exists():
        nodes_df = pd.read_parquet(parquet_path)
        
        # Get coordinates from graph
        coords = [{'id': str(n), 'x': G.nodes[n].get('x', 0), 'y': G.nodes[n].get('y', 0)} for n in G.nodes()]
        coords_df = pd.DataFrame(coords)
        
        # Merge
        nodes_df['id'] = nodes_df['id'].astype(str)
        
        if 'x' in nodes_df.columns:
            nodes_df = nodes_df.drop(columns=['x', 'y'])
            
        nodes_df = pd.merge(nodes_df, coords_df, on='id', how='left')
        nodes_df.to_parquet(parquet_path)
    else:
        print(f"  Warning: Parquet file not found for {name}, couldn't update coordinates.")

def run():
    parser = argparse.ArgumentParser(description="Apply layout to bibliometric graphs.")
    parser.add_argument("--algorithm", type=str, default="pyforceatlas2", choices=["pyforceatlas2", "fa2", "sfdp", "yifan_hu"], help="Layout algorithm to use (default: pyforceatlas2)")
    parser.add_argument("--iterations", type=int, default=2000, help="Number of iterations for the layout algorithm (default: 2000)")
    args = parser.parse_args()

    print("=" * 70)
    print(" ETL STAGE 3: APPLY LAYOUT")
    print(f" Algorithm: {args.algorithm}, Iterations: {args.iterations}")
    print("=" * 70)
    
    graphs = [
        "co_author",
        "co_funding",
        "co_affiliation",
        "author_keywords",
        "wos_categories",
    ]
    
    for g in graphs:
        process_and_apply_layout(g, algorithm=args.algorithm, iterations=args.iterations)

if __name__ == "__main__":
    run()