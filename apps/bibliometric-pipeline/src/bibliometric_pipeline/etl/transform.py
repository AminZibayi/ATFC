import pandas as pd
from pathlib import Path
from shared_python.paths import get_intermediate_data_path
from bibliometric_pipeline.graphs.builders import (
    build_co_author_edges,
    build_co_funding_edges,
    build_co_affiliation_edges,
    build_author_keywords_edges,
    build_wos_categories_edges,
)

def transform_graph(df: pd.DataFrame, builder_fn, name: str, min_weight: int = 2):
    print(f"Building {name} edges...")
    edges = builder_fn(df)
    if not edges.empty:
        edges = edges[edges['weight'] >= min_weight]
    print(f"  Generated {len(edges)} edges for {name} (min_weight={min_weight})")
    
    out_dir = get_intermediate_data_path("bibliometric-pipeline", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"edges_{name}.parquet"
    edges.to_parquet(out_path)

def run():
    print("=" * 70)
    print(" ETL STAGE 2: TRANSFORM")
    print("=" * 70)
    
    in_dir = get_intermediate_data_path("bibliometric-pipeline", "")
    in_path = in_dir / "records.parquet"
    if not in_path.exists():
        raise FileNotFoundError(f"Missing input records at {in_path}")
        
    df = pd.read_parquet(in_path)
    
    # We can tune the min_weight per graph to reduce noise
    transform_graph(df, build_co_author_edges, "co_author", min_weight=2)
    transform_graph(df, build_co_funding_edges, "co_funding", min_weight=2)
    transform_graph(df, build_co_affiliation_edges, "co_affiliation", min_weight=2)
    transform_graph(df, build_author_keywords_edges, "author_keywords", min_weight=2)
    transform_graph(df, build_wos_categories_edges, "wos_categories", min_weight=1)
    
if __name__ == "__main__":
    run()