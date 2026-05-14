import pandas as pd
from pathlib import Path
from shared_python.paths import get_raw_data_path, get_intermediate_data_path, get_raw_dir

def parse_wos_text_file(filepath: Path) -> pd.DataFrame:
    records = []
    current_record = {}
    current_tag = None
    
    # Tags where each line is a distinct list item
    line_list_tags = {'AU', 'AF', 'C1', 'CR'}
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
                
            stripped = line.strip()
            if stripped == 'ER':
                if 'UT' in current_record:
                    records.append(current_record)
                current_record = {}
                current_tag = None
                continue
            
            if stripped == 'EF':
                break
                
            if line.startswith(('FN ', 'VR ')):
                continue
                
            # Check if continuation line (WOS continuation: exactly 3 spaces)
            if line.startswith('   '):
                val = stripped
                if current_tag and val:
                    if current_tag in line_list_tags:
                        current_record[current_tag].append(val)
                    else:
                        current_record[current_tag] += ' ' + val
                continue
                
            # New tag: exactly 2 chars, then a space
            if len(line) >= 3 and line[2] == ' ' and line[0:2] != '  ':
                tag = line[:2]
                val = line[3:].strip()
                current_tag = tag
                
                if tag in line_list_tags:
                    current_record[tag] = [val] if val else []
                else:
                    current_record[tag] = val

    if current_record and 'UT' in current_record:
        records.append(current_record)

    df = pd.DataFrame(records)
    
    # Post-process semicolon-separated fields
    semicolon_tags = {'DE', 'ID', 'WC', 'FU'}
    for tag in semicolon_tags:
        if tag in df.columns:
            # fillna with empty string first
            df[tag] = df[tag].fillna("")
            df[tag] = df[tag].apply(lambda x: [item.strip() for item in x.split(';')] if x else [])
        else:
            df[tag] = [[] for _ in range(len(df))]
            
    # Ensure line list tags are lists
    for tag in line_list_tags:
        if tag in df.columns:
            df[tag] = df[tag].apply(lambda x: x if isinstance(x, list) else [])
        else:
            df[tag] = [[] for _ in range(len(df))]

    # Ensure other important fields exist
    for tag in ['UT', 'TI', 'SO', 'PY']:
        if tag not in df.columns:
            df[tag] = ""

    return df

def run():
    print("=" * 70)
    print(" ETL STAGE 1: EXTRACT")
    print("=" * 70)
    
    # Locate data/raw folder
    raw_dir = get_raw_dir()
    wos_files = list(raw_dir.glob("wos_*.txt"))
    if not wos_files:
        raise FileNotFoundError(f"No WOS text file found in {raw_dir}")
        
    wos_file = wos_files[0]
    print(f"Parsing {wos_file} ...")
    
    df = parse_wos_text_file(wos_file)
    # Deduplicate by UT
    df = df.drop_duplicates(subset=['UT'])
    print(f"Extracted {len(df)} unique records.")
    
    out_dir = get_intermediate_data_path("bibliometric-pipeline", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "records.parquet"
    
    df.to_parquet(out_path)
    print(f"Saved parsed records to {out_path}")

if __name__ == "__main__":
    run()