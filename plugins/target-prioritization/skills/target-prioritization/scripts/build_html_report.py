#!/usr/bin/env python3
"""Build a self-contained, interactive HTML report from targets_summary.csv +
targets_report.md.

Run this AFTER Claude has filled the per-gene Rationale / Suggested-next-step
slots and the Executive summary in `targets_report.md`. Writes
`targets_report.html` in the same directory.

Output is a single .html file with no external dependencies:
- Executive summary + tier counts
- Sortable / searchable / tier-filterable summary table
- Per-gene cards: rationale, evidence chips, full dossier grid,
  score-component bars, and links to UniProt
"""

import argparse
import csv
import html
import re
from pathlib import Path

TIER_COLOR = {
  "Tier-1-priority": "#10b981",
  "Tier-2-candidate": "#3b82f6",
  "Tier-3-watchlist": "#f59e0b",
  "Tier-4-deprioritized": "#94a3b8",
}


def md_inline_to_html(s: str) -> str:
  """Convert a small subset of markdown (escape, **bold**, *italic*, paragraphs)."""
  s = html.escape(s)
  s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
  s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
  s = re.sub(r"\n\n+", "</p><p>", s)
  return f"<p>{s}</p>"


def parse_report_md(md_text: str):
  """Extract executive summary and per-gene {rationale, next_step} from the md report."""
  exec_summary_md = ""
  m = re.search(
    r"## Executive summary\n\n(.*?)\n\n## Per-gene dossier", md_text, re.DOTALL
  )
  if m:
    exec_summary_md = m.group(1).strip()
    # If the placeholder is still present, blank it out so the HTML doesn't show it.
    if "TO BE FILLED BY CLAUDE" in exec_summary_md:
      exec_summary_md = "<em>Executive summary not yet written — fill the slot in targets_report.md and re-run.</em>"

  rationales = {}
  for block in re.split(r"\n---\n", md_text):
    h = re.search(r"### ([A-Z0-9\-]+)\s+—\s+composite\s+([0-9.]+)\s+\(([^)]+)\)", block)
    if not h:
      continue
    gene = h.group(1)
    rat = re.search(
      r"\*\*Rationale\*\*:\s+(.*?)\n\n\*\*Suggested next step\*\*", block, re.DOTALL
    )
    nxt = re.search(r"\*\*Suggested next step\*\*:\s+(.*?)(?:\n\n|$)", block, re.DOTALL)
    r_txt = rat.group(1).strip() if rat else ""
    n_txt = nxt.group(1).strip() if nxt else ""
    if "TO BE FILLED BY CLAUDE" in r_txt:
      r_txt = ""
    if "TO BE FILLED BY CLAUDE" in n_txt:
      n_txt = ""
    rationales[gene] = {"rationale": r_txt, "next_step": n_txt}
  return exec_summary_md, rationales


def fmt(v, decimals=None):
  if v is None or v == "" or v == "None":
    return "—"
  if decimals is not None:
    try:
      return f"{float(v):.{decimals}f}"
    except ValueError:
      return v
  return v


def bool_badge(v) -> str:
  if str(v).lower() == "true":
    return '<span class="badge badge-yes">yes</span>'
  return '<span class="badge badge-no">no</span>'


def bar(val, max_val=1.0, color="#3b82f6") -> str:
  try:
    v = float(val)
  except (ValueError, TypeError):
    return "—"
  pct = max(0, min(100, 100 * v / max_val))
  return (
    f'<div class="bar"><div class="bar-fill" style="width:{pct:.0f}%;background:{color};"></div>'
    f'<span class="bar-label">{v:.2f}</span></div>'
  )


