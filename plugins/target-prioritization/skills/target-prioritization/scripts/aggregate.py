#!/usr/bin/env python3
"""Aggregate raw fetcher JSONs → composite score → targets_summary.csv + targets_report.md (skeleton)."""
import argparse
import csv
import json
import sys
from pathlib import Path


def load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  warn: could not parse {p}: {e}", file=sys.stderr)
        return {}


def load_weights(p: Path) -> dict:
    """Minimal YAML reader (no PyYAML dep) for our flat schema."""
    out = {"weights": {}, "caps": {}, "flags": {}}
    section = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith(("weights:", "caps:", "flags:")):
            section = line.split(":", 1)[0]
            continue
        if section and line.startswith((" ", "\t")):
            try:
                k, v = line.strip().split(":", 1)
                out[section][k.strip()] = float(v.strip())
            except Exception:
                continue
    return out


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


# Override to retarget for your project — see fetch_opentargets.py for examples.
FOCUS_DISEASE_TERMS = ("crohn", "ulcerative colitis", "inflammatory bowel", "ibd")

# HPA single-cell type names that count as "in-scope" for cell_context_score.
# Must match HPA's exact strings (case-sensitive). Examples for retargeting:
#   Oncology / tumor microenv: ("Macrophages", "Fibroblasts", "T-cells")
#   Neurodegeneration:         ("Excitatory neurons", "Microglial cells", "Astrocytes")
#   Metabolic / liver:         ("Hepatocytes", "Kupffer cells")
#   Cardiovascular:            ("Cardiomyocytes", "Endothelial cells")
#   Pancreatic / diabetes:     ("Pancreatic beta cells", "Pancreatic alpha cells")
FOCUS_CELL_TYPES = ("T-cells",)


def derive_hpa_signal(hpa_entry: dict) -> dict:
    """Translate HPA entry into score-ready signals.

    - tissue_specificity_score: cleaner therapeutic window → higher
    - cell_context_score: focus-cell-type nCPM rank within this gene's
      cell-type expression dict (1.0 if a focus cell is top-1, decays
      down the rank). Returns 0 if no focus cell is expressed.
    """
    tissue_tag = (hpa_entry.get("tissue_specificity_tag") or "").strip()
    TISSUE_MAP = {
        "Tissue enriched": 1.0,
        "Group enriched":  1.0,
        "Tissue enhanced": 0.7,
        "Low tissue specificity": 0.2,
        "Not detected": 0.0,
    }
    tissue_score = TISSUE_MAP.get(tissue_tag, 0.3)

    cell_full = hpa_entry.get("cell_nCPM_full") or {}
    if cell_full:
        ranked = sorted(cell_full.items(), key=lambda kv: -kv[1])
        focus_rank = None
        focus_hits = []
        for i, (ct, _val) in enumerate(ranked, 1):
            if ct in FOCUS_CELL_TYPES:
                focus_hits.append(ct)
                if focus_rank is None:
                    focus_rank = i
        if focus_rank is None:
            cell_score = 0.0
        else:
            # rank 1 → 1.0, rank 2 → 0.7, rank 3 → 0.5, then linear decay
            ladder = {1: 1.0, 2: 0.7, 3: 0.5}
            cell_score = ladder.get(focus_rank, max(0.0, 0.5 - 0.05 * (focus_rank - 3)))
    else:
        focus_hits = []
        cell_score = 0.0

    return {
        "tissue_score": tissue_score,
        "cell_score": cell_score,
        "focus_cell_hits": focus_hits,
    }


def derive_disease_signal(ot_entry: dict) -> dict:
    """Derive a disease_genetics-style signal from OpenTargets associated diseases.
    Replaces the dropped dedicated GWAS fetcher — OT integrates GWAS Catalog etc."""
    rows = ot_entry.get("associated_diseases_top5") or []
    any_assoc = bool(rows)
    focus_hits = []
    max_focus_score = 0.0
    max_any_score = 0.0
    for r in rows:
        name = (r.get("name") or "").lower()
        score = float(r.get("score") or 0)
        max_any_score = max(max_any_score, score)
        if any(t in name for t in FOCUS_DISEASE_TERMS):
            focus_hits.append(r.get("name"))
            max_focus_score = max(max_focus_score, score)
    return {
        "any_assoc": any_assoc,
        "is_focus_disease_associated": bool(focus_hits),
        "focus_disease_hits": focus_hits,
        "max_focus_disease_score": max_focus_score,
        "max_any_score": max_any_score,
    }


