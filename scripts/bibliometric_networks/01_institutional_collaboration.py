"""
=============================================================================
 Institutional Collaboration Network
=============================================================================
 Builds a co-authorship network where nodes = institutions (extracted from
 the Addresses column, supplemented by non-truncated Affiliations entries)
 and edges = co-occurrence on the same paper.  Edge weight = number of
 shared papers.

 KEY DATA ISSUE: The Affiliations column is truncated at 72 characters by
 the WoS Excel export, creating fragment names like "University of" and
 "Indian Institute of".  The Addresses column is NOT truncated and contains
 WoS-abbreviated institution names (e.g. "Georgia Inst Technol").  This
 script uses Addresses as the primary source and supplements with clean
 Affiliations entries where available.

 Outputs  -> outputs/bibliometric_networks/institutional_*.xlsx
 Plots    -> plots/bibliometric_networks/institutional_*.png/.html
=============================================================================
"""

import itertools
import collections
import re
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
#  CONFIGURABLE PARAMETERS -- edit these to adjust the analysis
# ---------------------------------------------------------------------------
CONFIG = {
    "data_path": Path("../../data_source/wos_filtered_bibliography.xlsx"),
    "output_dir": Path("../../outputs/bibliometric_networks"),
    "plot_dir": Path("../../plots/bibliometric_networks"),

    "min_publications": 5,
    "min_edge_weight": 3,
    "top_n_labels": 30,
    "top_n_bar": 20,

    "layout_seed": 42,
    "layout_iterations": 150,
    "figure_dpi": 200,
    "figure_size": (22, 18),
    "node_size_scale": 80,
    "edge_width_scale": 0.6,
    "max_edge_width": 6,
}

# ---------------------------------------------------------------------------
#  TRUNCATION DETECTION -- suffixes that indicate a name was cut off
#  at the 72-char WoS export boundary (see ISSUES_LOG.md Issue 1)
# ---------------------------------------------------------------------------
_TRUNCATION_SUFFIXES = (
    " of", " for", " the", " and", " in", " at", " on", " to",
    " National", " Science", " Research", " Technology", " Foundation",
    " Council", " Department", " Ministry", " Program", " Key",
    " Natural", " Engineering", " Applied", " University",
)

# ---------------------------------------------------------------------------
#  WoS ABBREVIATION -> FULL NAME MAP
#  The Addresses column uses WoS-abbreviated names.  This map provides
#  human-readable full names for the most common abbreviations.
# ---------------------------------------------------------------------------
_WOS_FULL_NAMES = {
    "Univ": "University",
    "Inst": "Institute",
    "Technol": "Technology",
    "Sci": "Science",
    "Res": "Research",
    "Lab": "Laboratory",
    "Ctr": "Center",
    "Coll": "College",
    "Dept": "Department",
    "Fac": "Faculty",
    "Sch": "School",
    "Acad": "Academy",
    "Nat": "National",
    "Politecn": "Polytechnic",
    "Phys": "Physics",
    "Chem": "Chemistry",
    "Mech": "Mechanical",
    "Engn": "Engineering",
    "Med": "Medicine",
    "Biol": "Biology",
    "Mat": "Materials",
    "Prod": "Production",
    "Mfg": "Manufacturing",
    "Appl": "Applied",
    "Dev": "Development",
    "Syst": "System",
    "Environm": "Environmental",
    "Comput": "Computer",
    "Inf": "Information",
    "Telecommun": "Telecommunications",
    "Aerosp": "Aerospace",
    "Automob": "Automobile",
    "Archit": "Architecture",
    "Construct": "Construction",
    "Nanosci": "Nanoscience",
    "Nanotechnol": "Nanotechnology",
}

# ---------------------------------------------------------------------------
#  GENERIC NAME BLACKLIST -- single-word or very generic names that are
#  either truncation artifacts or too ambiguous to be useful as nodes
# ---------------------------------------------------------------------------
_GENERIC_BLACKLIST = {
    "university", "institute", "college", "center", "centre",
    "laboratory", "school", "hospital", "clinic", "foundation",
    "academy", "council", "department", "ministry", "agency",
}

