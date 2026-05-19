#!/usr/bin/env python3
"""PubMed E-utilities fetcher: total paper count + two configurable
context counts (disease focus + cell / lineage focus) + 5 most-recent
focus-disease PMIDs.

Customize CONTEXTS for your project. Examples:
  - Autoimmunity:  '... AND ("inflammatory bowel"[tiab] OR "Crohn"[tiab] OR "ulcerative colitis"[tiab])'
  - Oncology:      '... AND ("cancer"[tiab] OR "tumor"[tiab] OR "neoplasm"[tiab])'
  - Neurodegen:    '... AND ("Alzheimer"[tiab] OR "Parkinson"[tiab] OR "neurodegeneration"[tiab])'
  - Cell context:  '"T cell"', '"macrophage"', '"hepatocyte"', '"neuron"', etc.
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

CONTEXTS = {
    "total":           '"{gene}"[tiab]',
    "focus_disease":   '"{gene}"[tiab] AND ("inflammatory bowel disease"[tiab] OR "Crohn"[tiab] OR "ulcerative colitis"[tiab] OR ibd[tiab])',
    "cell_context":    '"{gene}"[tiab] AND ("T cell"[tiab] OR "T-cell"[tiab] OR "T lymphocyte"[tiab])',
}


def esearch(term: str, retmax: int = 0) -> dict:
    params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": str(retmax), "sort": "pub_date"}
    url = f"{ESEARCH}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def fetch_one(gene: str) -> dict:
    out = {
        "gene": gene,
        "pubmed_total": 0,
        "pubmed_focus_disease": 0,
        "pubmed_cell_context": 0,
        "maturity_tag": None,
        "recent_focus_disease_pmids": [],
    }
    for key, tmpl in CONTEXTS.items():
        term = tmpl.format(gene=gene)
        retmax = 5 if key == "focus_disease" else 0
        data = esearch(term, retmax=retmax)
        try:
            count = int(data.get("esearchresult", {}).get("count", 0))
        except Exception:
            count = 0
        out[f"pubmed_{key}"] = count
        if key == "focus_disease":
            out["recent_focus_disease_pmids"] = data.get("esearchresult", {}).get("idlist", [])[:5]
        time.sleep(0.34)  # NCBI rate limit: 3/sec without API key

    total = out["pubmed_total"]
    if total < 5:
        out["maturity_tag"] = "uncharted"
    elif total < 30:
        out["maturity_tag"] = "novel"
    elif total < 100:
        out["maturity_tag"] = "moderate"
    elif total < 500:
        out["maturity_tag"] = "well_studied"
    else:
        out["maturity_tag"] = "saturated"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    result = {}
    for i, g in enumerate(genes, 1):
        result[g] = fetch_one(g)
        if i % 5 == 0:
            print(f"  pubmed: {i}/{len(genes)}", flush=True)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"pubmed: wrote {len(result)} entries to {args.output}")


if __name__ == "__main__":
    main()
