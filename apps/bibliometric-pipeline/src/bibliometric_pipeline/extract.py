"""
=============================================================================
Phase 1: Data Extraction for Bibliometric Networks
=============================================================================
Loads the WoS filtered bibliography once and extracts cleaned entity lists
for all three networks:

  1. Institutions  (from Addresses + non-truncated Affiliations)
  2. Funding Orgs  (from Funding Orgs, with grant stripping & canonicalisation)
  3. Journals      (from Source Title, with normalisation)

Intermediate outputs are saved as CSV so that Phase 2 can build graphs
without re-parsing the raw Excel file (~94K rows, slow to load).

KEY DATA ISSUE: The Affiliations column is truncated at 72 characters by
the WoS Excel export, creating fragment names like "University of" and
"Indian Institute of". The Addresses column is NOT truncated and contains
WoS-abbreviated institution names (e.g. "Georgia Inst Technol"). This
script uses Addresses as the primary source and supplements with clean
Affiliations entries where available. (See ISSUES_LOG.md Issue 1)

Outputs -> outputs/bibliometric_networks/01_*.csv / .json
=============================================================================
"""

import collections
import json
import re
from pathlib import Path

import pandas as pd

from shared_python.paths import get_data_path, get_output_path

# ---------------------------------------------------------------------------
# CONFIGURABLE PARAMETERS
# ---------------------------------------------------------------------------
CONFIG = {
    "data_path": get_data_path("wos_filtered_bibliography.xlsx"),
    "output_dir": get_output_path("bibliometric-pipeline", "temp").parent,
}

print("=" * 70)
print(" PHASE 1: DATA EXTRACTION")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------
print("\n[1/5] Loading data ...")
df = pd.read_excel(
    CONFIG["data_path"],
    usecols=[
        "Addresses",
        "Affiliations",
        "Funding Orgs",
        "Source Title",
        "Publication Year",
        "WoS Categories",
        "UT (Unique WOS ID)",
    ],
)
print(f"  Loaded {len(df):,} records")

