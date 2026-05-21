import argparse
import logging
from pathlib import Path
import pandas as pd

from bibliometric_pipeline.metrics.diversity import compute_diversity_metrics
from shared_python.paths import get_intermediate_data_path, get_output_path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Calculate Diversity Metrics (Stirling Index)")
    parser.add_argument("--group-col", default="PY", help="Column to group by (e.g. PY for Publication Year)")
    parser.add_argument("--n-max", type=int, default=254, help="Total theoretical maximum categories")
    args = parser.parse_args()

    # Define paths
    input_path = get_intermediate_data_path("bibliometric-pipeline", "records.parquet")
    output_path = get_output_path("bibliometric-pipeline", "metrics/diversity_metrics.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    logger.info(f"Loading parsed records from {input_path}")
    df = pd.read_parquet(input_path)
    
    logger.info(f"Computing diversity metrics across {args.group_col} with N_max={args.n_max}")
    metrics_df = compute_diversity_metrics(df, group_col=args.group_col, category_col="WC", n_max=args.n_max)
    
    if metrics_df.empty:
        logger.warning("No metrics computed. Check your data.")
        return

    # Save to CSV
    metrics_df.to_csv(output_path)
    logger.info(f"Saved diversity metrics to {output_path}")
    
    # Print table
    print(f"\n--- Diversity Metrics by {args.group_col} ---")
    
    # Format table for console
    formatted_df = metrics_df.copy()
    for col in ["N", "H", "I", "Delta"]:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.4f}")
        
    formatted_df = formatted_df.rename(columns={
        "N": "N (Variety)", 
        "H": "H (Shannon)", 
        "I": "I (Simpson)", 
        "Delta": "Delta (Stirling)"
    })
    
    # Reset index to print unit column cleanly
    formatted_df = formatted_df.reset_index()
    formatted_df = formatted_df.rename(columns={args.group_col: "Unit"})
    
    print(formatted_df.to_string(index=False))

if __name__ == "__main__":
    main()
