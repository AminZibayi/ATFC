import networkx as nx
import pandas as pd
import argparse
import tomllib
from pathlib import Path

from shared_python.paths import get_output_path, get_workspace_root
from bibliometric_pipeline.layout.compute import compute_layout
from bibliometric_pipeline.io.writers import write_graphml

def process_and_apply_layout(name: str, algorithm: str = None, iterations: int = None, **kwargs):
    print(f"\nApplying layout to {name} graph...")
    out_dir = get_output_path("bibliometric-pipeline", "graphs")
    
    graphml_path = out_dir / f"{name}.graphml"
    parquet_path = out_dir / f"{name}_nodes.parquet"
    
    if not graphml_path.exists():
        print(f"  Skipping {name}, graphml not found.")
        return
        
    G = nx.read_graphml(graphml_path)
    
    # Attempt warm-start from existing parquet coordinates
    pos = None
    if parquet_path.exists():
        try:
            nodes_df = pd.read_parquet(parquet_path)
            if 'x' in nodes_df.columns and 'y' in nodes_df.columns:
                nodes_df['id'] = nodes_df['id'].astype(str)
                pos = {
                    row['id']: (float(row['x']), float(row['y']))
                    for _, row in nodes_df.iterrows()
                    if row['id'] in G
                }
        except Exception as e:
            print(f"  Could not load warm-start positions: {e}")
    
    print("  Computing layout...")
    compute_layout(G, algorithm=algorithm, iterations=iterations, pos=pos, **kwargs)
    
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
    # Load config defaults
    config_path = get_workspace_root() / "apps" / "bibliometric-pipeline" / "config.toml"
    default_algo = "pyforceatlas2"
    default_iters = None
    layout_config = {}
    graph_configs = {}
    
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            layout_config = config.get("layout", {})
            default_algo = layout_config.get("algorithm", default_algo)
            default_iters = layout_config.get("iterations", default_iters)
            
            for key in ["co_author", "co_funding", "co_affiliation", "author_keywords", "wos_categories"]:
                graph_configs[key] = config.get(key, {})

    parser = argparse.ArgumentParser(description="Apply layout to bibliometric graphs.")
    parser.add_argument("--algorithm", type=str, default=None, choices=["pyforceatlas2", "fa2", "sfdp", "yifan_hu"], help="Layout algorithm to use")
    parser.add_argument("--iterations", type=int, default=None, help="Number of iterations for the layout algorithm")
    args = parser.parse_args()

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
        graph_cfg = graph_configs.get(g, {})
        graph_layout = graph_cfg.get("layout", {})
        
        # Resolve algorithm: per-graph > CLI > global default
        g_algo = graph_layout.get("algorithm") or args.algorithm or default_algo
        # Resolve iterations: per-graph > CLI > global default > auto (None)
        g_iters = graph_layout.get("iterations")
        if g_iters is None:
            g_iters = args.iterations
        if g_iters is None:
            g_iters = default_iters
        
        # Select kwargs based on the resolved algorithm
        algo_key = "forceatlas2" if g_algo in ["pyforceatlas2", "fa2"] else "sfdp"
        base_kwargs = layout_config.get(algo_key, {})
        # Per-graph layout overrides for kwargs (filter out algo/iters)
        override_kwargs = {k: v for k, v in graph_layout.items() if k not in ("algorithm", "iterations")}
        g_kwargs = {**base_kwargs, **override_kwargs}
        
        print(f"\n-> {g}: algorithm={g_algo}, iterations={g_iters or 'auto'}")
        process_and_apply_layout(g, algorithm=g_algo, iterations=g_iters, **g_kwargs)

if __name__ == "__main__":
    run()
