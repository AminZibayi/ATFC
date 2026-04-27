"""
=============================================================================
 Funding Organization Network
=============================================================================
 Builds a co-funding network where nodes = funding organisations (from the
 Funding Orgs column) and edges = co-funding the same paper.  Edge weight =
 number of co-funded papers.

 Includes moderate normalisation: grant-number stripping, abbreviation
 canonicalisation (~25 groups), and fragment removal.

 Outputs  -> outputs/bibliometric_networks/funding_*.xlsx
 Plots    -> plots/bibliometric_networks/funding_*.png/.html
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

    "min_publications": 10,
    "min_edge_weight": 3,
    "top_n_labels": 30,
    "top_n_bar": 20,

    "layout_seed": 42,
    "layout_iterations": 150,
    "figure_dpi": 200,
    "figure_size": (22, 18),
    "node_size_scale": 60,
    "edge_width_scale": 0.6,
    "max_edge_width": 6,
}

# ---------------------------------------------------------------------------
#  CANONICALISATION MAP  (moderate -- abbreviations -> full name)
#  Keys are lowercased for case-insensitive matching.
# ---------------------------------------------------------------------------
_CANONICAL = {
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

# ---------------------------------------------------------------------------
#  FRAGMENT BLACKLIST  -- org names that are clearly truncated / not real orgs
# ---------------------------------------------------------------------------
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

_TRUNCATION_SUFFIXES = (
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
print("  FUNDING ORGANIZATION NETWORK")
print("=" * 70)

# ---------------------------------------------------------------------------
#  1. LOAD DATA
# ---------------------------------------------------------------------------
print("\n[1/8] Loading data ...")
df = pd.read_excel(
    CONFIG["data_path"],
    usecols=["Funding Orgs", "Publication Year", "UT (Unique WOS ID)"],
)
print(f"  Loaded {len(df):,} records")

# ---------------------------------------------------------------------------
#  2. PARSE & NORMALISE FUNDING ORGS
# ---------------------------------------------------------------------------
print("\n[2/8] Parsing & normalising funding orgs ...")
canonicalisation_log: dict[str, str] = {}


def clean_funding_org(raw: str) -> str | None:
    if pd.isna(raw):
        return None
    s = str(raw).strip().rstrip(";").strip()
    s = _GRANT_RE.sub("", s).strip()
    if not s:
        return None
    key = s.lower().strip()
    if key in _CANONICAL:
        canonical = _CANONICAL[key]
        if s != canonical:
            canonicalisation_log[s] = canonical
        return canonical
    if key in _FRAGMENT_BLACKLIST:
        return None
    if len(s.split()) == 1 and key not in _KNOWN_SINGLE_WORD_ABBREVS:
        return None
    if any(s.lower().endswith(t.lower()) for t in _TRUNCATION_SUFFIXES):
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
df = df[df["funder_list"].str.len() > 0].reset_index(drop=True)
print(f"  Records with funding: {len(df):,}")
print(f"  Canonicalisation mappings: {len(canonicalisation_log):,}")

# ---------------------------------------------------------------------------
#  3. COUNT PUBLICATIONS PER FUNDER
# ---------------------------------------------------------------------------
print("\n[3/8] Counting publications per funder ...")
pub_counter: collections.Counter = collections.Counter()
for funders in df["funder_list"]:
    for f in funders:
        pub_counter[f] += 1

eligible = {f for f, c in pub_counter.items() if c >= CONFIG["min_publications"]}
print(f"  Unique funders (raw): {len(pub_counter):,}")
print(f"  Eligible (>={CONFIG['min_publications']} pubs): {len(eligible):,}")

# ---------------------------------------------------------------------------
#  4. BUILD CO-FUNDING EDGES
# ---------------------------------------------------------------------------
print("\n[4/8] Building co-funding edges ...")
edge_counter: collections.Counter = collections.Counter()

for funders in df["funder_list"]:
    filtered = [f for f in funders if f in eligible]
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
#  5. BUILD GRAPH + METRICS
# ---------------------------------------------------------------------------
print("\n[5/8] Building graph & computing metrics ...")
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
        "funding_org": node,
        "degree": degree_dict.get(node, 0),
        "weighted_degree": weighted_degree_dict.get(node, 0),
        "betweenness": betweenness_dict.get(node, 0),
        "eigenvector": eigenvector_dict.get(node, 0),
        "clustering_coefficient": clustering_dict.get(node, 0),
        "community": community_map.get(node, -1),
        "pub_count": G.nodes[node].get("pub_count", 0),
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
    "top_hub": nodes_df.iloc[0]["funding_org"] if len(nodes_df) > 0 else "",
    "top_betweenness": nodes_df.sort_values("betweenness", ascending=False).iloc[0]["funding_org"] if len(nodes_df) > 0 else "",
}])

print(f"  Nodes: {G.number_of_nodes():,}  |  Edges: {G.number_of_edges():,}")
print(f"  Communities: {n_communities}  |  Modularity: {modularity:.4f}")

# ---------------------------------------------------------------------------
#  6. SAVE OUTPUTS
# ---------------------------------------------------------------------------
print("\n[6/8] Saving outputs ...")
nodes_df.to_excel(CONFIG["output_dir"] / "funding_nodes.xlsx", index=False)
edges_df.to_excel(CONFIG["output_dir"] / "funding_edges.xlsx", index=False)
metrics_df.to_excel(CONFIG["output_dir"] / "funding_metrics.xlsx", index=False)

if canonicalisation_log:
    canon_df = pd.DataFrame(
        list(canonicalisation_log.items()), columns=["original", "canonical"]
    )
    canon_df.to_excel(CONFIG["output_dir"] / "funding_canonicalization_map.xlsx", index=False)
print(f"  Saved to {CONFIG['output_dir']}")

# ---------------------------------------------------------------------------
#  7. VISUALISATIONS
# ---------------------------------------------------------------------------
print("\n[7/8] Generating visualizations ...")

# --- 7a. Static network ---
print("  7a. Static network ...")
pos = nx.spring_layout(
    G, seed=CONFIG["layout_seed"], iterations=CONFIG["layout_iterations"],
    k=1.5 / np.sqrt(G.number_of_nodes()) if G.number_of_nodes() > 0 else 1,
)

node_sizes = [np.log1p(weighted_degree_dict.get(n, 1)) * CONFIG["node_size_scale"] for n in G.nodes()]
comm_colors = plt.cm.tab20(np.linspace(0, 1, max(n_communities, 1)))
node_colors = [comm_colors[community_map.get(n, 0) % 20] for n in G.nodes()]

edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
max_w = max(edge_weights) if edge_weights else 1
edge_widths = [min(np.log1p(w) * CONFIG["edge_width_scale"], CONFIG["max_edge_width"]) for w in edge_weights]

fig, ax = plt.subplots(figsize=CONFIG["figure_size"])
ax.set_facecolor("#0e1117")
fig.set_facecolor("#0e1117")

for (u, v), width in zip(G.edges(), edge_widths):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    ax.plot([x0, x1], [y0, y1], color="#f72585", linewidth=width, alpha=0.3, zorder=1)

nx.draw_networkx_nodes(
    G, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
    edgecolors="white", linewidths=0.3, alpha=0.9,
)

top_label_nodes = nodes_df.head(CONFIG["top_n_labels"])["funding_org"].tolist()
label_map = {n: n for n in top_label_nodes if n in pos}
nx.draw_networkx_labels(
    G, {k: pos[k] for k in label_map}, labels=label_map, ax=ax,
    font_size=7, font_color="white", font_weight="bold",
)

ax.set_title("Funding Organization Co-Funding Network\n(Additive Manufacturing -- WoS Publications)", color="white", fontsize=16, fontweight="bold", pad=20)
ax.axis("off")
plt.tight_layout()
fig.savefig(CONFIG["plot_dir"] / "funding_co_funding_network.png", dpi=CONFIG["figure_dpi"], facecolor=fig.get_facecolor())
plt.close(fig)
print(f"    Saved {CONFIG['plot_dir'] / 'funding_co_funding_network.png'}")

# --- 7b. Interactive Plotly ---
print("  7b. Interactive HTML ...")
edge_traces = []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    w = G[u][v]["weight"]
    edge_traces.append(go.Scatter(
        x=[x0, x1, None], y=[y0, y1, None],
        mode="lines",
        line=dict(width=max(np.log1p(w) * 0.5, 0.5), color="#f72585"),
        opacity=min(0.15 + 0.5 * w / max_w, 0.7),
        hoverinfo="skip", showlegend=False,
    ))

x_nodes = [pos[n][0] for n in G.nodes()]
y_nodes = [pos[n][1] for n in G.nodes()]
hover_text = [
    f"<b>{n}</b><br>Papers: {G.nodes[n].get('pub_count', 0)}<br>Weighted Degree: {weighted_degree_dict.get(n, 0)}<br>Community: {community_map.get(n, 0)}"
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
    title=dict(text="Funding Organization Co-Funding Network -- Interactive", font=dict(size=18)),
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    hovermode="closest", margin=dict(b=20, l=5, r=5, t=50),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    dragmode="pan",
)

fig_p = go.Figure(data=edge_traces + [node_trace], layout=layout)
fig_p.write_html(str(CONFIG["plot_dir"] / "funding_co_funding_network.html"))
print(f"    Saved {CONFIG['plot_dir'] / 'funding_co_funding_network.html'}")

# --- 7c. Top-20 bar chart ---
print("  7c. Top-20 funders bar chart ...")
top20 = nodes_df.head(CONFIG["top_n_bar"])
c_colors = [mcolors.to_hex(comm_colors[community_map.get(n, 0) % 20]) for n in top20["funding_org"]]

fig2, ax2 = plt.subplots(figsize=(14, 8))
fig2.set_facecolor("#0e1117")
ax2.set_facecolor("#0e1117")
ax2.barh(range(len(top20)), top20["weighted_degree"].values, color=c_colors[::-1], edgecolor="white", linewidth=0.3)
ax2.set_yticks(range(len(top20)))
ax2.set_yticklabels(top20["funding_org"].values[::-1] if len(top20) > 1 else top20["funding_org"].values, fontsize=9, color="white")
ax2.invert_yaxis()
ax2.set_xlabel("Weighted Degree (co-funding strength)", color="white", fontsize=11)
ax2.set_title("Top 20 Funding Organizations by Co-Funding Weight", color="white", fontsize=14, fontweight="bold")
ax2.tick_params(colors="white")
for spine in ax2.spines.values():
    spine.set_color("#333")
plt.tight_layout()
fig2.savefig(CONFIG["plot_dir"] / "funding_top20_funders.png", dpi=CONFIG["figure_dpi"], facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f"    Saved {CONFIG['plot_dir'] / 'funding_top20_funders.png'}")

print("\n" + "=" * 70)
print("  FUNDING ORGANIZATION NETWORK -- COMPLETE")
print("=" * 70)
