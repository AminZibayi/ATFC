# Database & Pipeline Issues Log

## Issue 1: WoS 72-Character Cell Truncation

**Severity:** HIGH  
**Affected columns:** `Affiliations`, `Funding Orgs`, `Funding Text`, `Author Keywords`  
**Root cause:** The WoS Excel export applied a 72-character cell limit on these columns. Any value exceeding 72 chars is cut off mid-word at the cell boundary.  
**Evidence:** Max length of every affected column is exactly 72 characters. The `Addresses` column (max 1,083) and `Abstract` column (max 3,608) are NOT truncated.

**Impact on analyses:**
- ~16,353 records in `Affiliations` have truncated institution names (e.g., "University of" instead of "University of California Berkeley")
- ~12,560 records in `Funding Orgs` have truncated funder names (e.g., "National Natural" instead of "National Natural Science Foundation of China")
- Truncated fragments appear as top-10 hubs in the institutional network ("University of" ranked #1 with 316 degree) and funding network

**Fix applied (Phase 1 - 01_extract_data.py):** Switched from `Affiliations` to `Addresses` column for institution extraction. The `Addresses` column is NOT truncated and contains WoS-abbreviated institution names (e.g., "Georgia Inst Technol") that are complete, just abbreviated per WoS convention. A regex extracts the institution name as the first comma-delimited field after the `[Authors]` bracket. **Effectiveness:** Eliminates all truncated fragments. Institution names are complete but abbreviated (WoS style). The `Affiliations` column is used as a SUPPLEMENT — its non-truncated entries help recover full names, and truncated entries (ending in prepositions/articles) are detected and discarded.

**Fix applied (Phase 1 - 01_extract_data.py, funding):** Cannot use `Addresses` for funding (no equivalent column). Instead: (a) strip grant numbers with regex, (b) detect and discard truncated fragments using a suffix heuristic (entries ending in " of", " for", " National", etc.), (c) canonicalize abbreviation pairs. **Effectiveness:** Moderate — eliminates the most common fragments but some truncated orgs that happen to end at a natural-looking word boundary may survive. The canonicalization map handles ~100 major abbreviation groups. Remaining fragments below `min_publications` threshold are naturally filtered out.

**Fix applied (Phase 1 - 01_extract_data.py, journals):** `Source Title` column is NOT affected by the 72-char truncation (journal names are typically short). No fix needed.

---

## Issue 2: Affiliations Contains Duplicate / Fragment Entries

**Severity:** MEDIUM  
**Root cause:** The `Affiliations` column lists parent+child orgs (e.g., "University System of Georgia; Georgia Institute of Technology") and sometimes repeats the same org multiple times on one paper.
**Examples:** "University College Dublin; University College Dublin; University College"
**Fix:** Within-paper deduplication (set) applied in Phase 1 (01_extract_data.py). Parent-child relationships are kept as-is (they represent real hierarchical affiliations).

---

## Issue 3: Funding Orgs — Abbreviation vs Full Name Proliferation

**Severity:** MEDIUM  
**Root cause:** WoS records the same funder under multiple textual variants: abbreviation only ("NSF"), full name ("National Science Foundation"), and full name with abbreviation ("National Science Foundation (NSF)").
**Fix:** Moderate canonicalization map (~100 groups) that normalises the most common abbreviation variants to a single canonical form. The map is saved to `01_funding_canonicalization_map.csv` (Phase 1) and `funding_canonicalization_map.xlsx` (Phase 2) for audit. **Effectiveness:** Handles the top funders well. Less common variants remain as separate nodes, which is acceptable.

---

## Issue 4: Funding Orgs — Fragment / Truncated Non-Org Entries

**Severity:** MEDIUM  
**Root cause:** The 72-char truncation creates entries like "National", "Natural Science", "Fundamental", "Key", "Science" that are not real organization names.
**Fix:** Fragment blacklist filtering — entries with <=2 words that match a blacklist of common fragments are dropped. Additionally, the truncation-detection heuristic (entries ending in " of", " for", etc.) catches longer truncated forms. Applied in Phase 1 (01_extract_data.py). **Effectiveness:** Good for obvious fragments. Some edge cases (e.g., "Projekt DEAL" which is a real org but looks like a fragment) are handled by explicit whitelist entries in the canonicalization map.

---

## Issue 5: Journal Name Variants

**Severity:** LOW  
**Root cause:** ~47 duplicate journal name pairs exist in `Source Title`: case variants (uppercase vs mixed-case), `&` vs `AND`, hyphen vs space.
**Fix:** Normalisation to uppercase + `&` -> `AND` replacement + known duplicate map in `_JOURNAL_DUPLICATES`. Applied in Phase 1 (01_extract_data.py). **Effectiveness:** Good — collapses the 6 case-variant pairs and ~21 abbreviation collisions. Some genuine journal name changes over time (e.g., Applied Catalysis B renamed) are intentionally kept separate.

---

## Issue 6: Journal Network — Low Modularity (Dense Graph)

**Severity:** INFO (expected behavior)  
**Root cause:** The journal relationship network (edges = shared institutional affiliations) is extremely dense because additive manufacturing is a single field — most institutions publish across the same core journals, creating a near-complete graph.
**Observation:** With min_edge_weight=5, modularity=0.033 and only 3 communities. Raising min_edge_weight to 20 still yields modularity=0.033. The network is fundamentally dense.
**Mitigation:** This is a feature, not a bug — it shows that AM is a cohesive field. For community structure, the institutional collaboration network (modularity=0.708) is more informative. The journal network is best interpreted via centrality metrics (which journals are bridges vs peripherals) rather than community structure.

---

## Issue 7: Eigenvector Centrality Convergence Failure

**Severity:** LOW  
**Root cause:** NetworkX eigenvector centrality fails to converge on some graphs, likely due to structural properties (disconnected components or near-disconnected subgraphs).
**Fix:** Try/except block with fallback to skip eigenvector. Applied in Phase 2 (02_build_networks.py). Betweenness centrality (which always converges) is available as an alternative importance measure.

---

## Issue 8: Windows Console Unicode Encoding

**Severity:** LOW (cosmetic)  
**Root cause:** Windows cp1252 console cannot display Unicode characters like >= (U+2265) and -> (U+2192).
**Fix:** Replaced all Unicode symbols with ASCII equivalents (>= instead of >=, -> instead of ->) in all pipeline scripts.
