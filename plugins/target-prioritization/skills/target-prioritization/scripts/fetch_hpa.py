#!/usr/bin/env python3
"""Human Protein Atlas fetcher: tissue + single-cell + pathology per gene.

Per gene symbol:
  1) Resolve symbol -> Ensembl ID via search_download.php
  2) Fetch /<ENSG>.json and extract tissue, single-cell, pathology fields

Subcellular localization is NOT fetched here — UniProt is the authoritative
source (see scripts/fetch_uniprot.py). Cell-type / disease focus terms live
in scripts/aggregate.py (FOCUS_CELL_TYPES, FOCUS_DISEASE_TERMS).
"""
import argparse
import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

HPA_SEARCH = "https://www.proteinatlas.org/api/search_download.php"
HPA_ENTRY = "https://www.proteinatlas.org/{ensg}.json"


def http_get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def resolve_ensembl(gene: str) -> str | None:
    params = {"search": gene, "format": "json", "columns": "g,eg", "compress": "no"}
    data = http_get_json(f"{HPA_SEARCH}?{urllib.parse.urlencode(params)}")
    if not data:
        return None
    for row in data:
        if row.get("Gene") == gene:
            return row.get("Ensembl")
    return data[0].get("Ensembl") if data else None


def top_n_by_value(d, n: int = 3) -> list[tuple[str, float]]:
    if not isinstance(d, dict):
        return []
    items = []
    for k, v in d.items():
        try:
            items.append((k, float(v)))
        except (TypeError, ValueError):
            continue
    items.sort(key=lambda x: -x[1])
    return items[:n]


def to_float_dict(d) -> dict[str, float]:
    if not isinstance(d, dict):
        return {}
    out = {}
    for k, v in d.items():
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def summarize_pathology(entry: dict) -> dict:
    """Aggregate per-cancer-type 'Cancer prognostics - ...' dicts."""
    prognostic = []
    for k, v in entry.items():
        if not k.startswith("Cancer prognostics - ") or not isinstance(v, dict):
            continue
        if v.get("is_prognostic"):
            prognostic.append({
                "cancer": k.replace("Cancer prognostics - ", ""),
                "type": v.get("prognostic type", ""),
                "p_val": v.get("p_val"),
            })
    return {
        "n_prognostic_cancers": len(prognostic),
        "prognostic_top3": prognostic[:3],
        "rna_cancer_specificity": entry.get("RNA cancer specificity"),
    }


def fetch_one(gene: str) -> dict:
    out = {
        "gene": gene,
        "ensembl_id": None,
        "tissue_specificity_tag": None,
        "tissue_top_types": [],
        "cell_specificity_tag": None,
        "cell_top_types": [],
        "cell_nCPM_full": {},
        "expression_cluster": None,
        "pathology": {},
    }
    ensg = resolve_ensembl(gene)
    if not ensg:
        return out
    out["ensembl_id"] = ensg

    entry = http_get_json(HPA_ENTRY.format(ensg=ensg))
    if not entry:
        return out

    out["tissue_specificity_tag"] = entry.get("RNA tissue specificity")
    out["tissue_top_types"] = top_n_by_value(entry.get("RNA tissue specific nTPM"))
    out["cell_specificity_tag"] = entry.get("RNA single cell type specificity")
    cell_nCPM = entry.get("RNA single cell type specific nCPM")
    out["cell_nCPM_full"] = to_float_dict(cell_nCPM)
    out["cell_top_types"] = top_n_by_value(cell_nCPM)
    out["expression_cluster"] = entry.get("Single cell expression cluster")
    out["pathology"] = summarize_pathology(entry)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True, help="Comma-separated gene symbols")
    ap.add_argument("--output", required=True)
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args()

    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    result = {}
    for i, g in enumerate(genes, 1):
        result[g] = fetch_one(g)
        if i % 10 == 0:
            print(f"  hpa: {i}/{len(genes)}", flush=True)
        time.sleep(args.sleep)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"hpa: wrote {len(result)} entries to {args.output}")


if __name__ == "__main__":
    main()