# ---------------------------------------------------------------------------
# 2. EXTRACT INSTITUTIONS (Addresses + non-truncated Affiliations)
# ---------------------------------------------------------------------------
print("\n[2/5] Extracting institutions ...")

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
    "korea adv inst sci and technol": "Korea Advanced Institute of Science and Technology",
    "swiss fed inst technol": "Swiss Federal Institutes of Technology Domain",
    "texas a&m univ": "Texas A&M University System",
    "georgia inst technol": "Georgia Institute of Technology",
    "massachusetts inst technol": "Massachusetts Institute of Technology",
    "imperial coll sci technol & med": "Imperial College London",
    "imperial coll london": "Imperial College London",
    "univ london imperial coll sci technol & med": "Imperial College London",
    "univ calif berkeley": "University of California Berkeley",
    "univ calif los angeles": "University of California Los Angeles",
    "univ calif san diego": "University of California San Diego",
    "univ mich": "University of Michigan",
    "univ illinois": "University of Illinois",
    "penn state univ": "Pennsylvania State University",
    "ohio state univ": "Ohio State University",
    "univ texas austin": "University of Texas at Austin",
    "univ texas": "University of Texas System",
    "texas a&m univ coll stn": "Texas A&M University System",
    "natl univ def technol": "National University of Defense Technology",
    "tech univ munich": "Technical University of Munich",
    "tech univ berlin": "Technical University of Berlin",
    "tech univ delft": "Delft University of Technology",
    "univ melbourne": "University of Melbourne",
    "univ toronto": "University of Toronto",
    "univ cambridge": "University of Cambridge",
    "univ oxford": "University of Oxford",
    "univ tokyo": "University of Tokyo",
    "tokyo inst technol": "Tokyo Institute of Technology",
    "osaka univ": "Osaka University",
    "karlsruhe inst technol": "Karlsruhe Institute of Technology",
    "hong kong polytech univ": "Hong Kong Polytechnic University",
    "city univ hong kong": "City University of Hong Kong",
    "univ hong kong": "University of Hong Kong",
    "tsinghua univ": "Tsinghua University",
    "peking univ": "Peking University",
    "shanghai jiao tong univ": "Shanghai Jiao Tong University",
    "zhejiang univ": "Zhejiang University",
    "seoul natl univ": "Seoul National University",
    "politecn milano": "Politecnico di Milano",
    "politecn torino": "Politecnico di Torino",
    "univ bologna": "University of Bologna",
    "univ stuttgart": "University of Stuttgart",
    "univ hannover": "Leibniz Universitat Hannover",
    "tech univ dortmund": "Technical University of Dortmund",
    "politecn cataluna": "Universitat Politecnica de Catalunya",
    "univ politec madrid": "Universidad Politecnica de Madrid",
    "harvard univ": "Harvard University",
    "stanford univ": "Stanford University",
    "princeton univ": "Princeton University",
    "columbia univ": "Columbia University",
    "cornell univ": "Cornell University",
    "northwestern univ": "Northwestern University",
    "univ penn": "University of Pennsylvania",
    "univ chicago": "University of Chicago",
    "yale univ": "Yale University",
    "duke univ": "Duke University",
    "univ wis madison": "University of Wisconsin-Madison",
    "univ minn": "University of Minnesota",
    "purdue univ": "Purdue University",
    "univ washington": "University of Washington",
    "univ pittsburgh": "University of Pittsburgh",
    "univ florida": "University of Florida",
    "univ colorado": "University of Colorado",
    "univ arizona": "University of Arizona",
    "univ southern calif": "University of Southern California",
    "univ nottingham": "University of Nottingham",
    "univ manchester": "University of Manchester",
    "univ edinburgh": "University of Edinburgh",
    "univ birmingham": "University of Birmingham",
    "univ sheffield": "University of Sheffield",
    "univ bristol": "University of Bristol",
    "univ leeds": "University of Leeds",
    "univ southampton": "University of Southampton",
    "univ glasgow": "University of Glasgow",
    "univ new south wales": "University of New South Wales",
    "univ queensland": "University of Queensland",
    "univ sydney": "University of Sydney",
    "monash univ": "Monash University",
    "univ auckland": "University of Auckland",
    "univ technology sydney": "University of Technology Sydney",
    "texas a&m university college station": "Texas A&M University System",
    "oak ridge natl lab": "Oak Ridge National Laboratory",
    "nanjing univ aeronaut & astronaut": "Nanjing University of Aeronautics & Astronautics",
    "missouri univ sci & technol": "Missouri University of Science and Technology",
    "missouri university of science &": "Missouri University of Science and Technology",
    "polytechnic univ turin": "Polytechnic University of Turin",
    "polytechnic univ milan": "Polytechnic University of Milan",
    "politecnico di milano": "Polytechnic University of Milan",
    "politecnico di torino": "Polytechnic University of Turin",
    "univ michigan system": "University of Michigan",
    "fraunhofer germany": "Fraunhofer Gesellschaft",
    "univ sci & technol beijing": "University of Science and Technology Beijing",
    "university of science & technology beijing": "University of Science and Technology Beijing",
    "univ illinois system": "University of Illinois System",
    "pennsylvania commonwealth system of higher education (pcshe)": "Pennsylvania State University",
    "ucl": "University College London",
}

_ADDR_INST_RE = re.compile(r"\[.*?\]\s*(.+?)(?:,|$)")


def extract_inst_from_address(raw: str) -> str | None:
    if pd.isna(raw):
        return None
    s = str(raw).strip().rstrip(".")
    m = _ADDR_INST_RE.match(s)
    if m:
        return m.group(1).strip()
    parts = s.split(",")
    if parts:
        return parts[0].strip()
    return None


def is_truncated(name: str) -> bool:
    return any(name.lower().endswith(s.lower()) for s in _TRUNCATION_SUFFIXES)


def is_generic(name: str) -> bool:
    return name.lower().strip() in _GENERIC_BLACKLIST


def canonicalise_inst(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)
    key = name.lower().strip()
    if key in _INST_CANONICAL:
        return _INST_CANONICAL[key]
    return name


def parse_affiliations_safe(raw: str) -> list[str]:
    if pd.isna(raw):
        return []
    parts = [p.strip().rstrip(";").strip() for p in str(raw).split(";")]
    clean = []
    for p in parts:
        if p and not is_truncated(p) and not is_generic(p):
            clean.append(canonicalise_inst(p))
    return sorted(set(clean))