# ---------------------------------------------------------------------------
#  WoS ABBREVIATION CANONICALIZATION
#  Merge common WoS abbreviated forms with their full-name equivalents
#  from the Affiliations column.  Keys are lowercase for case-insensitive
#  matching.
# ---------------------------------------------------------------------------
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
    "swiss fed inst technol": "Swiss Federal Institutes of Technology Domain",
    "texas a&m univ coll stn": "Texas A&M University System",
    "texas a&m university college station": "Texas A&M University System",
    "oak ridge natl lab": "Oak Ridge National Laboratory",
    "nanjing univ aeronaut & astronaut": "Nanjing University of Aeronautics & Astronautics",
    "missouri univ sci & technol": "Missouri University of Science and Technology",
    "missouri university of science &": "Missouri University of Science and Technology",
    "georgia inst technol": "Georgia Institute of Technology",
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

# ---------------------------------------------------------------------------
#  Resolve paths -- data_source/ lives in the main repo root (gitignored,
#  so it is NOT present in worktrees). Walk up from script to find root.
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
_repo_root = SCRIPT_DIR
while not (_repo_root / "data_source").exists() and _repo_root.parent != _repo_root:
    _repo_root = _repo_root.parent
if not (_repo_root / "data_source").exists():
    raise FileNotFoundError("Cannot locate data_source/ -- run from the main repo or a worktree that has access to it")

CONFIG["data_path"] = (_repo_root / "data_source" / "wos_filtered_bibliography.xlsx").resolve()
CONFIG["output_dir"] = (SCRIPT_DIR / CONFIG["output_dir"]).resolve()
CONFIG["plot_dir"] = (SCRIPT_DIR / CONFIG["plot_dir"]).resolve()

CONFIG["output_dir"].mkdir(parents=True, exist_ok=True)
CONFIG["plot_dir"].mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("  INSTITUTIONAL COLLABORATION NETWORK")
print("=" * 70)

# ---------------------------------------------------------------------------
#  1. LOAD DATA
# ---------------------------------------------------------------------------
print("\n[1/7] Loading data ...")
df = pd.read_excel(
    CONFIG["data_path"],
    usecols=["Addresses", "Affiliations", "Publication Year", "UT (Unique WOS ID)"],
)
print(f"  Loaded {len(df):,} records")

# ---------------------------------------------------------------------------
#  2. EXTRACT INSTITUTIONS FROM ADDRESSES COLUMN
# ---------------------------------------------------------------------------
print("\n[2/7] Extracting institutions from Addresses column ...")

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


df["addr_inst"] = df["Addresses"].apply(extract_inst_from_address)

# ---------------------------------------------------------------------------
#  3. SUPPLEMENT WITH AFFILIATIONS (non-truncated entries only)
# ---------------------------------------------------------------------------
print("\n[3/7] Supplementing with Affiliations column (non-truncated only) ...")


def is_truncated(name: str) -> bool:
    return any(name.lower().endswith(s.lower()) for s in _TRUNCATION_SUFFIXES)


def is_generic(name: str) -> bool:
    key = name.lower().strip()
    return key in _GENERIC_BLACKLIST


def canonicalise_inst(name: str) -> str:
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


df["affil_list"] = df["Affiliations"].apply(parse_affiliations_safe)

# Build per-paper institution list: Addresses inst + non-truncated Affiliations
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


df["inst_list"] = df.apply(build_inst_list, axis=1)
df = df[df["inst_list"].str.len() > 0].reset_index(drop=True)
print(f"  Records with institutions: {len(df):,}")

# ---------------------------------------------------------------------------
#  4. COUNT PUBLICATIONS PER INSTITUTION
# ---------------------------------------------------------------------------
print("\n[4/7] Counting publications per institution ...")
pub_counter: collections.Counter = collections.Counter()
for insts in df["inst_list"]:
    for inst in insts:
        pub_counter[inst] += 1

