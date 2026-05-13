import networkx as nx
import pandas as pd
from pathlib import Path

from shared_python.paths import get_output_path
from bibliometric_pipeline.layout.forceatlas2 import compute_forceatlas2_layout
from bibliometric_pipeline.io.writers import write_graphml

def process_and_apply_layout(name: str):
    print(f"\nApplying layout to {name} graph...")
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    
    graphml_path = out_dir / f"{name}.graphml"
    parquet_path = out_dir / f"{name}_nodes.parquet"
    
    if not graphml_path.exists():
        print(f"  Skipping {name}, graphml not found.")
        return
        
    G = nx.read_graphml(graphml_path)
    
    print("  Computing ForceAtlas2 layout...")
    compute_forceatlas2_layout(G, iterations=2000)
    
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
    print("=" * 70)
    print(" ETL STAGE 3: APPLY LAYOUT")
    print("=" * 70)
    
    graphs = [
        "co_author",
        "co_funding",
        "co_affiliation",
        "author_keywords",
        "wos_categories",
    ]
    
    for g in graphs:
        process_and_apply_layout(g)

if __name__ == "__main__":
    run()