def build_inst_list(row) -> list[str]:
    insts = set()
    addr_inst = row.get("addr_inst")
    if addr_inst:
        addr_inst = canonicalise_inst(addr_inst)
        if not is_generic(addr_inst):
            insts.add(addr_inst)
    for a in row.get("affil_list", []):
        insts.add(a)
    return sorted(insts)


df["addr_inst"] = df["Addresses"].apply(extract_inst_from_address)
df["affil_list"] = df["Affiliations"].apply(parse_affiliations_safe)
df["inst_list"] = df.apply(build_inst_list, axis=1)

inst_pub_counter: collections.Counter = collections.Counter()
for insts in df["inst_list"]:
    for inst in insts:
        inst_pub_counter[inst] += 1

print(f"  Unique institutions (raw): {len(inst_pub_counter):,}")
print(f"  Top 10 institutions by publication count:")
for inst, count in inst_pub_counter.most_common(10):
    print(f"    {count:4d}  {inst[:70]}")

# ---------------------------------------------------------------------------
# 3. EXTRACT & NORMALISE FUNDING ORGS
# ---------------------------------------------------------------------------
print("\n[3/5] Extracting & normalising funding orgs ...")

_FUNDING_CANONICAL = {
    "nsf": "National Science Foundation",
    "national science foundation (nsf)": "National Science Foundation",
    "national science foundation": "National Science Foundation",
    "nsfc": "National Natural Science Foundation of China",
    "nnsfc": "National Natural Science Foundation of China",
    "national natural science foundation of china (nsfc)": "National Natural Science Foundation of China",
    "national natural science foundation of china (nnsfc)": "National Natural Science Foundation of China",
    "national natural science foundation of china": "National Natural Science Foundation of China",
    "doe": "U.S. Department of Energy",
    "u.s. department of energy (doe)": "U.S. Department of Energy",
    "us department of energy (doe)": "U.S. Department of Energy",
    "department of energy (doe)": "U.S. Department of Energy",
    "department of energy": "U.S. Department of Energy",
    "united states department of energy": "U.S. Department of Energy",
    "u.s. department of energy": "U.S. Department of Energy",
    "us department of energy": "U.S. Department of Energy",
    "nih": "National Institutes of Health",
    "national institutes of health (nih)": "National Institutes of Health",
    "national institutes of health": "National Institutes of Health",
    "u.s. national institutes of health (nih)": "National Institutes of Health",
    "us national institutes of health (nih)": "National Institutes of Health",
    "nasa": "National Aeronautics and Space Administration",
    "national aeronautics and space administration (nasa)": "National Aeronautics and Space Administration",
    "national aeronautics and space administration": "National Aeronautics and Space Administration",
    "u.s. national aeronautics and space administration (nasa)": "National Aeronautics and Space Administration",
    "dfg": "German Research Foundation (DFG)",
    "german research foundation (dfg)": "German Research Foundation (DFG)",
    "german research foundation": "German Research Foundation (DFG)",
    "deutsche forschungsgemeinschaft": "German Research Foundation (DFG)",
    "epsrc": "Engineering and Physical Sciences Research Council (EPSRC)",
    "engineering and physical sciences research council (epsrc)": "Engineering and Physical Sciences Research Council (EPSRC)",
    "engineering and physical sciences research council": "Engineering and Physical Sciences Research Council (EPSRC)",
    "nserc": "Natural Sciences and Engineering Research Council of Canada (NSERC)",
    "natural sciences and engineering research council of canada (nserc)": "Natural Sciences and Engineering Research Council of Canada (NSERC)",
    "natural sciences and engineering research council of canada": "Natural Sciences and Engineering Research Council of Canada (NSERC)",
    "nrf": "National Research Foundation of Korea",
    "national research foundation of korea (nrf)": "National Research Foundation of Korea",
    "national research foundation of korea": "National Research Foundation of Korea",
    "national research foundation of korea (nrf) - korea government (msit)": "National Research Foundation of Korea",
    "cnpq": "National Council for Scientific and Technological Development (CNPq)",
    "national council for scientific and technological development (cnpq)": "National Council for Scientific and Technological Development (CNPq)",
    "national council for scientific and technological development": "National Council for Scientific and Technological Development (CNPq)",
    "conselho nacional de desenvolvimento cientifico e tecnologico": "National Council for Scientific and Technological Development (CNPq)",
    "capes": "Coordination for the Improvement of Higher Education Personnel (CAPES)",
    "coordination for the improvement of higher education personnel (capes)": "Coordination for the Improvement of Higher Education Personnel (CAPES)",
    "coordenacao de aperfeicoamento de pessoal de nivel superior": "Coordination for the Improvement of Higher Education Personnel (CAPES)",
    "arc": "Australian Research Council",
    "australian research council (arc)": "Australian Research Council",
    "australian research council": "Australian Research Council",
    "rfbr": "Russian Foundation for Basic Research",
    "russian foundation for basic research (rfbr)": "Russian Foundation for Basic Research",
    "russian foundation for basic research": "Russian Foundation for Basic Research",
    "rsf": "Russian Science Foundation",
    "russian science foundation (rsf)": "Russian Science Foundation",
    "russian science foundation": "Russian Science Foundation",
    "european union": "European Union",
    "eu": "European Union",
    "european commission": "European Commission",
    "ec": "European Commission",
    "european research council (erc)": "European Research Council",
    "european research council": "European Research Council",
    "erc": "European Research Council",
    "mext": "MEXT (Japan)",
    "ministry of education, culture, sports, science and technology (mext)": "MEXT (Japan)",
    "jsps": "Japan Society for the Promotion of Science",
    "japan society for the promotion of science (jsps)": "Japan Society for the Promotion of Science",
    "japan society for the promotion of science": "Japan Society for the Promotion of Science",
    "csc": "China Scholarship Council",
    "china scholarship council (csc)": "China Scholarship Council",
    "china scholarship council": "China Scholarship Council",
    "dst": "Department of Science and Technology (India)",
    "department of science and technology (dst)": "Department of Science and Technology (India)",
    "department of science and technology": "Department of Science and Technology (India)",
    "serb": "Science and Engineering Research Board (India)",
    "science and engineering research board (serb)": "Science and Engineering Research Board (India)",
    "science and engineering research board": "Science and Engineering Research Board (India)",
    "dod": "U.S. Department of Defense",
    "u.s. department of defense (dod)": "U.S. Department of Defense",
    "department of defense (dod)": "U.S. Department of Defense",
    "department of defense": "U.S. Department of Defense",
    "air force office of scientific research (afosr)": "Air Force Office of Scientific Research",
    "afosr": "Air Force Office of Scientific Research",
    "office of naval research (onr)": "Office of Naval Research",
    "onr": "Office of Naval Research",
    "darpa": "DARPA",
    "defense advanced research projects agency (darpa)": "DARPA",
    "defense advanced research projects agency": "DARPA",
    "sfi": "Science Foundation Ireland",
    "science foundation ireland (sfi)": "Science Foundation Ireland",
    "science foundation ireland": "Science Foundation Ireland",
    "ncn": "National Science Centre Poland",
    "national science centre poland (ncn)": "National Science Centre Poland",
    "national science centre poland": "National Science Centre Poland",
    "national science centre": "National Science Centre Poland",
    "tubitak": "TUBITAK",
    "the scientific and technological research council of turkey (tubitak)": "TUBITAK",
    "mpst": "Ministry of Science and Technology (China)",
    "ministry of science and technology of the people's republic of china": "Ministry of Science and Technology (China)",
    "ministry of science and technology of china": "Ministry of Science and Technology (China)",
    "ministry of science and technology (most)": "Ministry of Science and Technology (China)",
    "most": "Ministry of Science and Technology (China)",
    "national key research and development program of china": "National Key R&D Program of China",
    "national key r&d program of china": "National Key R&D Program of China",
}

