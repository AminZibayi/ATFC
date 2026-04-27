"""
=============================================================================
 Journal Relationship Network
=============================================================================
 Builds a journal network where nodes = journals (from Source Title) and
 edges = shared institutional affiliations (same institution publishes in
 both journals).  Edge weight = number of shared institutions.

 Journal names are normalised: uppercase, & ↔ AND, known duplicates
 collapsed.  Each journal is labelled with its primary WoS research area.

 Outputs  -> outputs/bibliometric_networks/journal_*.xlsx
 Plots    -> plots/bibliometric_networks/journal_*.png/.html
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
#  CONFIGURABLE PARAMETERS
# ---------------------------------------------------------------------------
CONFIG = {
    "data_path": Path("../../data_source/wos_filtered_bibliography.xlsx"),
    "output_dir": Path("../../outputs/bibliometric_networks"),
    "plot_dir": Path("../../plots/bibliometric_networks"),

    "min_publications": 50,
    "min_edge_weight": 20,
    "top_n_labels": 30,
    "top_n_bar": 30,

    "layout_seed": 42,
    "layout_iterations": 150,
    "figure_dpi": 200,
    "figure_size": (22, 18),
    "node_size_scale": 15,
    "edge_width_scale": 0.3,
    "max_edge_width": 5,
}

# ---------------------------------------------------------------------------
#  JOURNAL NAME DUPLICATES  (normalise these)
#  Keys are the variant form (uppercased), values are the canonical form.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
#  Resolve paths -- data_source/ lives in the main repo root (gitignored,
#  so it is NOT present in worktrees).  Walk up from script to find root.
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
print("  JOURNAL RELATIONSHIP NETWORK")
print("=" * 70)

# ---------------------------------------------------------------------------
#  1. LOAD DATA
# ---------------------------------------------------------------------------
print("\n[1/8] Loading data ...")
df = pd.read_excel(
    CONFIG["data_path"],
    usecols=["Source Title", "Addresses", "Affiliations", "Publication Year", "WoS Categories", "UT (Unique WOS ID)"],
)
print(f"  Loaded {len(df):,} records")

# ---------------------------------------------------------------------------
# 2. NORMALISE JOURNAL NAMES
# ---------------------------------------------------------------------------
print("\n[2/8] Normalising journal names ...")


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
df = df[df["journal"] != ""].reset_index(drop=True)

# ---------------------------------------------------------------------------
# 3. EXTRACT INSTITUTIONS (Addresses + non-truncated Affiliations)
# ---------------------------------------------------------------------------
print("\n[3/8] Extracting institutions ...")

_ADDR_INST_RE = re.compile(r"\[.*?\]\s*(.+?)(?:,|$)")

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
    return any(name.lower().endswith(t.lower()) for t in _TRUNCATION_SUFFIXES)


def is_generic(name: str) -> bool:
    return name.lower().strip() in _GENERIC_BLACKLIST


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


df["addr_inst"] = df["Addresses"].apply(extract_inst_from_address)
df["affil_list"] = df["Affiliations"].apply(parse_affiliations_safe)


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
print(f"  Records with journal + institutions: {len(df):,}")

# ---------------------------------------------------------------------------
#  4. BUILD INSTITUTION->JOURNALS INVERTED INDEX
# ---------------------------------------------------------------------------
print("\n[4/8] Building institution->journals inverted index ...")
inst_journals: collections.defaultdict = collections.defaultdict(set)
journal_pub_counter: collections.Counter = collections.Counter()

for _, row in df.iterrows():
    journal = row["journal"]
    journal_pub_counter[journal] += 1
    for inst in row["inst_list"]:
        inst_journals[inst].add(journal)

eligible_journals = {j for j, c in journal_pub_counter.items() if c >= CONFIG["min_publications"]}
print(f"  Unique journals (raw): {len(journal_pub_counter):,}")
print(f"  Eligible (>={CONFIG['min_publications']} pubs): {len(eligible_journals):,}")

# ---------------------------------------------------------------------------
#  5. BUILD JOURNAL-JOURNAL EDGES FROM SHARED INSTITUTIONS
# ---------------------------------------------------------------------------
print("\n[5/8] Building journal-journal edges (shared institutions) ...")
edge_counter: collections.Counter = collections.Counter()

for inst, journals in inst_journals.items():
    filtered = [j for j in journals if j in eligible_journals]
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
#  6. BUILD GRAPH + METRICS
# ---------------------------------------------------------------------------
print("\n[6/8] Building graph & computing metrics ...")
G = nx.Graph()
G.add_weighted_edges_from(edges)

for node in G.nodes():
    G.nodes[node]["pub_count"] = journal_pub_counter.get(node, 0)

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

# --- Assign primary research area per journal ---
print("  Assigning research areas ...")
journal_area_counter: collections.defaultdict = collections.defaultdict(collections.Counter)
for _, row in df.iterrows():
    j = row["journal"]
    if j not in G.nodes():
        continue
    if pd.notna(row["WoS Categories"]):
        cats = [c.strip() for c in str(row["WoS Categories"]).split(";") if c.strip()]
        for cat in cats:
            journal_area_counter[j][cat] += 1

primary_area = {}
for j, area_counts in journal_area_counter.items():
    if area_counts:
        primary_area[j] = area_counts.most_common(1)[0][0]
    else:
        primary_area[j] = "Unclassified"

for node in G.nodes():
    if node not in primary_area:
        primary_area[node] = "Unclassified"

nodes_data = []
for node in G.nodes():
    nodes_data.append({
        "journal": node,
        "degree": degree_dict.get(node, 0),
        "weighted_degree": weighted_degree_dict.get(node, 0),
        "betweenness": betweenness_dict.get(node, 0),
        "eigenvector": eigenvector_dict.get(node, 0),
        "clustering_coefficient": clustering_dict.get(node, 0),
        "community": community_map.get(node, -1),
        "pub_count": G.nodes[node].get("pub_count", 0),
        "primary_research_area": primary_area.get(node, "Unclassified"),
    })

nodes_df = pd.DataFrame(nodes_data).sort_values("weighted_degree", ascending=False)
edges_df = pd.DataFrame(edges, columns=["source", "target", "weight"]).sort_values("weight", ascending=False)

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
    "top_hub": nodes_df.iloc[0]["journal"] if len(nodes_df) > 0 else "",
    "top_betweenness": nodes_df.sort_values("betweenness", ascending=False).iloc[0]["journal"] if len(nodes_df) > 0 else "",
}])

print(f"  Nodes: {G.number_of_nodes():,}  |  Edges: {G.number_of_edges():,}")
print(f"  Communities: {n_communities}  |  Modularity: {modularity:.4f}")

# ---------------------------------------------------------------------------
#  7. SAVE OUTPUTS
# ---------------------------------------------------------------------------
print("\n[7/8] Saving outputs ...")
nodes_df.to_excel(CONFIG["output_dir"] / "journal_nodes.xlsx", index=False)
edges_df.to_excel(CONFIG["output_dir"] / "journal_edges.xlsx", index=False)
metrics_df.to_excel(CONFIG["output_dir"] / "journal_metrics.xlsx", index=False)
print(f"  Saved to {CONFIG['output_dir']}")

# ---------------------------------------------------------------------------
#  8. VISUALISATIONS
# ---------------------------------------------------------------------------
print("\n[8/8] Generating visualizations ...")

# Build research area colour map
all_areas = sorted(set(primary_area.values()))
area_cmap = plt.cm.Set3(np.linspace(0, 1, max(len(all_areas), 1)))
area_color_map = {area: area_cmap[i % len(area_cmap)] for i, area in enumerate(all_areas)}

# --- 8a. Static network ---
print("  8a. Static network ...")
pos = nx.spring_layout(
    G, seed=CONFIG["layout_seed"], iterations=CONFIG["layout_iterations"],
    k=1.5 / np.sqrt(G.number_of_nodes()) if G.number_of_nodes() > 0 else 1,
)

node_sizes = [
    np.log1p(G.nodes[n].get("pub_count", 1)) * CONFIG["node_size_scale"]
    for n in G.nodes()
]
node_colors = [area_color_map.get(primary_area.get(n, "Unclassified"), (0.7, 0.7, 0.7, 1.0)) for n in G.nodes()]

edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
max_w = max(edge_weights) if edge_weights else 1
edge_widths = [min(np.log1p(w) * CONFIG["edge_width_scale"], CONFIG["max_edge_width"]) for w in edge_weights]

fig, ax = plt.subplots(figsize=CONFIG["figure_size"])
ax.set_facecolor("#0e1117")
fig.set_facecolor("#0e1117")

for (u, v), width in zip(G.edges(), edge_widths):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    ax.plot([x0, x1], [y0, y1], color="#4361ee", linewidth=width, alpha=0.25, zorder=1)

nx.draw_networkx_nodes(
    G, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
    edgecolors="white", linewidths=0.3, alpha=0.9,
)

top_label_nodes = nodes_df.head(CONFIG["top_n_labels"])["journal"].tolist()
label_map = {n: n for n in top_label_nodes if n in pos}
nx.draw_networkx_labels(
    G, {k: pos[k] for k in label_map}, labels=label_map, ax=ax,
    font_size=6, font_color="white", font_weight="bold",
)

ax.set_title("Journal Relationship Network (Shared Institutional Affiliations)\n(Additive Manufacturing -- WoS Publications)", color="white", fontsize=16, fontweight="bold", pad=20)
ax.axis("off")

legend_handles = []
for area, color in list(area_color_map.items())[:15]:
    legend_handles.append(plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=area[:40]))
ax.legend(handles=legend_handles, loc="lower left", fontsize=7, facecolor="#1a1a2e", edgecolor="#333", labelcolor="white", title="Research Area", title_fontsize=8)

plt.tight_layout()
fig.savefig(CONFIG["plot_dir"] / "journal_relationship_network.png", dpi=CONFIG["figure_dpi"], facecolor=fig.get_facecolor())
plt.close(fig)
print(f"    Saved {CONFIG['plot_dir'] / 'journal_relationship_network.png'}")

# --- 8b. Interactive Plotly ---
print("  8b. Interactive HTML ...")
edge_traces = []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    w = G[u][v]["weight"]
    edge_traces.append(go.Scatter(
        x=[x0, x1, None], y=[y0, y1, None],
        mode="lines",
        line=dict(width=max(np.log1p(w) * 0.3, 0.5), color="#4361ee"),
        opacity=min(0.15 + 0.5 * w / max_w, 0.7),
        hoverinfo="skip", showlegend=False,
    ))

x_nodes = [pos[n][0] for n in G.nodes()]
y_nodes = [pos[n][1] for n in G.nodes()]
hover_text = [
    f"<b>{n}</b><br>Papers: {G.nodes[n].get('pub_count', 0)}<br>Weighted Degree: {weighted_degree_dict.get(n, 0)}<br>Area: {primary_area.get(n, '')}<br>Community: {community_map.get(n, 0)}"
    for n in G.nodes()
]

area_names = sorted(set(primary_area.values()))
area_idx = {a: i for i, a in enumerate(area_names)}
n_areas = max(len(area_names), 1)

area_rgba_list = [mcolors.to_hex(area_color_map.get(a, (0.7, 0.7, 0.7, 1.0))) for a in area_names]
plotly_colorscale = [[i / max(n_areas - 1, 1), c] for i, c in enumerate(area_rgba_list)]

node_colors_plotly = [area_idx.get(primary_area.get(n, ""), 0) for n in G.nodes()]

node_trace = go.Scatter(
    x=x_nodes, y=y_nodes, mode="markers+text",
    text=[n if n in top_label_nodes else "" for n in G.nodes()],
    textposition="top center", textfont=dict(size=9, color="white"),
    hoverinfo="text", hovertext=hover_text,
    marker=dict(
        size=[max(np.log1p(G.nodes[n].get("pub_count", 1)) * 1.5, 4) for n in G.nodes()],
        color=[area_rgba_list[area_idx.get(primary_area.get(n, ""), 0)] for n in G.nodes()],
        line=dict(width=0.5, color="white"), opacity=0.9,
    ),
    showlegend=False,
)

layout = go.Layout(
    title=dict(text="Journal Relationship Network -- Interactive", font=dict(size=18)),
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    hovermode="closest", margin=dict(b=20, l=5, r=5, t=50),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    dragmode="pan",
)

fig_p = go.Figure(data=edge_traces + [node_trace], layout=layout)
fig_p.write_html(str(CONFIG["plot_dir"] / "journal_relationship_network.html"))
print(f"    Saved {CONFIG['plot_dir'] / 'journal_relationship_network.html'}")

# --- 8c. Top-30 journals bar chart ---
print("  8c. Top-30 journals bar chart ...")
top30 = nodes_df.sort_values("pub_count", ascending=False).head(CONFIG["top_n_bar"])
bar_colors = [mcolors.to_hex(area_color_map.get(primary_area.get(n, ""), (0.7, 0.7, 0.7, 1.0))) for n in top30["journal"]]

fig2, ax2 = plt.subplots(figsize=(14, 12))
fig2.set_facecolor("#0e1117")
ax2.set_facecolor("#0e1117")
ax2.barh(range(len(top30)), top30["pub_count"].values, color=bar_colors[::-1], edgecolor="white", linewidth=0.3)
ax2.set_yticks(range(len(top30)))
labels = [f"{j}  [{primary_area.get(j, '')[:30]}]" for j in top30["journal"].values]
ax2.set_yticklabels(labels[::-1] if len(top30) > 1 else labels, fontsize=8, color="white")
ax2.invert_yaxis()
ax2.set_xlabel("Number of Publications", color="white", fontsize=11)
ax2.set_title("Top 30 Journals by Publication Count (colored by Research Area)", color="white", fontsize=14, fontweight="bold")
ax2.tick_params(colors="white")
for spine in ax2.spines.values():
    spine.set_color("#333")
plt.tight_layout()
fig2.savefig(CONFIG["plot_dir"] / "journal_top30_journals.png", dpi=CONFIG["figure_dpi"], facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f"    Saved {CONFIG['plot_dir'] / 'journal_top30_journals.png'}")

print("\n" + "=" * 70)
print("  JOURNAL RELATIONSHIP NETWORK -- COMPLETE")
print("=" * 70)
