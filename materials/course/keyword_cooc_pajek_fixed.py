#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    import networkx as nx  # optional, for GraphML/GEXF export with attributes
except Exception:  # pragma: no cover
    nx = None


# Always read/write relative to the script folder (NOT the terminal's current folder)
BASE_DIR = Path(__file__).resolve().parent


# -----------------------------
# Normalization utilities
# -----------------------------
_WS_RE = re.compile(r"\s+")
_SPLIT_RE = re.compile(r"\s*;\s*|\s*\|\s*|\s*,\s*(?![^()]*\))")


def normalize_keyword(s: str) -> str:
    s = str(s).strip().lower()
    s = _WS_RE.sub(" ", s)
    return s


def split_keywords(cell: object) -> List[str]:
    if cell is None:
        return []
    cell = str(cell).strip()
    if not cell or cell.lower() == "nan":
        return []
    parts = _SPLIT_RE.split(cell)
    cleaned = [normalize_keyword(p) for p in parts if normalize_keyword(p)]
    # de-duplicate per document
    seen = set()
    out: List[str] = []
    for k in cleaned:
        if k not in seen:
            out.append(k)
            seen.add(k)
    return out


# -----------------------------
# Tech term list parsing
# -----------------------------
@dataclass(frozen=True)
class TechMatch:
    canonical: str
    category: str


def parse_tech_terms_txt(path: Path) -> Dict[str, TechMatch]:
    alias_map: Dict[str, TechMatch] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" not in line:
                continue
            left, right = line.split("\t", 1)
            category = normalize_keyword(right) or "unknown"

            aliases = [a.strip() for a in left.split(",") if a.strip()]
            if not aliases:
                continue
            canonical = normalize_keyword(aliases[0])

            for a in aliases:
                alias = normalize_keyword(a)
                if alias and alias not in alias_map:
                    alias_map[alias] = TechMatch(canonical=canonical, category=category)
    return alias_map