_FRAGMENT_BLACKLIST = {
    "national", "natural science", "fundamental", "key", "china",
    "science", "research", "technology", "projekt deal", "international",
    "university", "institute", "college", "center", "centre",
    "of", "the", "and", "for", "de", "la", "le", "der", "die", "das",
    "natural", "shanghai", "beijing", "zhejiang", "guangdong", "jiangsu",
    "shandong", "hunan", "hubei", "fujian", "shenzhen", "liaoning",
    "shaanxi", "shanxi", "chongqing", "tianjin", "guangzhou", "jiangxi",
    "sichuan", "outstanding", "youth", "young", "basic", "innovation",
    "priority", "strategic", "major", "intelligent", "open", "general",
    "joint", "royal", "german", "deutsche", "australian", "canadian",
    "swedish", "russian", "chinese", "egyptian", "korean", "ontario",
    "directorate", "division", "div", "ministry", "foundation",
    "medical", "mechanical", "scientific", "welding", "aeronautical",
    "state", "central", "european", "singapore", "army",
    "guangdong basic", "d program", "d program of china",
    "national", "natural",
    "epsrc funding source: ukri", "regione lombardia", "repubblica italiana",
    "european regional",
    "key scientific", "research fund", "h2020 societal challenges programme",
    "fundamental research funds", "h2020 - industrial leadership funding",
    "marie curie actions (msca) funding",
}

