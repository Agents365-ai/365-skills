#!/usr/bin/env python3
"""UniProt fetcher: per gene → subcellular localization, surface/secreted flag,
MHC flag, coding status, protein class.

Uses UniProt REST search endpoint with human + reviewed filter."""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/search"
FIELDS = "accession,gene_names,protein_name,cc_subcellular_location,protein_existence,keyword,ft_topo_dom,ft_transmem,ft_signal,cc_function"

MHC_PATTERNS = [
    re.compile(r"^HLA-[A-Z]{1,3}$", re.I),
    re.compile(r"^B2M$", re.I),
    re.compile(r"^TAP[12]$", re.I),
    re.compile(r"^TAPBP$", re.I),
    re.compile(r"^CD1[A-E]?$", re.I),
]


def is_mhc(gene: str) -> bool:
    return any(p.match(gene) for p in MHC_PATTERNS)


def fetch_one(gene: str) -> dict:
    """Query UniProt for a single human gene; return parsed fields."""
    query = f'(gene:{gene}) AND (organism_id:9606) AND (reviewed:true)'
    params = {"query": query, "fields": FIELDS, "format": "json", "size": "1"}
    url = f"{UNIPROT_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return {"gene": gene, "error": str(e)}

    out = {
        "gene": gene,
        "uniprot_id": None,
        "protein_name": None,
        "subcellular_location": [],
        "is_surface": False,
        "is_secreted": False,
        "is_mhc": is_mhc(gene),
        "is_coding": True,
        "has_transmembrane": False,
        "has_signal_peptide": False,
        "keywords": [],
        "protein_existence": None,
        "function_short": None,
    }
    results = data.get("results") or []
    if not results:
        return out
    rec = results[0]
    out["uniprot_id"] = rec.get("primaryAccession")
    name = rec.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value")
    out["protein_name"] = name
    out["protein_existence"] = rec.get("proteinExistence")

    # Subcellular location
    for cmt in rec.get("comments", []):
        if cmt.get("commentType") == "SUBCELLULAR LOCATION":
            for loc in cmt.get("subcellularLocations", []):
                v = loc.get("location", {}).get("value")
                if v:
                    out["subcellular_location"].append(v)
        if cmt.get("commentType") == "FUNCTION" and not out["function_short"]:
            for t in cmt.get("texts", []):
                if t.get("value"):
                    out["function_short"] = t["value"][:240]
                    break

    loc_lc = " | ".join(out["subcellular_location"]).lower()
    if any(s in loc_lc for s in ("cell membrane", "plasma membrane", "cell surface")):
        out["is_surface"] = True
    if any(s in loc_lc for s in ("secreted", "extracellular")):
        out["is_secreted"] = True

    # Features
    for ft in rec.get("features", []):
        if ft.get("type") == "Transmembrane":
            out["has_transmembrane"] = True
        if ft.get("type") == "Signal":
            out["has_signal_peptide"] = True
    if out["has_transmembrane"]:
        out["is_surface"] = True
    if out["has_signal_peptide"] and not out["is_surface"]:
        out["is_secreted"] = True

    out["keywords"] = [k.get("name") for k in rec.get("keywords", []) if k.get("name")][:20]

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True, help="Comma-separated gene symbols")
    ap.add_argument("--output", required=True)
    ap.add_argument("--sleep", type=float, default=0.1)
    args = ap.parse_args()

    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    result = {}
    for i, g in enumerate(genes, 1):
        result[g] = fetch_one(g)
        if i % 20 == 0:
            print(f"  uniprot: {i}/{len(genes)}", flush=True)
        time.sleep(args.sleep)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"uniprot: wrote {len(result)} entries to {args.output}")


if __name__ == "__main__":
    main()