eligible = {inst for inst, c in pub_counter.items() if c >= CONFIG["min_publications"]}
print(f"  Unique institutions (raw): {len(pub_counter):,}")
print(f"  Eligible (>={CONFIG['min_publications']} pubs): {len(eligible):,}")

# ---------------------------------------------------------------------------
#  5. BUILD CO-OCCURRENCE EDGES
# ---------------------------------------------------------------------------
print("\n[5/7] Building co-occurrence edges ...")
edge_counter: collections.Counter = collections.Counter()

for insts in df["inst_list"]:
    filtered = [i for i in insts if i in eligible]
    if len(filtered) < 2:
        continue
    for a, b in itertools.combinations(sorted(filtered), 2):
        edge_counter[(a, b)] += 1

edges = [
    (a, b, w) for (a, b), w in edge_counter.items() if w >= CONFIG["min_edge_weight"]
]
print(f"  Raw edges: {len(edge_counter):,}")
print(f"  Filtered edges (weight >={CONFIG['min_edge_weight']}): {len(edges):,}")

# ---------------------------------------------------------------------------
#  6. BUILD NETWORKX GRAPH + METRICS
# ---------------------------------------------------------------------------
print("\n[6/7] Building graph & computing metrics ...")
G = nx.Graph()
G.add_weighted_edges_from(edges)

for node in G.nodes():
    G.nodes[node]["pub_count"] = pub_counter.get(node, 0)

isolates = list(nx.isolates(G))
G.remove_nodes_from(isolates)
print(f"  Removed {len(isolates)} isolates")

degree_dict = dict(G.degree())
weighted_degree_dict = dict(G.degree(weight="weight"))
betweenness_dict = nx.betweenness_centrality(G, weight="weight", k=min(500, len(G)))
eigenvector_dict = {}
try:
    eigenvector_dict = nx.eigenvector_centrality(G, weight="weight", max_iter=500)
except nx.PowerIterationFailedConvergence:
    print("  Eigenvector centrality did not converge -- skipping")

communities = list(nx.community.greedy_modularity_communities(G))
community_map = {}
for i, comm in enumerate(communities):
    for node in comm:
        community_map[node] = i

clustering_dict = nx.clustering(G)

nodes_data = []
for node in G.nodes():
    nodes_data.append({
        "institution": node,
        "degree": degree_dict.get(node, 0),
        "weighted_degree": weighted_degree_dict.get(node, 0),
        "betweenness": betweenness_dict.get(node, 0),
        "eigenvector": eigenvector_dict.get(node, 0),
        "clustering_coefficient": clustering_dict.get(node, 0),
        "community": community_map.get(node, -1),
        "pub_count": G.nodes[node].get("pub_count", 0),
    })

nodes_df = pd.DataFrame(nodes_data).sort_values("weighted_degree", ascending=False)

edges_df = pd.DataFrame(edges, columns=["source", "target", "weight"]).sort_values(
    "weight", ascending=False
)

n_communities = len(communities)
modularity = nx.community.modularity(G, communities)
density = nx.density(G)
avg_clustering = np.mean(list(clustering_dict.values())) if clustering_dict else 0

metrics_df = pd.DataFrame([{
    "nodes": G.number_of_nodes(),
    "edges": G.number_of_edges(),
    "density": density,
    "avg_clustering": avg_clustering,
    "num_communities": n_communities,
    "modularity": modularity,
    "max_degree": max(degree_dict.values()) if degree_dict else 0,
    "max_weighted_degree": max(weighted_degree_dict.values()) if weighted_degree_dict else 0,
    "top_hub": nodes_df.iloc[0]["institution"] if len(nodes_df) > 0 else "",
    "top_betweenness": nodes_df.sort_values("betweenness", ascending=False).iloc[0]["institution"] if len(nodes_df) > 0 else "",
}])

print(f"  Nodes: {G.number_of_nodes():,}  |  Edges: {G.number_of_edges():,}")
print(f"  Communities: {n_communities}  |  Modularity: {modularity:.4f}")
print(f"  Density: {density:.6f}  |  Avg clustering: {avg_clustering:.4f}")