_KNOWN_SINGLE_WORD_ABBREVS = {
    "nsf", "nsfc", "nnsfc", "doe", "nih", "nasa", "dfg", "epsrc", "nserc",
    "nrf", "cnpq", "capes", "arc", "rfbr", "rsf", "eu", "ec", "erc",
    "mext", "jsps", "csc", "dst", "serb", "dod", "afosr", "onr", "darpa",
    "sfi", "ncn", "tubitak", "mpst", "most", "fapesp", "fapemig", "faperj",
    "finep", "fesr", "bmbf", "anid", "cas", "nsaf", "conacyt", "vinnova",
    "snf", "aro", "feder", "crue-csic", "mciu/aei", "mcin/aei",
}

_FUNDING_TRUNCATION_SUFFIXES = (
    " of", " for", " the", " and", " in", " at", " on", " to",
    " National", " Science", " Research", " Technology", " Foundation",
    " Council", " Department", " Ministry", " Program", " Key",
    " Natural", " Engineering", " Applied", " University",
    " Advancement", " Investigator", " Innovation",
    " Civil", " Mechanical", " Bioeng", " Env", " Chem",
    " Basic", " Regional", " Directorate", " Division",
    " R", " D", " Funds", " Funding", " Scientific",
)

_GRANT_RE = re.compile(r"\s*\[[^\]]*\]")

canonicalisation_log: dict[str, str] = {}


def clean_funding_org(raw: str) -> str | None:
    if pd.isna(raw):
        return None
    s = str(raw).strip().rstrip(";").strip()
    s = _GRANT_RE.sub("", s).strip()
    if not s:
        return None
    key = s.lower().strip()
    if key in _FUNDING_CANONICAL:
        canonical = _FUNDING_CANONICAL[key]
        if s != canonical:
            canonicalisation_log[s] = canonical
        return canonical
    if key in _FRAGMENT_BLACKLIST:
        return None
    if len(s.split()) == 1 and key not in _KNOWN_SINGLE_WORD_ABBREVS:
        return None
    if any(s.lower().endswith(t.lower()) for t in _FUNDING_TRUNCATION_SUFFIXES):
        return None
    if s.endswith(",") or s.endswith("&") or s.endswith("Of"):
        return None
    return s


def parse_funding_orgs(raw) -> list[str]:
    if pd.isna(raw):
        return []
    parts = [p.strip().rstrip(";").strip() for p in str(raw).split(";")]
    cleaned = []
    for p in parts:
        c = clean_funding_org(p)
        if c is not None:
            cleaned.append(c)
    return sorted(set(cleaned))


df["funder_list"] = df["Funding Orgs"].apply(parse_funding_orgs)

fund_pub_counter: collections.Counter = collections.Counter()
for funders in df["funder_list"]:
    for f in funders:
        fund_pub_counter[f] += 1

print(f"  Unique funders (raw): {len(fund_pub_counter):,}")
print(f"  Canonicalisation mappings: {len(canonicalisation_log):,}")
print(f"  Top 10 funders by publication count:")
for org, count in fund_pub_counter.most_common(10):
    print(f"    {count:4d}  {org[:70]}")

# ---------------------------------------------------------------------------
# 4. NORMALISE JOURNALS
# ---------------------------------------------------------------------------
print("\n[4/5] Normalising journals ...")

