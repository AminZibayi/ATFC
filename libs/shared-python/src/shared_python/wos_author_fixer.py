"""
Optimized script to fix the Authors column in wos_raw_bibliography.xlsx.
Combines pattern matching, lowercase-rejection, and smart deduplication.
"""

import pandas as pd
import re
import sys
from shared_python.paths import get_data_path

def normalize_name(name: str) -> str:
    """Normalize names for better deduplication (e.g. 'Smith, J.P.' -> 'smith,jp')"""
    if not name: return ""
    return re.sub(r'[\s\.]', '', name).lower()

def is_author_name(token: str, author_pattern: re.Pattern) -> bool:
    """Validate if a token is an author name using pattern and metadata rejection."""
    token = token.strip()
    if not author_pattern.match(token):
        return False
    
    if ',' in token:
        suffix = token.split(',', 1)[1].strip()
        if re.search(r'\b[a-z]{3,}\b', suffix):
            return False
            
    return True

def extract_authors_from_unnamed4(value, author_pattern: re.Pattern) -> list:
    """Extract unique author names from the Unnamed: 4 column."""
    if pd.isna(value) or str(value).strip() == '':
        return []

    tokens = [t.strip() for t in str(value).split(';') if t.strip()]
    
    extracted = []
    seen_normalized = set()

    for token in tokens:
        if is_author_name(token, author_pattern):
            norm = normalize_name(token)
            if norm not in seen_normalized:
                extracted.append(token)
                seen_normalized.add(norm)
        elif extracted:
            break
            
    return extracted

def combine_and_deduplicate(primary: str, extra: list) -> str:
    """Merge primary author with extras, ensuring no duplicates."""
    all_names = []
    seen_normalized = set()
    
    if primary and str(primary).strip().lower() != 'nan':
        p_list = [a.strip() for a in str(primary).split(';') if a.strip()]
        for p in p_list:
            norm = normalize_name(p)
            if norm not in seen_normalized:
                all_names.append(p)
                seen_normalized.add(norm)
                
    for e in extra:
        norm = normalize_name(e)
        if norm not in seen_normalized:
            all_names.append(e)
            seen_normalized.add(norm)
            
    return '; '.join(all_names)

def run_fix():
    sys.stdout.reconfigure(encoding='utf-8')

    input_file = get_data_path('wos_raw_bibliography.xlsx')
    output_file = get_data_path('wos_raw_bibliography_fixed.xlsx')

    author_pattern = re.compile(r'^[A-Z][a-zA-ZÀ-ÿ\s\-\']+,[\s]+[A-Z][a-zA-ZÀ-ÿ\s\.\-\']*$')

    print(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file, dtype=str) 
    print(f"Loaded {len(df)} rows.")

    print("Processing Author extraction...")
    df['Authors'] = [
        combine_and_deduplicate(row['Authors'], extract_authors_from_unnamed4(row['Unnamed: 4'], author_pattern))
        for _, row in df.iterrows()
    ]

    print(f"Saving to {output_file}...")
    df.to_excel(output_file, index=False, engine='openpyxl')
    print("Done! Cleanup complete.")

if __name__ == "__main__":
    run_fix()
