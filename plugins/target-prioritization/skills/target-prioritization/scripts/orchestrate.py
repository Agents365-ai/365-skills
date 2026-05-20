#!/usr/bin/env python3
"""Orchestrator: read gene list, dispatch fetchers in parallel, then call aggregate."""
import argparse
import csv
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_TOP = 50

FETCHERS = [
    ("uniprot",     SCRIPTS_DIR / "fetch_uniprot.py"),
    ("opentargets", SCRIPTS_DIR / "fetch_opentargets.py"),
    ("pubmed",      SCRIPTS_DIR / "fetch_pubmed.py"),
    ("hpa",         SCRIPTS_DIR / "fetch_hpa.py"),
]


def read_gene_list(path: Path, gene_col: str, top: int) -> list[str]:
    genes: list[str] = []
    with open(path, encoding="utf-8") as f:
        first = f.readline().strip()
        delim = "," if "," in first else ("\t" if "\t" in first else None)
        if delim is None:
            # plain text, one gene per line
            symbol = first.strip()
            if symbol and symbol.lower() not in {"gene", "symbol", "genes", "gene_symbol"}:
                genes.append(symbol)
            for line in f:
                s = line.strip()
                if s:
                    genes.append(s)
        else:
            header = [c.strip() for c in first.split(delim)]
            if gene_col in header:
                idx = header.index(gene_col)
            else:
                # fall back to first column
                idx = 0
            reader = csv.reader(f, delimiter=delim)
            # if header wasn't really a header (single column matches a known gene), include it
            if header[idx].lower() not in {"gene", "symbol", "genes", "gene_symbol", "feature"}:
                genes.append(header[idx])
            for row in reader:
                if row and len(row) > idx and row[idx].strip():
                    genes.append(row[idx].strip())
    # de-dup preserving order
    seen = set()
    unique = []
    for g in genes:
        if g not in seen:
            seen.add(g)
            unique.append(g)
    return unique[:top]


def run_fetcher(name: str, script: Path, genes: list[str], out_dir: Path) -> tuple[str, bool, str]:
    out_file = out_dir / "raw_data" / f"{name}.json"
    cmd = [
        sys.executable, str(script),
        "--genes", ",".join(genes),
        "--output", str(out_file),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        ok = proc.returncode == 0 and out_file.exists()
        msg = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else proc.stdout.strip()[:200]
        return name, ok, msg
    except subprocess.TimeoutExpired:
        return name, False, "TIMEOUT (>600s)"
    except Exception as e:
        return name, False, f"ERROR: {e}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="CSV/TSV/TXT with gene symbols")
    ap.add_argument("--output", required=True, help="Output directory")
    ap.add_argument("--gene-col", default="gene", help="Column name for gene symbols (default: gene)")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help=f"Top-N input genes to process (default: {DEFAULT_TOP})")
    ap.add_argument("--weights", default=str(SCRIPTS_DIR.parent / "weights.yaml"), help="Path to weights.yaml")
    args = ap.parse_args()

    inp = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw_data").mkdir(exist_ok=True)

    genes = read_gene_list(inp, args.gene_col, args.top)
    print(f"[orchestrate] Read {len(genes)} genes from {inp.name}")
    (out_dir / "raw_data" / "genes.json").write_text(json.dumps(genes, indent=2))

    # Run fetchers in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=len(FETCHERS)) as pool:
        futures = {pool.submit(run_fetcher, name, script, genes, out_dir): name
                   for name, script in FETCHERS}
        for fut in as_completed(futures):
            name, ok, msg = fut.result()
            results[name] = ok
            status = "ok " if ok else "FAIL"
            print(f"[orchestrate] {status} {name:14s} {msg}")

    # Aggregate
    agg = SCRIPTS_DIR / "aggregate.py"
    cmd = [
        sys.executable, str(agg),
        "--raw-dir", str(out_dir / "raw_data"),
        "--output-dir", str(out_dir),
        "--weights", args.weights,
        "--input-csv", str(inp) if inp.suffix.lower() in {".csv", ".tsv"} else "",
    ]
    proc = subprocess.run(cmd, capture_output=False)
    if proc.returncode != 0:
        print(f"[orchestrate] aggregate.py failed (exit {proc.returncode})", file=sys.stderr)
        sys.exit(proc.returncode)

    print(f"[orchestrate] Done. See {out_dir / 'targets_report.md'} and {out_dir / 'targets_summary.csv'}")


if __name__ == "__main__":
    main()