_JOURNAL_DUPLICATES = {
    "MATERIALS": "MATERIALS",
    "MICROMACHINES": "MICROMACHINES",
    "ACS APPLIED MATERIALS AND INTERFACES": "ACS APPLIED MATERIALS AND INTERFACES",
    "ACS APPLIED MATERIALS & INTERFACES": "ACS APPLIED MATERIALS AND INTERFACES",
    "CLEFT PALATE CRANIOFACIAL JOURNAL": "CLEFT PALATE-CRANIOFACIAL JOURNAL",
    "CLEFT PALATE-CRANIOFACIAL JOURNAL": "CLEFT PALATE-CRANIOFACIAL JOURNAL",
    "LC GC NORTH AMERICA": "LCGC NORTH AMERICA",
    "LCGC NORTH AMERICA": "LCGC NORTH AMERICA",
    "SCIENCE OF ADVANCED MATERIALS": "SCIENCE OF ADVANCED MATERIALS",
    "AEROSPACE": "AEROSPACE",
    "AEROSPACE-BASEL": "AEROSPACE-BASEL",
    "ACS ES AND T ENGINEERING": "ACS ES&T ENGINEERING",
    "ACS ES&T ENGINEERING": "ACS ES&T ENGINEERING",
    "ACS EST ENGINEERING": "ACS ES&T ENGINEERING",
    "APPLIED CATALYSIS B-ENVIRONMENT AND ENERGY": "APPLIED CATALYSIS B-ENVIRONMENTAL",
    "APPLIED CATALYSIS B-ENVIRONMENTAL": "APPLIED CATALYSIS B-ENVIRONMENTAL",
}


def normalise_journal(raw: str) -> str:
    if pd.isna(raw):
        return ""
    s = str(raw).strip().upper()
    s = s.replace("&", "AND")
    key = s
    if key in _JOURNAL_DUPLICATES:
        return _JOURNAL_DUPLICATES[key]
    return s


df["journal"] = df["Source Title"].apply(normalise_journal)

journal_pub_counter: collections.Counter = collections.Counter()
for j in df["journal"]:
    if j:
        journal_pub_counter[j] += 1

print(f"  Unique journals (raw): {len(journal_pub_counter):,}")
print(f"  Top 10 journals by publication count:")
for journal, count in journal_pub_counter.most_common(10):
    print(f"    {count:4d}  {journal[:70]}")

# ---------------------------------------------------------------------------
# 5. SAVE INTERMEDIATE FILES
# ---------------------------------------------------------------------------
print("\n[5/5] Saving intermediate files ...")

# Save per-paper extracted lists as a lightweight CSV (only the columns
# needed for graph building; the heavy raw columns are dropped).
export_cols = [
    "UT (Unique WOS ID)",
    "Publication Year",
    "inst_list",
    "funder_list",
    "journal",
    "WoS Categories",
]
df_out = df[export_cols].copy()

# Serialise list columns as semicolon-joined strings for CSV round-trip
df_out["inst_list"] = df_out["inst_list"].apply(lambda x: ";".join(x))
df_out["funder_list"] = df_out["funder_list"].apply(lambda x: ";".join(x))

df_out.to_csv(CONFIG["output_dir"] / "01_papers_extracted.csv", index=False)
print(f"  Saved 01_papers_extracted.csv ({len(df_out):,} rows)")

# Save canonicalisation audit log
if canonicalisation_log:
    canon_df = pd.DataFrame(
        list(canonicalisation_log.items()), columns=["original", "canonical"]
    )
    canon_df.to_csv(CONFIG["output_dir"] / "01_funding_canonicalization_map.csv", index=False)
    print(f"  Saved 01_funding_canonicalization_map.csv ({len(canon_df)} mappings)")

# Save extraction summary
summary = {
    "total_publications": len(df),
    "institutions": {
        "unique": len(inst_pub_counter),
        "publications_with_institutions": sum(1 for il in df["inst_list"] if il),
    },
    "funding_orgs": {
        "unique": len(fund_pub_counter),
        "publications_with_funding": sum(1 for fl in df["funder_list"] if fl),
        "canonicalisation_mappings": len(canonicalisation_log),
    },
    "journals": {
        "unique": len(journal_pub_counter),
        "publications_with_journals": sum(1 for j in df["journal"] if j),
    },
}

with open(CONFIG["output_dir"] / "01_extraction_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"  Saved 01_extraction_summary.json")

print("\n" + "=" * 70)
print(" PHASE 1 COMPLETE")
print("=" * 70)
