import re
import pandas as pd
from itertools import combinations

# --- Normalization Configs ---
_TRUNCATION_SUFFIXES = (
    " of", " for", " the", " and", " in", " at", " on", " to",
    " National", " Science", " Research", " Technology", " Foundation",
    " Council", " Department", " Ministry", " Program", " Key",
    " Natural", " Engineering", " Applied", " University",
)

_GENERIC_BLACKLIST = {
    "university", "institute", "college", "center", "centre",
    "laboratory", "school", "hospital", "clinic", "foundation",
    "academy", "council", "department", "ministry", "agency",
}

_INST_CANONICAL = {
    "chinese acad sci": "Chinese Academy of Sciences",
    "us doe": "United States Department of Energy (DOE)",
    "nanyang technol univ": "Nanyang Technological University",
    "indian inst technol": "Indian Institute of Technology",
    "indian inst technol system": "Indian Institute of Technology System (IIT System)",
    "german res ctr artificial intelligence dfki": "DFKI German Research Center for Artificial Intelligence",
    "helmholtz assoc": "Helmholtz Association",
    "fraunhofer gesellschaft": "Fraunhofer Gesellschaft",
    "natl univ singapore": "National University of Singapore",
    "korean inst sci technol": "Korea Institute of Science and Technology",
    "korea adv inst sci & technol": "Korea Advanced Institute of Science and Technology",
    "swiss fed inst technol": "Swiss Federal Institutes of Technology Domain",
    "texas a&m univ": "Texas A&M University System",
    "georgia inst technol": "Georgia Institute of Technology",
    "massachusetts inst technol": "Massachusetts Institute of Technology",
    "imperial coll london": "Imperial College London",
    "univ calif berkeley": "University of California Berkeley",
    "univ calif los angeles": "University of California Los Angeles",
    "univ mich": "University of Michigan",
    "univ illinois": "University of Illinois",
    "penn state univ": "Pennsylvania State University",
    "ohio state univ": "Ohio State University",
    "univ texas austin": "University of Texas at Austin",
    "univ toronto": "University of Toronto",
    "univ cambridge": "University of Cambridge",
    "univ oxford": "University of Oxford",
    "harvard univ": "Harvard University",
    "stanford univ": "Stanford University",
    "princeton univ": "Princeton University",
    "columbia univ": "Columbia University",
    "cornell univ": "Cornell University",
    "northwestern univ": "Northwestern University",
    "univ penn": "University of Pennsylvania",
    "univ chicago": "University of Chicago",
    "yale univ": "Yale University",
    "ucl": "University College London",
}

_FUNDING_CANONICAL = {
    "nsf": "National Science Foundation",
    "national science foundation (nsf)": "National Science Foundation",
    "national science foundation": "National Science Foundation",
    "nsfc": "National Natural Science Foundation of China",
    "national natural science foundation of china (nsfc)": "National Natural Science Foundation of China",
    "national natural science foundation of china": "National Natural Science Foundation of China",
    "doe": "U.S. Department of Energy",
    "u.s. department of energy (doe)": "U.S. Department of Energy",
    "department of energy": "U.S. Department of Energy",
    "nih": "National Institutes of Health",
    "national institutes of health": "National Institutes of Health",
    "nasa": "National Aeronautics and Space Administration",
    "national aeronautics and space administration": "National Aeronautics and Space Administration",
    "dfg": "German Research Foundation (DFG)",
    "german research foundation": "German Research Foundation (DFG)",
    "epsrc": "Engineering and Physical Sciences Research Council (EPSRC)",
    "nserc": "Natural Sciences and Engineering Research Council of Canada (NSERC)",
    "nrf": "National Research Foundation of Korea",
    "cnpq": "National Council for Scientific and Technological Development (CNPq)",
    "capes": "Coordination for the Improvement of Higher Education Personnel (CAPES)",
    "arc": "Australian Research Council",
    "european union": "European Union",
    "eu": "European Union",
    "european commission": "European Commission",
    "european research council (erc)": "European Research Council",
    "erc": "European Research Council",
}

_FRAGMENT_BLACKLIST = {
    "national", "natural science", "fundamental", "key", "china",
    "science", "research", "technology", "projekt deal", "international",
    "university", "institute", "college", "center", "centre",
    "of", "the", "and", "for", "de", "la", "le", "der", "die", "das",
    "state", "central", "european", "singapore", "army",
    "national", "natural", "european regional",
}

_KNOWN_SINGLE_WORD_ABBREVS = {
    "nsf", "nsfc", "nnsfc", "doe", "nih", "nasa", "dfg", "epsrc", "nserc",
    "nrf", "cnpq", "capes", "arc", "rfbr", "rsf", "eu", "ec", "erc",
    "mext", "jsps", "csc", "dst", "serb", "dod", "afosr", "onr", "darpa",
}

_FUNDING_TRUNCATION_SUFFIXES = _TRUNCATION_SUFFIXES + (
    " Advancement", " Investigator", " Innovation",
    " Civil", " Mechanical", " Bioeng", " Env", " Chem",
    " Basic", " Regional", " Directorate", " Division",
    " R", " D", " Funds", " Funding", " Scientific",
)


# --- Helper Functions ---
_ADDR_INST_RE = re.compile(r"\[.*?\]\s*(.+?)(?:,|$)")
_GRANT_RE = re.compile(r"\s*\[[^\]]*\]")