def render_card(row, rationales):
  gene = row["gene"]
  tier = row["tier"]
  rat = rationales.get(gene, {}).get("rationale", "")
  nxt = rationales.get(gene, {}).get("next_step", "")
  color = TIER_COLOR.get(tier, "#64748b")
  # Escape CSV-sourced values before interpolating into HTML attributes/content.
  # `gene` is also used in the URL fragment and `id` attribute; html.escape with
  # the default quote=True handles both content and attribute contexts.
  gene_html = html.escape(gene)
  uniprot_html = html.escape(row["uniprot_id"] or "")

  def cell(label, value):
    return f"<div class='kv'><div class='kv-k'>{label}</div><div class='kv-v'>{value}</div></div>"

  chips = []
  if row["is_surface"] == "True":
    chips.append('<span class="chip chip-surface">surface</span>')
  if row["is_secreted"] == "True":
    chips.append('<span class="chip chip-secreted">secreted</span>')
  if row["is_mhc"] == "True":
    chips.append('<span class="chip chip-mhc">MHC</span>')
  if row["has_transmembrane"] == "True":
    chips.append('<span class="chip chip-tm">TM</span>')
  if row["is_focus_disease_associated"] == "True":
    chips.append('<span class="chip chip-focus">focus-disease</span>')
  if row["any_focus_disease_drug"] == "True":
    chips.append('<span class="chip chip-drug">approved drug</span>')
  chips_html = " ".join(chips)

  focus_drugs = row["focus_disease_drugs"] or "—"
  focus_traits = row["focus_disease_traits"] or "—"

  breakdown_keys = [
    ("Druggability", "druggability"),
    ("Disease genetics", "disease_genetics"),
    ("Tractability", "tractability"),
    ("Tissue specificity", "tissue_specificity"),
    ("Cell context", "cell_context_score"),
    ("Essentiality", "essentiality_score"),
    ("Safety constraint", "safety_constraint_score"),
    ("Expression (DE)", "expression"),
    ("Novelty", "novelty"),
    ("Over-studied penalty", "over_studied_penalty"),
  ]
  breakdown_rows = "".join(
    f"<tr><td>{label}</td><td>{bar(row[k])}</td></tr>" for label, k in breakdown_keys
  )

  chembl_top = row["chembl_top_compounds"] or "—"
  chembl = (
    f"target={fmt(row['chembl_target_id'])} · "
    f"best pIC50={fmt(row['chembl_best_pchembl'])} · "
    f"best IC50 nM={fmt(row['chembl_best_ic50_nm'])}"
  )

  pct_ess = ""
  if row["depmap_pct_essential"]:
    try:
      pct_ess = f"{float(row['depmap_pct_essential']) * 100:.1f}"
    except ValueError:
      pct_ess = row["depmap_pct_essential"]
  pct_ess = pct_ess or "—"

  return f"""
    <article class="card" data-gene="{gene_html}" data-tier="{tier}" id="g-{gene_html}">
      <header class="card-head" style="border-left-color:{color}">
        <div>
          <h2>{gene_html} <span class="composite">composite {fmt(row["composite_score"], 3)}</span></h2>
          <div class="card-sub">{html.escape(row["protein_name"])} · <a href="https://www.uniprot.org/uniprotkb/{uniprot_html}" target="_blank" rel="noopener">{uniprot_html}</a></div>
          <div class="chips">{chips_html}</div>
        </div>
        <div class="tier-badge" style="background:{color}">{tier}</div>
      </header>

      <div class="card-body">
        <section class="rationale">
          <h3>Rationale</h3>
          <p>{html.escape(rat) or "<em>not yet written</em>"}</p>
          <h3>Suggested next step</h3>
          <p>{html.escape(nxt) or "<em>not yet written</em>"}</p>
        </section>

        <section class="grid">
          {cell("Localization", html.escape(row["subcellular_location"]) or "—")}
          {cell("Druggability", f"approved={row['approved_drug_count']} · max_phase={row['highest_clinical_phase']} · focus_disease_drug={bool_badge(row['any_focus_disease_drug'])}")}
          {cell("Focus-disease drugs", html.escape(focus_drugs))}
          {cell("Tractability", f"sm_mol={fmt(row['tractability_small_molecule'])} · Ab={fmt(row['tractability_antibody'])}")}
          {cell("Disease assoc (OT)", f"any={bool_badge(row['any_disease_assoc'])} · focus={bool_badge(row['is_focus_disease_associated'])} · focus_score={fmt(row['max_focus_disease_assoc_score'], 3)} · max_score={fmt(row['max_disease_assoc_score'], 3)}")}
          {cell("Focus traits", html.escape(focus_traits))}
          {cell("PubMed", f"total={row['pubmed_total']} · focus_disease={row['pubmed_focus_disease']} · cell_context={row['pubmed_cell_context']} · maturity={row['maturity_tag']}")}
          {cell("HPA tissue", f"{row['hpa_tissue_specificity_tag']} · top={html.escape(row['hpa_tissue_top_types']) or '—'}")}
          {cell("HPA single-cell", f"{row['hpa_cell_specificity_tag']} · top={html.escape(row['hpa_cell_top_types']) or '—'} · focus_hits={html.escape(row['hpa_focus_cell_hits']) or '—'}")}
          {cell("HPA cluster", html.escape(row["hpa_expression_cluster"]) or "—")}
          {cell("HPA pathology", f"n_prog_cancers={row['hpa_n_prognostic_cancers']} · {row['hpa_cancer_specificity']}")}
          {cell("DepMap CRISPR", f"n={row['depmap_n_screens']} · mean_effect={fmt(row['depmap_mean_gene_effect'], 3)} · %essential={pct_ess}")}
          {cell("gnomAD constraint", f"LOEUF={fmt(row['loeuf'], 3)} · oe_lof={fmt(row['constraint_oe_lof'], 3)} · top_decile={bool_badge(row['constraint_top_decile'])}")}
          {cell("ChEMBL", chembl)}
          {cell("ChEMBL top compounds", html.escape(chembl_top))}
        </section>

        <section class="breakdown">
          <h3>Score breakdown</h3>
          <table>{breakdown_rows}</table>
        </section>
      </div>
    </article>
    """


