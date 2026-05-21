import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def compute_diversity_metrics(
    records_df: pd.DataFrame, 
    group_col: str = "PY", 
    category_col: str = "WC", 
    n_max: int = 254
) -> pd.DataFrame:
    """
    Computes Variety (N), Shannon (H), Simpson (I), and Stirling (Delta) indices 
    for each group (e.g., Publication Year).
    
    Args:
        records_df: Parsed WoS records.
        group_col: Column to group by (unit of analysis).
        category_col: The category column containing lists of categories (e.g., 'WC').
        n_max: Total theoretical number of categories (254 for modern WoS, 175 for old SCI).
        
    Returns:
        DataFrame with groups as index and metrics (N, H, I, Delta) as columns.
    """
    
    # 1. Prepare data - explode categories
    df_temp = records_df[[group_col, category_col]].copy()
    # Handle possible NaN/None in lists
    def clean_categories(items):
        if items is None:
            return []
        try:
            return [str(i).strip().upper() for i in items if str(i).strip()]
        except TypeError:
            return []
            
    df_temp[category_col] = df_temp[category_col].apply(clean_categories)
    df_exploded = df_temp.explode(category_col)
    df_exploded = df_exploded.dropna(subset=[group_col, category_col])
    df_exploded[category_col] = df_exploded[category_col].astype(str)
    df_exploded = df_exploded[df_exploded[category_col] != ""]
    
    if df_exploded.empty:
        logger.warning("No valid categories found after exploding.")
        return pd.DataFrame(columns=["N", "H", "I", "Delta"])

    # List of unique categories present in the data
    active_categories = df_exploded[category_col].unique()
    num_active = len(active_categories)
    cat_to_idx = {cat: i for i, cat in enumerate(active_categories)}
    
    # 2. Build Proxy Similarity Matrix (Salton's Cosine)
    # We will build it from co-occurrences in the entire dataset
    # We need c_ij (co-occurrence) and c_ii (diagonal, total paper count per category)
    
    # c_ii calculation (count of unique papers per category)
    # We need paper id for this. Let's add it.
    df_temp["_paper_id"] = range(len(df_temp))
    df_exploded_with_id = df_temp[["_paper_id", category_col]].explode(category_col)
    df_exploded_with_id = df_exploded_with_id.dropna(subset=[category_col])
    df_exploded_with_id[category_col] = df_exploded_with_id[category_col].astype(str).str.strip().str.upper()
    df_exploded_with_id = df_exploded_with_id[df_exploded_with_id[category_col] != ""]
    # unique papers per category
    df_exploded_with_id = df_exploded_with_id.drop_duplicates(subset=["_paper_id", category_col])
    
    c_ii_series = df_exploded_with_id.groupby(category_col).size()
    
    # Co-occurrence c_ij
    merged = pd.merge(df_exploded_with_id, df_exploded_with_id, on="_paper_id", suffixes=("_source", "_target"))
    # We want full matrix, so we can just count all pairs (including i < j, i > j, and i == j)
    # Actually, diagonal is just c_ii, so we only need to group and size
    co_occurrences = merged.groupby([f"{category_col}_source", f"{category_col}_target"]).size().reset_index(name="weight")
    
    # Initialize similarity matrix s_matrix with 0
    s_matrix = np.zeros((num_active, num_active))
    
    # Fill s_matrix using Salton's cosine
    logger.info("Building proxy similarity matrix (Salton's cosine)...")
    for _, row in co_occurrences.iterrows():
        src = row[f"{category_col}_source"]
        tgt = row[f"{category_col}_target"]
        w = row["weight"]
        
        i = cat_to_idx[src]
        j = cat_to_idx[tgt]
        
        c_ii = c_ii_series.get(src, 0)
        c_jj = c_ii_series.get(tgt, 0)
        
        if c_ii > 0 and c_jj > 0:
            s_matrix[i, j] = w / np.sqrt(c_ii * c_jj)
    
    # ENSURE DIAGONAL IS EXACTLY 1.0 TO AVOID FLOATING POINT IMPRECISION CORRUPTING DELTA
    np.fill_diagonal(s_matrix, 1.0)
    
    # 3. Compute distributions p_i and metrics per group
    results = []
    groups = df_exploded.groupby(group_col)
    
    for group_name, group_df in groups:
        # p_i distribution
        cat_counts = group_df[category_col].value_counts()
        total_occurrences = cat_counts.sum()
        
        if total_occurrences == 0:
            continue
            
        p = np.zeros(num_active)
        for cat, count in cat_counts.items():
            if cat in cat_to_idx:
                p[cat_to_idx[cat]] = count / total_occurrences
                
        # Variety (N)
        active_in_group = (p > 0).sum()
        N = active_in_group / n_max
        
        # Balance (H - Shannon)
        p_nonzero = p[p > 0]
        H_raw = -np.sum(p_nonzero * np.log(p_nonzero))
        H = H_raw / np.log(n_max) if n_max > 1 else 0
        
        # Balance (I - Simpson)
        I = 1 - np.sum(p**2)
        
        # Integration (Delta - Stirling)
        # Vectorized formula: 1 - sum_{i,j} (s_ij * p_i * p_j)
        p_matrix = np.outer(p, p)
        Delta = 1 - np.sum(s_matrix * p_matrix)
        
        results.append({
            group_col: group_name,
            "N": N,
            "H": H,
            "I": I,
            "Delta": Delta
        })
        
    results_df = pd.DataFrame(results).set_index(group_col).sort_index()
    return results_df
