#!/usr/bin/env python3
"""ChEMBL fetcher: per-gene top tool compounds + best IC50.

Two HTTP calls per gene:
  1) target/search.json?q=<symbol> → pick the human SINGLE PROTEIN target
  2) activity.json?target_chembl_id=<id>&standard_type=IC50&pchembl_value__gte=7
       order_by=-pchembl_value → top 5 most potent compounds

Dossier-only: ChEMBL data does not contribute to the composite score. Its
purpose is to surface concrete tool compounds for downstream experimental
validation (read by Claude when writing the 'Suggested next step' slot).
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"


def http_get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def resolve_target(gene: str) -> dict | None:
    """Pick the best human SINGLE PROTEIN ChEMBL target for a gene symbol."""
    url = f"{CHEMBL}/target/search.json?{urllib.parse.urlencode({'q': gene, 'limit': 10})}"
    data = http_get_json(url)
    if not data:
        return None
    candidates = [
        t for t in (data.get("targets") or [])
        if t.get("organism") == "Homo sapiens" and t.get("target_type") == "SINGLE PROTEIN"
    ]
    if not candidates:
        return None
    # Prefer exact pref_name or synonym match to the gene symbol
    upper = gene.upper()
    for t in candidates:
        syns = " ".join(
            (cs.get("component_synonym") or "")
            for c in (t.get("target_components") or [])
            for cs in (c.get("target_component_synonyms") or [])
        ).upper()
        if upper in syns.split() or t.get("pref_name", "").upper() == upper:
            return t
    return candidates[0]


def fetch_top_compounds(target_id: str, limit: int = 5) -> list[dict]:
    params = {
        "target_chembl_id": target_id,
        "standard_type": "IC50",
        "pchembl_value__gte": 7,
        "limit": limit,
        "order_by": "-pchembl_value",
    }
    data = http_get_json(f"{CHEMBL}/activity.json?{urllib.parse.urlencode(params)}")
    if not data:
        return []
    out = []
    for a in (data.get("activities") or [])[:limit]:
        out.append({
            "chembl_id": a.get("molecule_chembl_id"),
            "pref_name": a.get("molecule_pref_name"),
            "pchembl_value": a.get("pchembl_value"),
            "ic50_nm": a.get("standard_value"),
            "units": a.get("standard_units"),
            "assay_id": a.get("assay_chembl_id"),
        })
    return out


def fetch_one(gene: str) -> dict:
    out = {
        "gene": gene,
        "chembl_target_id": None,
        "chembl_target_name": None,
        "n_potent_compounds": 0,
        "best_pchembl": None,
        "best_ic50_nm": None,
        "top_compounds": [],
    }
    target = resolve_target(gene)
    if not target:
        return out
    tid = target.get("target_chembl_id")
    out["chembl_target_id"] = tid
    out["chembl_target_name"] = target.get("pref_name")
    compounds = fetch_top_compounds(tid)
    if not compounds:
        return out
    out["top_compounds"] = compounds
    out["n_potent_compounds"] = len(compounds)
    try:
        out["best_pchembl"] = float(compounds[0]["pchembl_value"])
    except (TypeError, ValueError, KeyError):
        pass
    try:
        out["best_ic50_nm"] = float(compounds[0]["ic50_nm"])
    except (TypeError, ValueError, KeyError):
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    result = {}
    for i, g in enumerate(genes, 1):
        result[g] = fetch_one(g)
        if i % 10 == 0:
            print(f"  chembl: {i}/{len(genes)}", flush=True)
        time.sleep(args.sleep)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"chembl: wrote {len(result)} entries to {args.output}")


if __name__ == "__main__":
    main()