# ---------------------------------------------------------------------------
#  7. SAVE OUTPUTS
# ---------------------------------------------------------------------------
print("\n[7/7] Saving outputs ...")
nodes_df.to_excel(CONFIG["output_dir"] / "institutional_nodes.xlsx", index=False)
edges_df.to_excel(CONFIG["output_dir"] / "institutional_edges.xlsx", index=False)
metrics_df.to_excel(CONFIG["output_dir"] / "institutional_metrics.xlsx", index=False)
print(f"  Saved to {CONFIG['output_dir']}")

# ---------------------------------------------------------------------------
#  VISUALIZATIONS
# ---------------------------------------------------------------------------
print("\n[7/7] Generating visualizations ...")

# --- Static network plot ---
print("  Static network ...")
pos = nx.spring_layout(
    G, seed=CONFIG["layout_seed"], iterations=CONFIG["layout_iterations"], k=1.5 / np.sqrt(G.number_of_nodes())
)

node_sizes = []
for n in G.nodes():
    wd = weighted_degree_dict.get(n, 1)
    node_sizes.append(np.log1p(wd) * CONFIG["node_size_scale"])

comm_colors = plt.cm.tab20(np.linspace(0, 1, max(n_communities, 1)))
node_colors = [comm_colors[community_map.get(n, 0) % 20] for n in G.nodes()]

edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
max_w = max(edge_weights) if edge_weights else 1
edge_widths = [
    min(np.log1p(w) * CONFIG["edge_width_scale"], CONFIG["max_edge_width"])
    for w in edge_weights
]

fig, ax = plt.subplots(1, 1, figsize=CONFIG["figure_size"])
ax.set_facecolor("#0e1117")
fig.set_facecolor("#0e1117")

for (u, v), width in zip(G.edges(), edge_widths):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    ax.plot([x0, x1], [y0, y1], color="#4cc9f0", linewidth=width, alpha=0.3, zorder=1)

nx.draw_networkx_nodes(
    G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, edgecolors="white", linewidths=0.3, alpha=0.9
)

top_label_nodes = nodes_df.head(CONFIG["top_n_labels"])["institution"].tolist()
label_map = {n: n for n in top_label_nodes if n in pos}
nx.draw_networkx_labels(
    G, {k: pos[k] for k in label_map}, labels=label_map, ax=ax,
    font_size=7, font_color="white", font_weight="bold"
)

ax.set_title("Institutional Collaboration Network\n(Additive Manufacturing -- WoS Publications)", color="white", fontsize=16, fontweight="bold", pad=20)
ax.axis("off")
plt.tight_layout()
fig.savefig(CONFIG["plot_dir"] / "institutional_collaboration_network.png", dpi=CONFIG["figure_dpi"], facecolor=fig.get_facecolor())
plt.close(fig)
print(f"    Saved institutional_collaboration_network.png")

# --- Interactive Plotly HTML ---
print("  Interactive HTML ...")
edge_traces = []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    w = G[u][v]["weight"]
    edge_traces.append(go.Scatter(
        x=[x0, x1, None], y=[y0, y1, None],
        mode="lines",
        line=dict(width=max(np.log1p(w) * 0.5, 0.5), color="#4cc9f0"),
        opacity=min(0.15 + 0.5 * w / max_w, 0.7),
        hoverinfo="skip", showlegend=False,
    ))

x_nodes = [pos[n][0] for n in G.nodes()]
y_nodes = [pos[n][1] for n in G.nodes()]
hover_text = [
    f"<b>{n}</b><br>Papers: {G.nodes[n].get('pub_count', 0)}<br>Weighted Degree: {weighted_degree_dict.get(n, 0)}<br>Community: {community_map.get(n, 0)}<br>Betweenness: {betweenness_dict.get(n, 0):.4f}"
    for n in G.nodes()
]