def compute_components(g: str, uniprot: dict, ot: dict, pubmed: dict, hpa: dict,
                       weights: dict, input_expr: dict) -> dict:
    w = weights["weights"]; c = weights["caps"]; f = weights["flags"]
    u = (uniprot.get(g) or {})
    o = (ot.get(g) or {})
    gw = derive_disease_signal(o)
    pm = (pubmed.get(g) or {})
    hp = (hpa.get(g) or {})
    hs = derive_hpa_signal(hp)
    tissue_specificity = clamp01(hs["tissue_score"])
    cell_context_score = clamp01(hs["cell_score"])

    # 2) druggability score
    drug = 0.0
    if o.get("approved_drug_count", 0) > 0:
        drug = max(drug, f.get("approved_drug_bonus", 0.7))
    phase = o.get("highest_clinical_phase", 0) or 0
    drug = max(drug, clamp01(phase / 4.0))
    if o.get("any_focus_disease_drug"):
        drug = max(drug, 0.85)
    druggability = clamp01(drug)

    # 3) disease genetics — derived from OpenTargets associated diseases
    g_score = 0.0
    if gw["any_assoc"]:
        g_score += 0.4 * gw["max_any_score"]
    if gw["is_focus_disease_associated"]:
        g_score += f.get("focus_disease_assoc_bonus", 0.5) + 0.2 * gw["max_focus_disease_score"]
    disease_genetics = clamp01(g_score)

    # 4) tractability bonus
    if u.get("is_surface"):
        tract = f.get("surface_protein_bonus", 1.0)
    elif u.get("is_secreted"):
        tract = f.get("secreted_protein_bonus", 0.8)
    else:
        tract = f.get("intracellular_default", 0.3)
    tractability = clamp01(tract)

    # 5) expression score — from input DE table (if provided)
    expr = input_expr.get(g)
    if expr is not None:
        expression = clamp01(expr / 3.0)   # log1p(CP10K) ~ 0-3 typical range
    else:
        expression = 0.0

    # 6) novelty bonus + 7) over-studied penalty
    total = pm.get("pubmed_total", 0)
    cap = c.get("pubmed_total_for_maturity", 100)
    floor = c.get("pubmed_well_studied_floor", 5)
    if total < floor:
        novelty = 0.3       # too uncharted = risk
        over_studied = 0.0
    elif total <= cap:
        novelty = 1.0
        over_studied = 0.0
    else:
        novelty = clamp01(1.0 - (total - cap) / (10 * cap))
        over_studied = clamp01((total - cap) / (5 * cap))

    composite = (
        w.get("druggability_score", 0)     * druggability
        + w.get("disease_genetics_score", 0) * disease_genetics
        + w.get("tractability_bonus", 0)     * tractability
        + w.get("tissue_specificity", 0)     * tissue_specificity
        + w.get("cell_context_score", 0)     * cell_context_score
        + w.get("expression_score", 0)       * expression
        + w.get("novelty_bonus", 0)          * novelty
        - w.get("over_studied_penalty", 0)   * over_studied
    )

    return {
        "druggability":       round(druggability, 3),
        "disease_genetics":   round(disease_genetics, 3),
        "tractability":       round(tractability, 3),
        "tissue_specificity": round(tissue_specificity, 3),
        "cell_context_score": round(cell_context_score, 3),
        "expression":         round(expression, 3),
        "novelty":            round(novelty, 3),
        "over_studied":       round(over_studied, 3),
        "composite_raw":      round(composite, 4),
    }


def tier_for(score_norm: float) -> str:
    if score_norm >= 0.75: return "Tier-1-priority"
    if score_norm >= 0.50: return "Tier-2-candidate"
    if score_norm >= 0.30: return "Tier-3-watchlist"
    return "Tier-4-deprioritized"