# -----------------------------
# WoS keyword extraction
# -----------------------------
def guess_keyword_column(df: pd.DataFrame, preferred: Optional[str] = None) -> str:
    if preferred and preferred in df.columns:
        return preferred

    candidates = [
        "Author Keywords", "DE", "ID", "Keywords", "Keyword",
        "keywords", "author keywords", "DE (Author Keywords)", "Keywords Plus",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if "keyword" in str(c).lower():
            return c

    raise ValueError(
        "Could not find a keyword column automatically. "
        "Use --keyword-col with the correct column name."
    )


def iter_documents_keywords(df: pd.DataFrame, keyword_col: str) -> Iterable[List[str]]:
    for _, row in df.iterrows():
        kws = split_keywords(row.get(keyword_col, ""))
        if kws:
            yield kws


# -----------------------------
# Co-occurrence computation
# -----------------------------
def build_cooccurrence(docs: Iterable[List[str]]) -> Tuple[Counter, Counter]:
    node_freq: Counter = Counter()
    edge_w: Counter = Counter()

    for kws in docs:
        unique = list(dict.fromkeys(kws))
        for k in unique:
            node_freq[k] += 1
        for a, b in itertools.combinations(sorted(unique), 2):
            edge_w[(a, b)] += 1

    return node_freq, edge_w


# -----------------------------
# Excel loader (robust to multi-sheet dict)
# -----------------------------
def load_excel_as_df(xlsx_path: Path, sheet: Optional[str]) -> pd.DataFrame:
    df_obj = pd.read_excel(xlsx_path, sheet_name=sheet)
    if isinstance(df_obj, dict):
        if sheet is not None:
            available = list(df_obj.keys())
            raise ValueError(f"Sheet '{sheet}' not found. Available sheets: {available}")
        if not df_obj:
            raise ValueError("Excel file contains no sheets.")
        first_sheet = next(iter(df_obj.keys()))
        print(f"[INFO] Multiple sheets detected. Using first sheet: {first_sheet}")
        return df_obj[first_sheet]
    return df_obj


# -----------------------------
# Pajek .net writer (labels only)
# -----------------------------
def pajek_escape_label(label: str) -> str:
    return label.replace('"', "'")


def write_pajek_net(out_path: Path, nodes: List[Dict], edges: List[Tuple[int, int, int]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"*Vertices {len(nodes)}\n")
        for n in nodes:
            f.write(f'{n["id"]} "{pajek_escape_label(n["keyword"])}"\n')
        f.write("*Edges\n")
        for i, j, w in edges:
            f.write(f"{i} {j} {w}\n")


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Keyword co-occurrence -> Gephi-ready CSV + optional Pajek .net")

    ap.add_argument("--xlsx", type=str, default=str(BASE_DIR / "output_wos_file.xlsx"))
    ap.add_argument("--sheet", type=str, default=None)
    ap.add_argument("--keyword-col", type=str, default=None)
    ap.add_argument("--tech-terms", type=str, default=str(BASE_DIR / "tech_terms.txt"))

    ap.add_argument("--min-doc-freq", type=int, default=2)
    ap.add_argument("--min-edge-weight", type=int, default=2)

    ap.add_argument("--out-nodes", type=str, default=str(BASE_DIR / "nodes.csv"))
    ap.add_argument("--out-edges", type=str, default=str(BASE_DIR / "edges.csv"))
    ap.add_argument("--out-net", type=str, default=str(BASE_DIR / "keyword_cooccurrence.net"))

    ap.add_argument("--out-gexf", type=str, default=str(BASE_DIR / "keyword_cooccurrence.gexf"))
    ap.add_argument("--out-graphml", type=str, default=str(BASE_DIR / "keyword_cooccurrence.graphml"))
    ap.add_argument("--include-categories", action="store_true", help="Add category nodes and tech->category edges so Gephi shows Type=category")
    ap.add_argument("--category-edge-weight", type=str, default="docfreq", choices=["docfreq","one"], help="Weight for tech->category edges")

    args = ap.parse_args()

    xlsx_path = Path(args.xlsx)
    tech_path = Path(args.tech_terms)

    out_nodes = Path(args.out_nodes)
    out_edges = Path(args.out_edges)
    out_net = Path(args.out_net)
    out_gexf = Path(args.out_gexf)
    out_graphml = Path(args.out_graphml)

    print(f"[INFO] Script folder (BASE_DIR): {BASE_DIR}")
    print(f"[INFO] Reading Excel: {xlsx_path.resolve()}")
    print(f"[INFO] Reading Tech terms: {tech_path.resolve()}")
    print(f"[INFO] Writing nodes.csv: {out_nodes.resolve()}")
    print(f"[INFO] Writing edges.csv: {out_edges.resolve()}")
    print(f"[INFO] Writing .net: {out_net.resolve()}")
    print(f"[INFO] Writing .gexf: {out_gexf.resolve()}")
    print(f"[INFO] Writing .graphml: {out_graphml.resolve()}")

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")
    if not tech_path.exists():
        raise FileNotFoundError(f"Tech term file not found: {tech_path}")

    df = load_excel_as_df(xlsx_path, sheet=args.sheet)
    keyword_col = guess_keyword_column(df, preferred=args.keyword_col)
    print(f"[INFO] Keyword column used: {keyword_col}")

    alias_map = parse_tech_terms_txt(tech_path)

    docs_iter = iter_documents_keywords(df, keyword_col)
    node_freq, edge_w = build_cooccurrence(docs_iter)

    kept_nodes = {k for k, dfreq in node_freq.items() if dfreq >= args.min_doc_freq}

    kept_edges: List[Tuple[str, str, int]] = []
    for (a, b), w in edge_w.items():
        if w >= args.min_edge_weight and a in kept_nodes and b in kept_nodes:
            kept_edges.append((a, b, int(w)))

    # Ensure nodes cover all endpoints
    endpoints = set()
    for a, b, _ in kept_edges:
        endpoints.add(a); endpoints.add(b)
    kept_nodes = kept_nodes.intersection(endpoints)

    def annotate(k: str) -> Tuple[str, str, str]:
        m = alias_map.get(k)
        if m:
            return "technology", m.category, m.canonical
        return "other", "other", k

    sorted_nodes = sorted(kept_nodes)
    id_map: Dict[str, int] = {k: i + 1 for i, k in enumerate(sorted_nodes)}

    # Nodes for Gephi
    nodes_gephi: List[Dict] = []
    nodes_internal: List[Dict] = []
    for k in sorted_nodes:
        typ, cat, canonical = annotate(k)
        nodes_internal.append({"id": id_map[k], "keyword": k})
        nodes_gephi.append({
            "Id": id_map[k],
            "Label": k,
            "Type": typ,
            "Category": cat,
            "Canonical": canonical,
            "DocFreq": int(node_freq[k]),
        })

    # Edges for Gephi
    edges_gephi: List[Dict] = []
    pajek_edges: List[Tuple[int, int, int]] = []
    for a, b, w in sorted(kept_edges, key=lambda x: (-x[2], x[0], x[1])):
        if a not in id_map or b not in id_map:
            continue
        i, j = id_map[a], id_map[b]
        edges_gephi.append({"Source": i, "Target": j, "Weight": w, "Type": "Undirected"})
        pajek_edges.append((i, j, w))


    # Optionally add category nodes (so Gephi shows Type=category) and connect tech -> category
    if args.include_categories:
        # Collect categories present among technology nodes
        categories_present = {}
        for row in nodes_gephi:
            if row.get("Type") == "technology":
                cat = row.get("Category") or "unknown"
                categories_present.setdefault(cat, 0)
                categories_present[cat] += 1

        # Allocate new IDs for category nodes
        next_id = max((n["Id"] for n in nodes_gephi), default=0) + 1
        cat_id_map: Dict[str, int] = {}
        for cat in sorted(categories_present.keys()):
            cat_id_map[cat] = next_id
            nodes_gephi.append({
                "Id": next_id,
                "Label": cat,
                "Type": "category",
                "Category": cat,
                "Canonical": cat,
                "DocFreq": int(categories_present[cat]),
            })
            next_id += 1

        # Add tech -> category edges (undirected by default)
        for row in list(nodes_gephi):
            if row.get("Type") != "technology":
                continue
            cat = row.get("Category") or "unknown"
            if cat not in cat_id_map:
                continue
            w = row.get("DocFreq", 1)
            if args.category_edge_weight == "one":
                w = 1
            edges_gephi.append({
                "Source": int(row["Id"]),
                "Target": int(cat_id_map[cat]),
                "Weight": int(w),
                "Type": "Undirected",
                "Relation": "has_category",
            })

    # Write outputs (even if empty)
    out_nodes.parent.mkdir(parents=True, exist_ok=True)
    out_edges.parent.mkdir(parents=True, exist_ok=True)
    out_net.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(nodes_gephi).to_csv(out_nodes, index=False, encoding="utf-8-sig")
    pd.DataFrame(edges_gephi).to_csv(out_edges, index=False, encoding="utf-8-sig")
    write_pajek_net(out_net, [{"id": n["Id"], "keyword": n["Label"]} for n in nodes_gephi], pajek_edges)

    # GraphML / GEXF preserve node attributes in Gephi (unlike Pajek .net)
    if nx is None:
        print("[WARN] networkx not available; skipping .gexf/.graphml export. Install with: pip install networkx")
    else:
        G = nx.Graph()
        for n in nodes_gephi:
            nid = int(n["Id"])
            # store all attributes except Id
            attrs = {k: v for k, v in n.items() if k != "Id"}
            G.add_node(nid, **attrs)
        for e in edges_gephi:
            s = int(e["Source"]); t = int(e["Target"])
            attrs = {k: v for k, v in e.items() if k not in ("Source","Target")}
            # If multiple edges repeat, keep the max weight and merge attrs conservatively
            if G.has_edge(s, t):
                existing = G[s][t]
                existing["Weight"] = max(int(existing.get("Weight", 1)), int(attrs.get("Weight", 1)))
            else:
                G.add_edge(s, t, **attrs)

        out_gexf.parent.mkdir(parents=True, exist_ok=True)
        out_graphml.parent.mkdir(parents=True, exist_ok=True)
        try:
            nx.write_gexf(G, out_gexf)
            print(f"[INFO] Wrote GEXF: {out_gexf.resolve()}")
        except Exception as ex:
            print(f"[WARN] Failed to write GEXF: {ex}")
        try:
            nx.write_graphml(G, out_graphml)
            print(f"[INFO] Wrote GraphML: {out_graphml.resolve()}")
        except Exception as ex:
            print(f"[WARN] Failed to write GraphML: {ex}")

    print("[INFO] Done.")
    print(f"[INFO] Nodes kept: {len(nodes_gephi)}")
    print(f"[INFO] Edges kept: {len(edges_gephi)}")


if __name__ == "__main__":
    main()