def render_summary_row(r):
  color = TIER_COLOR.get(r["tier"], "#64748b")
  gene_html = html.escape(r["gene"])
  flags = []
  if r["is_surface"] == "True":
    flags.append("S")
  if r["is_secreted"] == "True":
    flags.append("Sec")
  if r["is_mhc"] == "True":
    flags.append("MHC")
  flags_str = "/".join(flags) or "—"
  tier_short = (
    r["tier"]
    .replace("Tier-", "T")
    .replace("-priority", "")
    .replace("-candidate", "")
    .replace("-watchlist", "")
    .replace("-deprioritized", "")
  )
  return f"""
      <tr data-tier="{r["tier"]}">
        <td><a href="#g-{gene_html}">{gene_html}</a></td>
        <td data-sort="{r["composite_score"]}">{fmt(r["composite_score"], 3)}</td>
        <td><span class="tier-pill" style="background:{color}">{tier_short}</span></td>
        <td>{flags_str}</td>
        <td data-sort="{r["druggability"]}">{fmt(r["druggability"], 2)}</td>
        <td data-sort="{r["disease_genetics"]}">{fmt(r["disease_genetics"], 2)}</td>
        <td data-sort="{r["cell_context_score"]}">{fmt(r["cell_context_score"], 2)}</td>
        <td data-sort="{r["safety_constraint_score"]}">{fmt(r["safety_constraint_score"], 2)}</td>
        <td>{r["maturity_tag"]}</td>
        <td>{fmt(r["highest_clinical_phase"])}</td>
        <td>{fmt(r["chembl_best_pchembl"])}</td>
      </tr>
    """