def load_input_expr(csv_path: str) -> dict:
    """Read mean_g2 / mean_g1 / max_mean from a DE CSV if present, keyed by gene."""
    expr = {}
    if not csv_path:
        return expr
    p = Path(csv_path)
    if not p.exists():
        return expr
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                g = row.get("gene") or row.get("symbol")
                if not g:
                    continue
                vals = []
                for k in ("mean_g2", "mean_g1", "sample_mean_g2", "sample_mean_g1"):
                    v = row.get(k)
                    try:
                        vals.append(float(v))
                    except (ValueError, TypeError):
                        continue
                if vals:
                    expr[g] = max(vals)
    except Exception:
        pass
    return expr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--input-csv", default="", help="Original DE CSV (used for expression score)")
    args = ap.parse_args()

    raw = Path(args.raw_dir)
    out_dir = Path(args.output_dir)
    weights = load_weights(Path(args.weights))

    genes = json.loads((raw / "genes.json").read_text(encoding="utf-8"))
    uniprot = load_json(raw / "uniprot.json")
    ot      = load_json(raw / "opentargets.json")
    pubmed  = load_json(raw / "pubmed.json")
    hpa     = load_json(raw / "hpa.json")
    input_expr = load_input_expr(args.input_csv)

    rows = []
    for g in genes:
        comp = compute_components(g, uniprot, ot, pubmed, hpa, weights, input_expr)
        u = uniprot.get(g, {}) or {}
        o = ot.get(g, {}) or {}
        gw = derive_disease_signal(o)
        pm = pubmed.get(g, {}) or {}
        hp = hpa.get(g, {}) or {}
        hs = derive_hpa_signal(hp)
        rows.append({
            "gene": g,
            "composite_raw": comp["composite_raw"],
            "druggability": comp["druggability"],
            "disease_genetics": comp["disease_genetics"],
            "tractability": comp["tractability"],
            "tissue_specificity": comp["tissue_specificity"],
            "cell_context_score": comp["cell_context_score"],
            "expression": comp["expression"],
            "novelty": comp["novelty"],
            "over_studied_penalty": comp["over_studied"],
            "uniprot_id": u.get("uniprot_id"),
            "protein_name": u.get("protein_name"),
            "subcellular_location": " | ".join(u.get("subcellular_location") or []),
            "is_surface": u.get("is_surface"),
            "is_secreted": u.get("is_secreted"),
            "is_mhc": u.get("is_mhc"),
            "has_transmembrane": u.get("has_transmembrane"),
            "approved_drug_count": o.get("approved_drug_count", 0),
            "highest_clinical_phase": o.get("highest_clinical_phase", 0),
            "any_focus_disease_drug": o.get("any_focus_disease_drug", False),
            "focus_disease_drugs": "; ".join(o.get("focus_disease_drugs") or []),
            "tractability_small_molecule": o.get("tractability_small_molecule"),
            "tractability_antibody": o.get("tractability_antibody"),
            "any_disease_assoc": gw["any_assoc"],
            "is_focus_disease_associated": gw["is_focus_disease_associated"],
            "focus_disease_traits": "; ".join(gw["focus_disease_hits"]),
            "max_focus_disease_assoc_score": round(gw["max_focus_disease_score"], 3),
            "max_disease_assoc_score": round(gw["max_any_score"], 3),
            "pubmed_total": pm.get("pubmed_total", 0),
            "pubmed_focus_disease": pm.get("pubmed_focus_disease", 0),
            "pubmed_cell_context": pm.get("pubmed_cell_context", 0),
            "maturity_tag": pm.get("maturity_tag"),
            "hpa_tissue_specificity_tag": hp.get("tissue_specificity_tag"),
            "hpa_tissue_top_types": "; ".join(f"{k}={v}" for k, v in (hp.get("tissue_top_types") or [])),
            "hpa_cell_specificity_tag": hp.get("cell_specificity_tag"),
            "hpa_cell_top_types": "; ".join(f"{k}={v}" for k, v in (hp.get("cell_top_types") or [])),
            "hpa_focus_cell_hits": "; ".join(hs["focus_cell_hits"]),
            "hpa_expression_cluster": hp.get("expression_cluster"),
            "hpa_n_prognostic_cancers": (hp.get("pathology") or {}).get("n_prognostic_cancers", 0),
            "hpa_cancer_specificity": (hp.get("pathology") or {}).get("rna_cancer_specificity"),
        })

    # Min-max rescale composite into [0,1] for tier assignment
    raws = [r["composite_raw"] for r in rows]
    lo, hi = (min(raws), max(raws)) if raws else (0.0, 1.0)
    span = (hi - lo) or 1.0
    for r in rows:
        r["composite_score"] = round((r["composite_raw"] - lo) / span, 3)
        r["tier"] = tier_for(r["composite_score"])

    rows.sort(key=lambda r: -r["composite_score"])

    # CSV
    csv_path = out_dir / "targets_summary.csv"
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"aggregate: wrote {csv_path}")

    # Markdown skeleton (rationale slots left for Claude to fill)
    md = ["# Target Prioritization Report\n",
          f"_{len(rows)} genes scored. Sorted by composite_score (descending)._\n",
          "## Executive summary\n",
          "_TO BE FILLED BY CLAUDE — 3–5 sentences on the top 5–10 genes._\n",
          "## Per-gene dossier\n"]
    for r in rows:
        md.append(f"### {r['gene']}  —  composite {r['composite_score']:.3f}  ({r['tier']})\n")
        md.append("| Field | Value |")
        md.append("|---|---|")
        md.append(f"| UniProt | {r['uniprot_id'] or '—'} — {r['protein_name'] or '—'} |")
        md.append(f"| Localization | {r['subcellular_location'] or '—'} |")
        md.append(f"| Surface / secreted / MHC | surf={r['is_surface']}  sec={r['is_secreted']}  mhc={r['is_mhc']}  TM={r['has_transmembrane']} |")
        md.append(f"| Druggability | approved={r['approved_drug_count']}  max_phase={r['highest_clinical_phase']}  focus_disease_drug={r['any_focus_disease_drug']}  focus_disease_drugs={r['focus_disease_drugs'] or '—'} |")
        md.append(f"| Tractability | sm_mol={r['tractability_small_molecule'] or '—'}  Ab={r['tractability_antibody'] or '—'} |")
        md.append(f"| Disease assoc (OT) | any={r['any_disease_assoc']}  focus={r['is_focus_disease_associated']}  focus_traits={r['focus_disease_traits'] or '—'}  max_score={r['max_disease_assoc_score']} |")
        md.append(f"| PubMed | total={r['pubmed_total']}  focus_disease={r['pubmed_focus_disease']}  cell_context={r['pubmed_cell_context']}  maturity={r['maturity_tag']} |")
        md.append(f"| HPA tissue | tag={r['hpa_tissue_specificity_tag'] or '—'}  top={r['hpa_tissue_top_types'] or '—'} |")
        md.append(f"| HPA single-cell | tag={r['hpa_cell_specificity_tag'] or '—'}  top={r['hpa_cell_top_types'] or '—'}  focus_cell_hits={r['hpa_focus_cell_hits'] or '—'}  cluster={r['hpa_expression_cluster'] or '—'} |")
        md.append(f"| HPA pathology | n_prognostic_cancers={r['hpa_n_prognostic_cancers']}  cancer_specificity={r['hpa_cancer_specificity'] or '—'} |")
        md.append(f"| Component breakdown | drug={r['druggability']}  genetics={r['disease_genetics']}  tract={r['tractability']}  tissue_spec={r['tissue_specificity']}  cell_ctx={r['cell_context_score']}  expr={r['expression']}  novelty={r['novelty']}  over_studied={r['over_studied_penalty']} |")
        md.append("")
        md.append("**Rationale**: _TO BE FILLED BY CLAUDE — 2–3 sentences. Use prompts/rationale_template.md._")
        md.append("")
        md.append("**Suggested next step**: _TO BE FILLED BY CLAUDE — 1 concrete sentence (e.g. siRNA knockdown in the relevant cell type; orthogonal IHC; ex-vivo tool-compound challenge; cross-cohort replication)._")
        md.append("")
        md.append("---\n")

    md_path = out_dir / "targets_report.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"aggregate: wrote {md_path}")


if __name__ == "__main__":
    main()
