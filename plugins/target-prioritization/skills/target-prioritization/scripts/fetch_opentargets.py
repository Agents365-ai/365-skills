#!/usr/bin/env python3
"""OpenTargets GraphQL fetcher: druggability + approved drugs per gene.

Queries by gene symbol → resolves Ensembl ID → drug + tractability summary.

Customize FOCUS_DISEASE_TERMS for your project. Examples:
  - Autoimmunity:    ("crohn", "ulcerative colitis", "inflammatory bowel")
  - Oncology:        ("cancer", "carcinoma", "lymphoma", "leukemia", "tumor")
  - Neurodegen:      ("alzheimer", "parkinson", "huntington", "als")
  - Metabolic:       ("diabetes", "obesity", "fatty liver", "nash")
A drug whose indication list contains any of these substrings is tagged
in `focus_disease_drugs` and `any_focus_disease_drug = True`.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

OT_URL = "https://api.platform.opentargets.org/api/v4/graphql"

ID_QUERY = """
query Resolve($q: String!) {
  search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 1}) {
    hits { id name entity }
  }
}
"""

TARGET_QUERY = """
query Target($id: String!) {
  target(ensemblId: $id) {
    id approvedSymbol approvedName biotype
    tractability { modality value label }
    drugAndClinicalCandidates {
      count
      rows {
        id
        maxClinicalStage
        drug { id name maximumClinicalStage drugType mechanismsOfAction { rows { mechanismOfAction } } }
        diseases { diseaseFromSource disease { id name } }
      }
    }
    associatedDiseases(page: {index:0, size:10}) {
      rows { disease { id name } score }
    }
    depMapEssentiality {
      tissueName
      screens { cellLineName geneEffect }
    }
    geneticConstraint {
      constraintType
      oe
      oeUpper
      upperBin
    }
  }
}
"""

PHASE_MAP = {
    "APPROVAL": 4, "PHASE_IV": 4, "PHASE_4": 4,
    "PHASE_III": 3, "PHASE_3": 3,
    "PHASE_II": 2, "PHASE_2": 2,
    "PHASE_I": 1, "PHASE_1": 1,
    "EARLY_PHASE_1": 1, "PRECLINICAL": 0,
    "WITHDRAWN": -1, "UNKNOWN": 0, "": 0,
}


def stage_to_phase(stage: str | None) -> int:
    if not stage:
        return 0
    return PHASE_MAP.get(stage.strip().upper(), 0)


def is_approved_stage(stage: str | None) -> bool:
    return bool(stage and stage.strip().upper() in {"APPROVAL", "PHASE_IV", "PHASE_4"})


# Per-modality tractability label priority (highest tier first).
TRACTABILITY_PRIORITY = [
    "Approved Drug", "Advanced Clinical", "Phase 1 Clinical",
    "Structure with Ligand", "High-Quality Ligand", "High-Quality Pocket",
    "Med-Quality Pocket", "Druggable Family",
    "UniProt loc high conf", "GO CC high conf", "UniProt loc med conf",
    "UniProt SigP or TMHMM", "GO CC med conf", "Human Protein Atlas loc",
    "Small Molecule Binder", "Literature",
]


def best_label(entries: list[dict]) -> str | None:
    """Among entries whose value is True, return the highest-priority label."""
    true_labels = {e.get("label") for e in entries if e.get("value")}
    for lbl in TRACTABILITY_PRIORITY:
        if lbl in true_labels:
            return lbl
    return None


# Lowercased substrings — a drug-indication string that contains any of
# these is tagged as a focus-disease drug. Override for your project.
FOCUS_DISEASE_TERMS = ("crohn", "ulcerative colitis", "inflammatory bowel")


def gql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        OT_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"errors": [str(e)]}


def fetch_one(gene: str) -> dict:
    out = {
        "gene": gene,
        "ensembl_id": None,
        "approved_symbol": None,
        "biotype": None,
        "tractability_small_molecule": None,
        "tractability_antibody": None,
        "tractability_other": [],
        "approved_drug_count": 0,
        "approved_drugs": [],
        "highest_clinical_phase": 0,
        "any_focus_disease_drug": False,
        "focus_disease_drugs": [],
        "associated_diseases_top5": [],
        "depmap_n_screens": 0,
        "depmap_n_tissues": 0,
        "depmap_mean_gene_effect": None,
        "depmap_pct_essential": 0.0,
        "loeuf": None,
        "constraint_oe_lof": None,
        "constraint_top_decile": False,
    }
    # resolve
    r = gql(ID_QUERY, {"q": gene})
    hits = (r.get("data") or {}).get("search", {}).get("hits", []) or []
    if not hits:
        return out
    ensembl_id = hits[0]["id"]
    out["ensembl_id"] = ensembl_id
    out["approved_symbol"] = hits[0]["name"]

    r = gql(TARGET_QUERY, {"id": ensembl_id})
    tgt = (r.get("data") or {}).get("target")
    if not tgt:
        return out
    out["biotype"] = tgt.get("biotype")
    by_modality: dict[str, list[dict]] = {}
    for tr in tgt.get("tractability", []) or []:
        by_modality.setdefault((tr.get("modality") or "").upper(), []).append(tr)
    out["tractability_small_molecule"] = best_label(by_modality.get("SM", []))
    out["tractability_antibody"] = best_label(by_modality.get("AB", []))
    for mod in ("PR", "OC"):
        lbl = best_label(by_modality.get(mod, []))
        if lbl:
            out["tractability_other"].append(f"{mod}:{lbl}")

    kd = tgt.get("drugAndClinicalCandidates") or {}
    drugs_seen: dict[str, dict] = {}
    for row in kd.get("rows", []) or []:
        drug = row.get("drug") or {}
        name = drug.get("name")
        if not name:
            continue
        # Row-level max stage and drug-level max stage; take the larger
        row_phase = stage_to_phase(row.get("maxClinicalStage"))
        drug_phase = stage_to_phase(drug.get("maximumClinicalStage"))
        ph = max(row_phase, drug_phase)
        approved = is_approved_stage(row.get("maxClinicalStage")) or is_approved_stage(drug.get("maximumClinicalStage"))
        out["highest_clinical_phase"] = max(out["highest_clinical_phase"], ph)
        d = drugs_seen.setdefault(name, {
            "name": name,
            "approved": approved,
            "max_phase": ph,
            "mechanisms": set(),
            "diseases": set(),
        })
        d["max_phase"] = max(d["max_phase"], ph)
        if approved:
            d["approved"] = True
        moa = ((drug.get("mechanismsOfAction") or {}).get("rows") or [])
        for m in moa:
            if m.get("mechanismOfAction"):
                d["mechanisms"].add(m["mechanismOfAction"])
        for dis_item in (row.get("diseases") or []):
            dis = (dis_item.get("disease") or {}).get("name") or dis_item.get("diseaseFromSource")
            if not dis:
                continue
            d["diseases"].add(dis)
            if any(t in dis.lower() for t in FOCUS_DISEASE_TERMS):
                out["any_focus_disease_drug"] = True
                if name not in out["focus_disease_drugs"]:
                    out["focus_disease_drugs"].append(name)

    approved = [d for d in drugs_seen.values() if d["approved"]]
    out["approved_drug_count"] = len(approved)
    out["approved_drugs"] = [
        {"name": d["name"], "max_phase": d["max_phase"],
         "mechanisms": sorted(d["mechanisms"]), "diseases": sorted(d["diseases"])[:5]}
        for d in approved[:10]
    ]

    for row in (tgt.get("associatedDiseases") or {}).get("rows", []) or []:
        out["associated_diseases_top5"].append({
            "name": (row.get("disease") or {}).get("name"),
            "score": row.get("score"),
        })

    # DepMap CRISPR essentiality — geneEffect < 0 means KO reduces fitness.
    # We summarize across all screened cell lines; pan-essentials (>80%) and
    # never-essentials (<5%) both flag low-priority targets via the cap.
    effects: list[float] = []
    tissues = tgt.get("depMapEssentiality") or []
    for tissue in tissues:
        for s in tissue.get("screens") or []:
            ge = s.get("geneEffect")
            if isinstance(ge, (int, float)):
                effects.append(float(ge))
    if effects:
        out["depmap_n_screens"] = len(effects)
        out["depmap_n_tissues"] = len(tissues)
        out["depmap_mean_gene_effect"] = sum(effects) / len(effects)
        out["depmap_pct_essential"] = sum(1 for e in effects if e < -0.5) / len(effects)

    # gnomAD-derived constraint (loaded from OT's geneticConstraint table).
    # The "lof" row carries LOEUF (oeUpper) — lower = more constrained.
    for row in tgt.get("geneticConstraint") or []:
        if row.get("constraintType") == "lof":
            out["loeuf"] = row.get("oeUpper")
            out["constraint_oe_lof"] = row.get("oe")
            out["constraint_top_decile"] = (row.get("upperBin") == 1)
            break

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
            print(f"  opentargets: {i}/{len(genes)}", flush=True)
        time.sleep(args.sleep)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"opentargets: wrote {len(result)} entries to {args.output}")


if __name__ == "__main__":
    main()