CSS = """
  :root {
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #0f172a;
    --muted: #64748b;
    --border: #e2e8f0;
    --accent: #3b82f6;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text); font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 32px 24px 80px; }
  h1 { font-size: 24px; margin: 0 0 4px; }
  .sub { color: var(--muted); margin-bottom: 24px; font-size: 13px; }
  h2 { margin: 0; font-size: 20px; }
  h3 { font-size: 13px; margin: 16px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }

  .exec { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; }
  .exec p { margin: 0 0 12px; }
  .exec p:last-child { margin-bottom: 0; }
  .tier-summary { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }

  .controls { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
  .controls input { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; flex: 1; min-width: 200px; }
  .filter-btn { padding: 6px 12px; border: 1px solid var(--border); background: var(--card); border-radius: 6px; cursor: pointer; font-size: 12px; }
  .filter-btn.active { background: var(--text); color: white; border-color: var(--text); }

  .summary-table { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 32px; }
  .summary-table table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  .summary-table th, .summary-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  .summary-table th { background: #f1f5f9; font-weight: 600; cursor: pointer; user-select: none; position: sticky; top: 0; }
  .summary-table th:hover { background: #e2e8f0; }
  .summary-table tbody tr:hover { background: #f8fafc; }
  .summary-table tbody tr:last-child td { border-bottom: none; }

  .tier-pill { display: inline-block; padding: 2px 8px; border-radius: 10px; color: white; font-size: 11px; font-weight: 600; }
  .tier-badge { padding: 6px 12px; border-radius: 8px; color: white; font-size: 11px; font-weight: 600; white-space: nowrap; }

  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; overflow: hidden; }
  .card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: 16px 20px; border-left: 4px solid var(--accent); background: #fafbfd; }
  .card-sub { color: var(--muted); font-size: 12.5px; margin-top: 2px; }
  .composite { font-size: 12px; font-weight: 500; color: var(--muted); margin-left: 8px; }
  .chips { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
  .chip { font-size: 10.5px; padding: 2px 8px; border-radius: 10px; background: #eef2ff; color: #3730a3; font-weight: 500; }
  .chip-surface { background: #dbeafe; color: #1e40af; }
  .chip-secreted { background: #dcfce7; color: #166534; }
  .chip-mhc { background: #fef3c7; color: #92400e; }
  .chip-tm { background: #e0e7ff; color: #3730a3; }
  .chip-focus { background: #fce7f3; color: #9d174d; }
  .chip-drug { background: #d1fae5; color: #065f46; }

  .badge { font-size: 10.5px; padding: 1px 6px; border-radius: 6px; font-weight: 500; }
  .badge-yes { background: #d1fae5; color: #065f46; }
  .badge-no { background: #fee2e2; color: #991b1b; }

  .card-body { padding: 16px 20px 20px; }
  .rationale p { margin: 0 0 8px; }
  .rationale p:last-child { margin-bottom: 0; }

  .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 16px; margin-top: 16px; }
  .kv { font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
  .kv-k { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 2px; }
  .kv-v { word-break: break-word; }

  .breakdown table { width: 100%; border-collapse: collapse; margin-top: 6px; }
  .breakdown td { padding: 4px 0; font-size: 12.5px; }
  .breakdown td:first-child { width: 180px; color: var(--muted); }
  .bar { position: relative; background: #f1f5f9; border-radius: 4px; height: 18px; overflow: hidden; }
  .bar-fill { height: 100%; }
  .bar-label { position: absolute; top: 0; left: 6px; line-height: 18px; font-size: 11px; font-weight: 500; }

  @media (max-width: 700px) {
    .grid { grid-template-columns: 1fr; }
    .card-head { flex-direction: column; }
  }
"""

JS = """
document.querySelectorAll("#summary th").forEach((th, idx) => {
  th.addEventListener("click", () => {
    const table = th.closest("table");
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const desc = !th.classList.contains("sorted-desc");
    table.querySelectorAll("th").forEach(t => t.classList.remove("sorted-asc","sorted-desc"));
    th.classList.add(desc ? "sorted-desc" : "sorted-asc");
    const type = th.dataset.sort || "text";
    rows.sort((a,b) => {
      const av = a.children[idx].dataset.sort ?? a.children[idx].textContent;
      const bv = b.children[idx].dataset.sort ?? b.children[idx].textContent;
      if (type === "num") {
        const an = parseFloat(av); const bn = parseFloat(bv);
        if (isNaN(an) && isNaN(bn)) return 0;
        if (isNaN(an)) return 1;
        if (isNaN(bn)) return -1;
        return desc ? bn - an : an - bn;
      }
      return desc ? bv.localeCompare(av) : av.localeCompare(bv);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});

const search = document.getElementById("search");
let currentTier = "all";
function applyFilters() {
  const q = search.value.trim().toLowerCase();
  document.querySelectorAll(".card").forEach(card => {
    const tier = card.dataset.tier;
    const matchText = !q || card.textContent.toLowerCase().includes(q);
    const matchTier = currentTier === "all" || tier === currentTier;
    card.style.display = (matchText && matchTier) ? "" : "none";
  });
  document.querySelectorAll("#summary tbody tr").forEach(row => {
    const tier = row.dataset.tier;
    const matchText = !q || row.textContent.toLowerCase().includes(q);
    const matchTier = currentTier === "all" || tier === currentTier;
    row.style.display = (matchText && matchTier) ? "" : "none";
  });
}
search.addEventListener("input", applyFilters);
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentTier = btn.dataset.tier;
    applyFilters();
  });
});
"""


