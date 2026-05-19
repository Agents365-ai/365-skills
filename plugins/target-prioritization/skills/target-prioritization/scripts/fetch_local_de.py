#!/usr/bin/env python3
"""Local-evidence fetcher: scan the user's project for cross-lineage DE convergence.

Looks for sibling DE-pipeline output CSVs under <project_root> matching common
patterns (`hu_de_*`, `pert_de_*`, `cluster_degs*`, `de_*`) and reports, per gene,
which lineages/contrasts also flag it as significant — and in which direction.

Heuristics:
- A "DE table" is a CSV whose header includes a gene-name column
  (`gene`/`feature`/`symbol`) and at least one of: log2FC / avg_log2FC / fc /
  pvalue / pass_*.
- "Significant" = (pass_both_1s == True) OR (any adj-p column < 0.05) OR
  (logfc_threshold met).
- Direction = sign of the first log2FC-like column found.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

DE_DIR_PATTERNS = re.compile(r"(hu_de_|pert_de_|cluster_degs|^de_|cd4t_markers)", re.I)
GENE_COLS = {"gene", "feature", "symbol", "gene_symbol", "names"}
LOG2FC_COLS = ("avg_log2fc", "log2fc", "log2foldchange", "logfc", "log2fc_sample")
PVAL_COLS = ("adj_pvalue", "p_val_adj", "padj", "fdr", "sample_wilcox_adj_1s", "sample_t_adj_1s", "qvalue")
PASS_COLS = ("pass_both_1s", "pass_either_1s", "significant", "is_sig")
PVAL_CUTOFF = 0.05


def find_de_files(root: Path, max_files: int = 200) -> list[Path]:
    candidates = []
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        if DE_DIR_PATTERNS.search(d.name) or DE_DIR_PATTERNS.search(str(d.relative_to(root))):
            for f in d.rglob("*.csv"):
                # skip huge counts/expression matrices
                try:
                    if f.stat().st_size > 50_000_000:
                        continue
                except OSError:
                    continue
                candidates.append(f)
                if len(candidates) >= max_files:
                    return candidates
    return candidates


def parse_header(path: Path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
    except Exception:
        return None
    if not header:
        return None
    lc = [h.strip().lower() for h in header]
    gene_idx = None
    for i, h in enumerate(lc):
        if h in GENE_COLS:
            gene_idx = i
            break
    if gene_idx is None:
        return None
    log2fc_idx = next((i for i, h in enumerate(lc) if h in LOG2FC_COLS), None)
    pval_idx = next((i for i, h in enumerate(lc) if h in PVAL_COLS), None)
    pass_idx = next((i for i, h in enumerate(lc) if h in PASS_COLS), None)
    if log2fc_idx is None and pval_idx is None and pass_idx is None:
        return None
    return {"header": header, "lc": lc, "gene_idx": gene_idx,
            "log2fc_idx": log2fc_idx, "pval_idx": pval_idx, "pass_idx": pass_idx}


def scan_file(path: Path, gene_set: set[str]) -> dict[str, dict]:
    meta = parse_header(path)
    if not meta:
        return {}
    hits: dict[str, dict] = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or len(row) <= meta["gene_idx"]:
                    continue
                g = row[meta["gene_idx"]].strip()
                if g not in gene_set:
                    continue
                # gather signal
                fc = None
                if meta["log2fc_idx"] is not None and len(row) > meta["log2fc_idx"]:
                    try:
                        fc = float(row[meta["log2fc_idx"]])
                    except (ValueError, TypeError):
                        fc = None
                pval = None
                if meta["pval_idx"] is not None and len(row) > meta["pval_idx"]:
                    try:
                        pval = float(row[meta["pval_idx"]])
                    except (ValueError, TypeError):
                        pval = None
                pass_flag = None
                if meta["pass_idx"] is not None and len(row) > meta["pass_idx"]:
                    v = row[meta["pass_idx"]].strip().lower()
                    pass_flag = v in ("true", "1", "yes")

                significant = (pass_flag is True) or (pval is not None and pval < PVAL_CUTOFF and (fc is None or abs(fc) >= 0.25))
                if not significant:
                    continue
                hits.setdefault(g, []).append({
                    "log2fc": fc,
                    "pval": pval,
                    "pass_flag": pass_flag,
                    "direction": ("up_g1" if (fc and fc > 0) else ("up_g2" if (fc and fc < 0) else "unknown")),
                })
    except Exception:
        return hits
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True)
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        print(f"local_de: project root not found: {root}", file=sys.stderr)
        sys.exit(2)

    genes = [g.strip() for g in args.genes.split(",") if g.strip()]
    gene_set = set(genes)
    files = find_de_files(root)
    print(f"local_de: scanning {len(files)} candidate DE files under {root}")

    per_gene_evidence: dict[str, list[dict]] = {g: [] for g in genes}
    for f in files:
        rel = f.relative_to(root)
        hits = scan_file(f, gene_set)
        for g, recs in hits.items():
            for rec in recs:
                rec_with_src = dict(rec)
                rec_with_src["source"] = str(rel)
                per_gene_evidence[g].append(rec_with_src)

    # Summarize
    summary = {}
    for g in genes:
        ev = per_gene_evidence[g]
        # Unique source files (lineage/contrast)
        sources = sorted({e["source"] for e in ev})
        # Compress direction summary
        up_g1 = sum(1 for e in ev if e["direction"] == "up_g1")
        up_g2 = sum(1 for e in ev if e["direction"] == "up_g2")
        summary[g] = {
            "gene": g,
            "n_supporting_files": len(sources),
            "supporting_files": sources[:15],
            "n_events": len(ev),
            "up_g1_events": up_g1,
            "up_g2_events": up_g2,
            "raw_events": ev[:30],   # cap to keep JSON small
        }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"local_de: wrote summary for {len(summary)} genes to {args.output}")


if __name__ == "__main__":
    main()