def canonicalise_inst(name: str) -> str:
    key = str(name).lower().strip()
    return _INST_CANONICAL.get(key, name)

def extract_inst_from_address(raw: str) -> str | None:
    s = str(raw).strip().rstrip(".")
    m = _ADDR_INST_RE.match(s)
    if m:
        return m.group(1).strip()
    parts = s.split(",")
    if parts:
        return parts[0].strip()
    return None

def clean_funding_org(raw: str) -> str | None:
    s = str(raw).strip().rstrip(";").strip()
    s = _GRANT_RE.sub("", s).strip()
    if not s:
        return None
    key = s.lower().strip()
    if key in _FUNDING_CANONICAL:
        return _FUNDING_CANONICAL[key]
    if key in _FRAGMENT_BLACKLIST:
        return None
    if len(s.split()) == 1 and key not in _KNOWN_SINGLE_WORD_ABBREVS:
        return None
    if any(s.lower().endswith(t.lower()) for t in _FUNDING_TRUNCATION_SUFFIXES):
        return None
    if s.endswith(",") or s.endswith("&") or s.endswith("Of"):
        return None
    return s


# --- Edge Builders ---
def build_generic_edges(df: pd.DataFrame, source_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Builds nodes and edges from a list column."""
    if source_col not in df.columns:
        raise KeyError(
            f"Column '{source_col}' not found in DataFrame. Available: {list(df.columns)}"
        )
        
    df_temp = df.copy()
    df_temp["_paper_id"] = range(len(df_temp))

    # Explode the list column
    exploded = df_temp[["_paper_id", source_col]].explode(source_col)
    
    # Drop nulls
    exploded = exploded.dropna(subset=[source_col])
    
    # Convert to string and strip
    exploded[source_col] = exploded[source_col].astype(str).str.strip()
    
    # Drop empty strings
    exploded = exploded[exploded[source_col] != ""]
    
    # Drop duplicate items per paper
    exploded = exploded.drop_duplicates(subset=["_paper_id", source_col])

    if exploded.empty:
        return pd.DataFrame(columns=["id", "paper_count"]), pd.DataFrame(columns=["source", "target", "weight"])

    # Nodes: count unique papers per item
    nodes_df = (
        exploded.groupby(source_col)
        .size()
        .reset_index(name="paper_count")
        .rename(columns={source_col: "id"})
    )

    # Edges: self-merge to find co-occurrences
    merged = pd.merge(exploded, exploded, on="_paper_id", suffixes=("_source", "_target"))
    
    # Keep only source < target to avoid duplicates and self-loops
    merged = merged[merged[f"{source_col}_source"] < merged[f"{source_col}_target"]]
    
    if merged.empty:
        edges_df = pd.DataFrame(columns=["source", "target", "weight"])
    else:
        edges_df = (
            merged.groupby([f"{source_col}_source", f"{source_col}_target"])
            .size()
            .reset_index(name="weight")
            .rename(
                columns={
                    f"{source_col}_source": "source",
                    f"{source_col}_target": "target",
                }
            )
        )
        
    return nodes_df, edges_df


def build_co_author_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uses AU (Authors)"""
    return build_generic_edges(df, "AU")


def build_author_keywords_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uses DE (Author Keywords)"""
    # Keywords are already parsed as list in DE
    # But let's uppercase them to avoid case issues
    def clean_keywords(row):
        items = row.get("DE", [])
        if items is None:
            return []
        try:
            return [str(i).strip().upper() for i in items if str(i).strip()]
        except TypeError:
            return []
    
    df_temp = df.copy()
    df_temp["DE_CLEAN"] = df_temp.apply(clean_keywords, axis=1)
    return build_generic_edges(df_temp, "DE_CLEAN")


def build_wos_categories_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uses WC (WoS Categories)"""
    df_temp = df.copy()
    
    def clean_wc(items):
        if items is None:
            return []
        try:
            return [str(i).strip().upper() for i in items if str(i).strip()]
        except TypeError:
            return []
            
    df_temp["WC_CLEAN"] = df_temp["WC"].apply(clean_wc)
    return build_generic_edges(df_temp, "WC_CLEAN")


def build_co_affiliation_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uses C1 (Addresses) -> extracts institution name."""
    def extract_affiliations(row):
        items = row.get("C1", [])
        if items is None:
            return []
        insts = set()
        try:
            for i in items:
                inst = extract_inst_from_address(i)
                if inst:
                    inst = canonicalise_inst(inst)
                    if inst.lower() not in _GENERIC_BLACKLIST:
                        insts.add(inst)
        except TypeError:
            pass
        return sorted(list(insts))

    df_temp = df.copy()
    df_temp["C1_CLEAN"] = df_temp.apply(extract_affiliations, axis=1)
    return build_generic_edges(df_temp, "C1_CLEAN")


def build_co_funding_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uses FU (Funding Agency) -> extracts clean funder name."""
    def extract_funders(row):
        items = row.get("FU", [])
        if items is None:
            return []
        funders = set()
        try:
            for i in items:
                f = clean_funding_org(i)
                if f:
                    funders.add(f)
        except TypeError:
            pass
        return sorted(list(funders))

    df_temp = df.copy()
    df_temp["FU_CLEAN"] = df_temp.apply(extract_funders, axis=1)
    return build_generic_edges(df_temp, "FU_CLEAN")