node_trace = go.Scatter(
    x=x_nodes, y=y_nodes, mode="markers+text",
    text=[n if n in top_label_nodes else "" for n in G.nodes()],
    textposition="top center", textfont=dict(size=9, color="white"),
    hoverinfo="text", hovertext=hover_text,
    marker=dict(
        size=[max(np.log1p(weighted_degree_dict.get(n, 1)) * 3, 4) for n in G.nodes()],
        color=[community_map.get(n, 0) for n in G.nodes()],
        colorscale="Turbo", line=dict(width=0.5, color="white"), opacity=0.9,
    ),
    showlegend=False,
)

layout = go.Layout(
    title=dict(text="Institutional Collaboration Network -- Interactive", font=dict(size=18)),
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    hovermode="closest", margin=dict(b=20, l=5, r=5, t=50),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    dragmode="pan",
)

fig_plotly = go.Figure(data=edge_traces + [node_trace], layout=layout)
fig_plotly.write_html(str(CONFIG["plot_dir"] / "institutional_collaboration_network.html"))
print(f"    Saved institutional_collaboration_network.html")

# --- Top-20 hubs bar chart ---
print("  Top-20 hubs bar chart ...")
top20 = nodes_df.head(CONFIG["top_n_bar"])
c_colors = [
    mcolors.to_hex(comm_colors[community_map.get(n, 0) % 20]) for n in top20["institution"]
]

fig2, ax2 = plt.subplots(figsize=(12, 8))
fig2.set_facecolor("#0e1117")
ax2.set_facecolor("#0e1117")
ax2.barh(range(len(top20)), top20["weighted_degree"].values, color=c_colors[::-1], edgecolor="white", linewidth=0.3)
ax2.set_yticks(range(len(top20)))
ax2.set_yticklabels(top20["institution"].values[::-1] if len(top20) > 1 else top20["institution"].values, fontsize=9, color="white")
ax2.invert_yaxis()
ax2.set_xlabel("Weighted Degree (co-occurrence strength)", color="white", fontsize=11)
ax2.set_title("Top 20 Institutional Hubs by Collaborative Weight", color="white", fontsize=14, fontweight="bold")
ax2.tick_params(colors="white")
for spine in ax2.spines.values():
    spine.set_color("#333")
plt.tight_layout()
fig2.savefig(CONFIG["plot_dir"] / "institutional_top20_hubs.png", dpi=CONFIG["figure_dpi"], facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f"    Saved institutional_top20_hubs.png")

# --- Top-20 betweenness bar chart ---
print("  Top-20 betweenness bar chart ...")
top20_bt = nodes_df.sort_values("betweenness", ascending=False).head(CONFIG["top_n_bar"])
c_colors_bt = [
    mcolors.to_hex(comm_colors[community_map.get(n, 0) % 20]) for n in top20_bt["institution"]
]

fig3, ax3 = plt.subplots(figsize=(12, 8))
fig3.set_facecolor("#0e1117")
ax3.set_facecolor("#0e1117")
ax3.barh(range(len(top20_bt)), top20_bt["betweenness"].values, color=c_colors_bt[::-1], edgecolor="white", linewidth=0.3)
ax3.set_yticks(range(len(top20_bt)))
ax3.set_yticklabels(top20_bt["institution"].values[::-1] if len(top20_bt) > 1 else top20_bt["institution"].values, fontsize=9, color="white")
ax3.invert_yaxis()
ax3.set_xlabel("Betweenness Centrality", color="white", fontsize=11)
ax3.set_title("Top 20 Institutional Brokers by Betweenness Centrality", color="white", fontsize=14, fontweight="bold")
ax3.tick_params(colors="white")
for spine in ax3.spines.values():
    spine.set_color("#333")
plt.tight_layout()
fig3.savefig(CONFIG["plot_dir"] / "institutional_top20_betweenness.png", dpi=CONFIG["figure_dpi"], facecolor=fig3.get_facecolor())
plt.close(fig3)
print(f"    Saved institutional_top20_betweenness.png")

print("\n" + "=" * 70)
print("  INSTITUTIONAL COLLABORATION NETWORK -- COMPLETE")
print("=" * 70)
