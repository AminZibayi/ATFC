import csv
from pathlib import Path

import pandas as pd
from normality import normalize
from rapidfuzz import fuzz, process
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS
from shared_python.paths import get_intermediate_data_path, get_output_path

# Static Blockchain Vocabulary
BLOCKCHAIN_VOCAB = [
    "51% attack",
    "address",
    "blockchain",
    "block",
    "cbdc",
    "deposit tokens",
    "distributed ledger technology",
    "tokenization",
    "smart contracts",
    "web3",
    "cryptocurrency",
    "digital assets",
    "decentralized finance",
    "defi",
    "decentralized autonomous organization",
    "dao",
    "decentralized identity",
    "self-sovereign identity",
    "ssi",
    "verifiable credential",
    "soulbound token",
]


def extract_aio_terms(aio_path: Path):
    print(f"Extracting terms from AIO ({aio_path})...")
    g = Graph()
    g.parse(str(aio_path), format="xml")

    canonical_terms = []

    # Simple extraction of classes and their labels
    # IAO_0000118 is alternative term
    IAO_0000118 = URIRef("http://purl.obolibrary.org/obo/IAO_0000118")

    for s, _p, _o in g.triples(
        (None, RDF.type, URIRef("http://www.w3.org/2002/07/owl#Class"))
    ):
        labels = list(g.objects(s, RDFS.label))
        alt_labels = list(g.objects(s, IAO_0000118))

        if labels:
            canonical_label = str(labels[0])
            term_dict = {"id": str(s), "label": canonical_label, "synonyms": []}
            for alt in alt_labels:
                term_dict["synonyms"].append(str(alt))
            canonical_terms.append(term_dict)

    return canonical_terms


def canonicalize_keywords():
    vocab_dir = get_intermediate_data_path("canonicalization-workflow", "vocabularies")
    aio_path = vocab_dir / "aio.owl"

    aio_terms = []
    if aio_path.exists():
        aio_terms = extract_aio_terms(aio_path)

    master_vocab = {}

    # Add AIO
    for t in aio_terms:
        canon_norm = normalize(t["label"])
        if canon_norm:
            master_vocab[canon_norm] = {"id": t["id"], "label": t["label"]}
        for syn in t["synonyms"]:
            syn_norm = normalize(syn)
            if syn_norm and syn_norm not in master_vocab:
                master_vocab[syn_norm] = {"id": t["id"], "label": t["label"]}

    # Add Blockchain Vocab
    for term in BLOCKCHAIN_VOCAB:
        term_norm = normalize(term)
        if term_norm and term_norm not in master_vocab:
            master_vocab[term_norm] = {
                "id": f"bc_{term_norm.replace(' ', '_')}",
                "label": term,
            }

    # Load keywords
    records_path = (
        get_intermediate_data_path("bibliometric-pipeline", "") / "records.parquet"
    )
    if not records_path.exists():
        raise FileNotFoundError(f"Missing records at {records_path}")

    df = pd.read_parquet(records_path)

    # Extract keywords
    raw_keywords = set()
    for items in df["DE"].dropna():
        for k in items:
            raw_keywords.add(k)

    print(f"Extracted {len(raw_keywords)} raw keywords to canonicalize.")

    mappings = []
    unmapped = []

    canonical_list = list(master_vocab.keys())

    for rw in raw_keywords:
        rw_norm = normalize(rw)
        if not rw_norm:
            continue

        # 1. Exact Match
        if rw_norm in master_vocab:
            mappings.append(
                {
                    "variant": rw,
                    "variant_norm": rw_norm,
                    "canonical_id": master_vocab[rw_norm]["id"],
                    "canonical_label": master_vocab[rw_norm]["label"],
                    "match_type": "exact",
                }
            )
            continue

        # 2. Fuzzy Match
        best_match = process.extractOne(
            rw_norm, canonical_list, scorer=fuzz.token_set_ratio
        )
        if best_match and best_match[1] >= 90:
            canon_key = best_match[0]
            mappings.append(
                {
                    "variant": rw,
                    "variant_norm": rw_norm,
                    "canonical_id": master_vocab[canon_key]["id"],
                    "canonical_label": master_vocab[canon_key]["label"],
                    "match_type": "fuzzy",
                    "score": best_match[1],
                }
            )
        else:
            unmapped.append(rw)

    print(f"Mapped: {len(mappings)}")
    print(f"Unmapped: {len(unmapped)}")

    out_dir = get_output_path("canonicalization-workflow", "")

    # Write Synonyms table
    syn_path = out_dir / "keyword_synonyms.csv"
    with open(syn_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            ["variant", "canonical_id", "canonical_label", "match_type", "score"]
        )
        for m in mappings:
            writer.writerow(
                [
                    m["variant"],
                    m["canonical_id"],
                    m["canonical_label"],
                    m["match_type"],
                    m.get("score", 100),
                ]
            )

    # Write Unmapped / Review
    review_path = out_dir / "manual_review.csv"
    with open(review_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "variant_norm"])
        for u in unmapped:
            writer.writerow([u, normalize(u)])

    print(f"Saved {syn_path}")
    print(f"Saved {review_path}")


def run():
    print("=" * 70)
    print(" CANONICALIZING KEYWORDS")
    print("=" * 70)
    canonicalize_keywords()


if __name__ == "__main__":
    run()