def build(report_dir: Path, title: str, subtitle: str) -> Path:
  csv_path = report_dir / "targets_summary.csv"
  md_path = report_dir / "targets_report.md"
  out_path = report_dir / "targets_report.html"

  if not csv_path.exists():
    raise SystemExit(f"missing: {csv_path}")
  if not md_path.exists():
    raise SystemExit(f"missing: {md_path}")

  try:
    rows = list(csv.DictReader(open(csv_path)))
  except OSError as e:
    raise SystemExit(f"cannot read {csv_path}: {e}")
  exec_md, rationales = parse_report_md(md_path.read_text())
  exec_html = (
    md_inline_to_html(exec_md)
    if exec_md
    else "<p><em>No executive summary written.</em></p>"
  )

  tier_counts = {}
  for r in rows:
    tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1
  tier_pills = " ".join(
    f'<span class="tier-pill" style="background:{TIER_COLOR.get(t, "#64748b")}">'
    f"{t.replace('Tier-', 'T').split('-')[0]}: {n}</span>"
    for t, n in sorted(tier_counts.items())
  )

  summary_rows = "\n".join(render_summary_row(r) for r in rows)
  cards_html = "\n".join(render_card(r, rationales) for r in rows)

  page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <h1>{html.escape(title)}</h1>
  <div class="sub">{html.escape(subtitle)}</div>

  <section class="exec">
    <h3 style="margin-top:0">Executive summary</h3>
    {exec_html}
    <div class="tier-summary">{tier_pills}</div>
  </section>

  <div class="controls">
    <input id="search" placeholder="Search gene symbol, protein name, or trait…" />
    <button class="filter-btn active" data-tier="all">All</button>
    <button class="filter-btn" data-tier="Tier-1-priority">Tier-1</button>
    <button class="filter-btn" data-tier="Tier-2-candidate">Tier-2</button>
    <button class="filter-btn" data-tier="Tier-3-watchlist">Tier-3</button>
    <button class="filter-btn" data-tier="Tier-4-deprioritized">Tier-4</button>
  </div>

  <div class="summary-table">
    <table id="summary">
      <thead>
        <tr>
          <th data-sort="text">Gene</th>
          <th data-sort="num" class="sorted-desc">Composite</th>
          <th data-sort="text">Tier</th>
          <th data-sort="text">Loc</th>
          <th data-sort="num">Drug</th>
          <th data-sort="num">Genetics</th>
          <th data-sort="num">Cell ctx</th>
          <th data-sort="num">Safety</th>
          <th data-sort="text">Maturity</th>
          <th data-sort="num">MaxPhase</th>
          <th data-sort="num">Best pIC50</th>
        </tr>
      </thead>
      <tbody>
        {summary_rows}
      </tbody>
    </table>
  </div>

  {cards_html}

</div>

<script>{JS}</script>
</body>
</html>
"""

  out_path.write_text(page)
  return out_path


def main():
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument(
    "--report-dir",
    required=True,
    help="Directory containing targets_summary.csv and targets_report.md",
  )
  ap.add_argument(
    "--title",
    default="Target Prioritization Report",
    help="Page title (default: 'Target Prioritization Report')",
  )
  ap.add_argument(
    "--subtitle",
    default="",
    help="Optional subtitle shown under the H1 (e.g. cohort / contrast description)",
  )
  args = ap.parse_args()

  report_dir = Path(args.report_dir).expanduser().resolve()
  try:
    n_rows = sum(1 for _ in csv.DictReader(open(report_dir / "targets_summary.csv")))
  except OSError as e:
    raise SystemExit(f"cannot read {report_dir / 'targets_summary.csv'}: {e}")
  subtitle = args.subtitle or f"{n_rows} genes · sorted by composite score"

  out_path = build(report_dir, args.title, subtitle)
  print(f"build_html_report: wrote {out_path}  ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
  main()
