#!/usr/bin/env python3
"""render_report.py — scaffold a Phase 7 report from state, or lint anchors.

Why this exists: the Phase 7 report has a lot of *mechanical* content
(question header, sources counts, themes/tensions assembled from state,
methodology appendix from queries+ranking, self-critique appendix copied
verbatim, bibliography pointer) that the agent re-types from scratch
every time. Read it once from `research_state.json` and emit a fillable
scaffold — the agent only writes prose, not structure.

Two modes:

  - render (default): produce a markdown skeleton with the structural
    slots filled from state. Each thematic section carries its theme
    summary, the bulleted list of papers contributing to it (with
    `[^id]` anchors), and a `<!-- AGENT: ... -->` placeholder where the
    agent fills the synthesis prose.

  - lint (`--lint <path>`): parse a finished or in-progress report and
    verify every `[^id]` anchor refers to a paper actually in
    `state.papers`. Catches typos and stale anchors before the report
    ships.

Both modes are read-only — they never mutate `research_state.json`.
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from _common import (
    EXIT_VALIDATION, err, maybe_emit_schema, ok, set_command_meta,
)
from research_state import load_state


# ---------- helpers ----------


def _slug(question: str) -> str:
    """Filename slug: lowercase, alnum-only, first 6 tokens joined by '-'."""
    tokens = re.findall(r"[a-z0-9]+", (question or "report").lower())
    return "-".join(tokens[:6]) if tokens else "report"


def _short_title(paper: dict[str, Any], n: int = 90) -> str:
    t = (paper.get("title") or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _short_cite(paper: dict[str, Any]) -> str:
    """Brief inline citation: 'Author et al. (year)' or fallback."""
    authors = paper.get("authors") or []
    year = paper.get("year")
    if authors and year:
        first = authors[0].split()[-1] if authors[0] else "?"
        suffix = " et al." if len(authors) > 1 else ""
        return f"{first}{suffix} ({year})"
    if authors:
        return authors[0]
    if year:
        return f"({year})"
    return paper.get("title", "untitled")[:60]


def _papers_for_ids(state: dict[str, Any], ids: list[str]) -> list[dict]:
    return [state["papers"][pid] for pid in ids if pid in state["papers"]]


# ---------- render mode ----------


def _smart_title_case(question: str) -> str:
    """Title-case the question for an H1 without breaking acronyms or hyphens.

    Naive `.title()` (or per-word `.capitalize()`) destroys acronyms like
    LLM, MT, GPT and turns "LLM-as-a-judge" into "Llm-As-A-Judge". This
    preserves any token that is already all-uppercase, capitalises only
    the first letter of regular words, leaves short function words
    lowercase except at position 0, and respects internal hyphens by
    case-mapping each subtoken independently.
    """
    raw = (question or "Report").strip().rstrip(".?!")
    if not raw:
        return "Report"
    lowercase_words = {
        "a", "an", "the", "and", "or", "but", "of", "in", "on", "at",
        "to", "for", "with", "by", "as", "is", "are", "vs",
    }

    def cap_subtoken(sub: str, *, first_in_word: bool) -> str:
        if not sub:
            return sub
        # Preserve all-caps acronyms (LLM, MT, GPT, RAG, NLG, RLHF, …).
        if sub.upper() == sub and any(c.isalpha() for c in sub):
            return sub
        # Preserve mixed-case identifiers (AlpacaEval, OpenAI, ChatGPT) —
        # author-supplied capitalisation is almost always intentional.
        if any(c.isupper() for c in sub[1:]):
            return sub
        # Function words stay lowercase even inside a hyphenated phrase,
        # except as the first subtoken of the word.
        if not first_in_word and sub.lower() in lowercase_words:
            return sub.lower()
        return sub[0].upper() + sub[1:].lower()

    def cap_word(word: str, *, first: bool) -> str:
        if not word:
            return word
        if word.lower() in lowercase_words and not first:
            # short function words stay lower except at position 0
            return word.lower()
        # split on hyphens so each subtoken can preserve acronym shape
        parts = word.split("-")
        return "-".join(
            cap_subtoken(p, first_in_word=(i == 0)) for i, p in enumerate(parts)
        )

    words = raw.split()
    out = [cap_word(w, first=(i == 0)) for i, w in enumerate(words)]
    return " ".join(out)


def _render_header(state: dict[str, Any]) -> str:
    archetype = state.get("archetype", "literature_review")
    title = _smart_title_case(state.get("question") or "Report")
    sel_ids = state.get("selected_ids") or []
    papers = state.get("papers") or {}
    selected = [papers[pid] for pid in sel_ids if pid in papers]
    deep = sum(1 for p in selected if p.get("tier") == "deep")
    skim = sum(1 for p in selected if p.get("tier") == "skim")
    sources = sorted({q.get("source") for q in state.get("queries") or []
                      if q.get("source")})
    return (
        f"# {title} — A {archetype.replace('_', ' ').title()}\n"
        f"\n"
        f"**Question:** {state.get('question', '')}\n"
        f"**Date:** {date.today().isoformat()}\n"
        f"**Archetype:** `{archetype}`\n"
        f"**Sources consulted:** {', '.join(sources) or '(none)'}\n"
        f"**Papers in corpus:** {len(papers)} "
        f"({len(sel_ids)} selected — {deep} deep, {skim} skim)\n"
        f"\n"
        "---\n"
    )


_EXECUTIVE_SUMMARY = (
    "\n## Executive summary\n\n"
    "<!-- AGENT: 3–5 bullets summarizing the report's headline findings.\n"
    "Each bullet should anchor to ≥1 paper via [^id]. Avoid generic\n"
    "claims — specific numbers and named methods. -->\n"
    "\n"
    "- ...\n"
    "- ...\n"
    "- ...\n"
)


_BACKGROUND = (
    "\n## 1. Background\n\n"
    "<!-- AGENT: 2–3 paragraphs defining key terms, scope, and why\n"
    "the question matters. Every non-trivial claim must anchor [^id]. -->\n"
)


_SYNTHESIS = (
    "\n## Synthesis\n\n"
    "<!-- AGENT: this is the section that earns the report. Where do\n"
    "the themes connect? What is the dominant view? Where is the field\n"
    "actually moving? Don't summarize — argue. -->\n"
)


def _render_themes(state: dict[str, Any]) -> str:
    themes = state.get("themes") or []
    if not themes:
        return (
            "\n## 2. Themes\n\n"
            "<!-- AGENT: state.themes is empty — Phase 5 was skipped.\n"
            "Add themes via `research_state.py theme --name ... --paper-ids ...`\n"
            "before rendering, or write theme sections manually here. -->\n"
        )
    out = []
    for i, theme in enumerate(themes, start=2):
        out.append(f"\n## {i}. {theme['name']}\n\n")
        if theme.get("summary"):
            out.append(f"{theme['summary']}\n\n")
        members = _papers_for_ids(state, theme.get("paper_ids") or [])
        if members:
            out.append("Contributing papers:\n\n")
            for p in members:
                out.append(
                    f"- {_short_cite(p)} — {_short_title(p, 80)} "
                    f"[^{p['id']}]\n"
                )
            out.append("\n")
        out.append(
            "<!-- AGENT: synthesize this theme. What does the corpus say?\n"
            "Where does it converge / diverge? Anchor every claim. -->\n"
        )
    return "".join(out)


def _render_tensions(state: dict[str, Any]) -> str:
    tensions = state.get("tensions") or []
    if not tensions:
        return ""
    out = ["\n## Tensions surfaced in synthesis\n\n"]
    for t in tensions:
        out.append(f"### {t.get('topic', 'Untitled tension')}\n\n")
        for i, side in enumerate(t.get("sides") or [], start=1):
            anchors = "".join(f"[^{pid}]" for pid in side.get("paper_ids") or [])
            out.append(
                f"- **Side {i}:** {side.get('position', '')} {anchors}\n"
            )
        out.append("\n")
        out.append(
            "<!-- AGENT: classify the disagreement (empirical /\n"
            "methodological / theoretical) and weigh which side the\n"
            "corpus currently supports, if any. -->\n\n"
        )
    return "".join(out)


_GAPS = (
    "\n## Open questions and gaps\n\n"
    "<!-- AGENT: bullet list of gaps. For each, name what the corpus\n"
    "does NOT cover and pinpoint where you'd start digging. -->\n"
    "\n- Gap 1: ...\n- Gap 2: ...\n- Gap 3: ...\n"
)


def _render_recommendations(state: dict[str, Any]) -> str:
    selected = _papers_for_ids(state, state.get("selected_ids") or [])
    # Top 5 by score component (already-computed during Phase 2 ranking)
    scored = [p for p in selected if p.get("score") is not None]
    scored.sort(key=lambda p: p.get("score", 0), reverse=True)
    top = scored[:5]
    if not top:
        return (
            "\n## Recommendations for further reading\n\n"
            "<!-- AGENT: state.papers carries no scores — Phase 2 ranking\n"
            "was skipped. Pick 3–5 papers manually. -->\n"
        )
    lines = ["\n## Recommendations for further reading\n\n"]
    lines.append(
        "Top-scored papers from the corpus, ranked by Phase 2 score "
        "(see Methodology appendix for the formula):\n\n"
    )
    for i, p in enumerate(top, start=1):
        lines.append(
            f"{i}. **{_short_cite(p)}** — {_short_title(p, 100)} "
            f"[^{p['id']}]\n"
        )
    lines.append(
        "\n<!-- AGENT: optionally add a one-line rationale per pick "
        "(why the reader should start here). -->\n"
    )
    return "".join(lines)


def _render_methodology(state: dict[str, Any]) -> str:
    queries = state.get("queries") or []
    by_source: dict[str, int] = {}
    for q in queries:
        src = q.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
    sources_line = ", ".join(f"{s} ({n} queries)"
                             for s, n in sorted(by_source.items()))
    ranking = state.get("ranking") or {}
    formula = ranking.get("formula", "(no ranking recorded)")
    weights = ranking.get("weights") or {}
    weights_str = ", ".join(f"{k}={v}" for k, v in weights.items()) \
        or "(no weights recorded)"
    sel_ids = state.get("selected_ids") or []
    return (
        "\n## Appendix A — Methodology\n\n"
        f"**Search strategy:** {len(queries)} queries across "
        f"{len(by_source)} federated sources — {sources_line}.\n\n"
        f"**Saturation:** see `python scripts/research_state.py "
        f"--state <state.json> saturation` for the per-source breakdown\n"
        f"that gated Phase 1 → Phase 2.\n\n"
        f"**Ranking formula (Phase 2):**\n"
        f"```\n{formula}\n```\n"
        f"Weights: {weights_str}.\n\n"
        f"**Selection:** top {len(sel_ids)} by score, triaged into "
        f"deep (full-text agent fan-out) and skim (abstract-only stub)\n"
        f"tiers via `skim_papers.py`. Per-paper `score_components` and\n"
        f"`triage_components` are preserved in state.\n"
    )


def _render_critique_appendix(state: dict[str, Any]) -> str:
    appendix = (state.get("self_critique") or {}).get("appendix") or ""
    if appendix:
        return f"\n## Appendix B — Self-critique\n\n{appendix.strip()}\n"
    findings = (state.get("self_critique") or {}).get("findings") or []
    return (
        "\n## Appendix B — Self-critique\n\n"
        f"<!-- AGENT: state.self_critique.appendix is empty "
        f"({len(findings)} findings recorded but no appendix written).\n"
        "Write the appendix via `research_state.py critique --appendix \"...\"`\n"
        "before rendering, or paste the synthesized text here. -->\n"
    )


def _render_bibliography(state: dict[str, Any], slug: str) -> str:
    sel_ids = state.get("selected_ids") or []
    papers = _papers_for_ids(state, sel_ids)
    lines = [
        "\n## Bibliography\n\n",
        "Full BibTeX (with score components and source provenance) "
        f"at `reports/{slug}_{date.today().strftime('%Y%m%d')}.bib`.\n",
        "Generate via:\n\n",
        "```bash\n",
        f"python scripts/export_bibtex.py --state research_state.json \\\n",
        f"  --format bibtex --output reports/{slug}_"
        f"{date.today().strftime('%Y%m%d')}.bib\n",
        "```\n\n",
    ]
    if papers:
        lines.append("Anchor index:\n\n")
        for p in papers:
            doi = p.get("doi") or ""
            doi_part = f" — doi:{doi}" if doi else ""
            lines.append(
                f"[^{p['id']}]: {_short_cite(p)}. "
                f"{_short_title(p, 110)}{doi_part}\n"
            )
    return "".join(lines)


def render(state: dict[str, Any]) -> str:
    return (
        _render_header(state)
        + _EXECUTIVE_SUMMARY
        + _BACKGROUND
        + _render_themes(state)
        + _render_tensions(state)
        + _SYNTHESIS
        + _GAPS
        + _render_recommendations(state)
        + _render_methodology(state)
        + _render_critique_appendix(state)
        + _render_bibliography(state, _slug(state.get("question") or ""))
    )


# ---------- lint mode ----------


# Footnote-style anchor: [^any-non-bracket-text]. Markdown's footnote
# syntax. We deliberately do not match across lines.
_ANCHOR_RE = re.compile(r"\[\^([^\]\s][^\]]*)\]")


def _scan_anchors(text: str) -> tuple[set[str], set[str]]:
    """Return (used, defined) sets of anchor ids.

    `used` are inline `[^id]` references. `defined` are footnote
    definitions of the shape `[^id]: ...` at the start of a line. An
    anchor that is both used and defined appears in both sets.
    """
    used: set[str] = set()
    defined: set[str] = set()
    for line in text.splitlines():
        stripped = line.lstrip()
        # Footnote definition: '[^id]: text'
        m = re.match(r"\[\^([^\]\s][^\]]*)\]:\s*", stripped)
        if m:
            defined.add(m.group(1))
            # also collect any inline anchors inside the definition body
            tail = stripped[m.end():]
            for m2 in _ANCHOR_RE.finditer(tail):
                used.add(m2.group(1))
            continue
        for m2 in _ANCHOR_RE.finditer(line):
            used.add(m2.group(1))
    return used, defined


def lint(state: dict[str, Any], report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        err("report_not_found",
            f"Report file does not exist: {report_path}",
            retryable=False, exit_code=EXIT_VALIDATION,
            path=str(report_path))
    text = report_path.read_text()
    used, defined = _scan_anchors(text)
    known = set(state.get("papers") or {})
    unknown_used = sorted(a for a in used if a not in known)
    unknown_defined = sorted(a for a in defined if a not in known)
    undefined_in_text = sorted(a for a in used
                               if a not in defined and a not in known)
    unused_definitions = sorted(a for a in defined if a not in used)
    return {
        "report_path": str(report_path),
        "anchors_used": len(used),
        "anchors_defined": len(defined),
        "papers_in_state": len(known),
        "unknown_anchors_used": unknown_used,
        "unknown_anchors_defined": unknown_defined,
        "undefined_in_text": undefined_in_text,
        "unused_definitions": unused_definitions,
        "ok": (not unknown_used and not unknown_defined),
    }


# ---------- CLI ----------


def main() -> None:
    p = argparse.ArgumentParser(
        description="Render Phase 7 report scaffold from state, or "
                    "lint [^id] anchors in an existing report.")
    set_command_meta(p, since="0.10.0", tier="read")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument(
        "--output",
        help="Render mode only. Output path. "
             "Default: reports/<slug>_<YYYYMMDD>.md",
    )
    p.add_argument(
        "--lint",
        metavar="REPORT_PATH",
        help="Lint mode: scan REPORT_PATH for [^id] anchors and verify "
             "each refers to a paper in state.papers. Read-only.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Render mode only. Overwrite an existing output file. "
             "Without this, an existing target returns output_exists "
             "(exit 3) so hand edits in a Phase 7 draft aren't clobbered.",
    )
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "render_report")
    args = p.parse_args()

    if args.lint and (args.output or args.force):
        err("inconsistent_input",
            "--lint is mutually exclusive with --output / --force "
            "(lint mode never writes). Pick one mode.",
            retryable=False, exit_code=EXIT_VALIDATION)

    state = load_state(Path(args.state))

    if args.lint:
        result = lint(state, Path(args.lint))
        ok(result)
        return

    text = render(state)
    if args.output:
        out_path = Path(args.output)
    else:
        slug = _slug(state.get("question") or "report")
        out_path = Path("reports") / f"{slug}_{date.today().strftime('%Y%m%d')}.md"
    overwrote = out_path.exists()
    if overwrote and not args.force:
        err("output_exists",
            f"Output path already exists: {out_path}. "
            "Pass --force to overwrite (will not preserve hand edits).",
            retryable=False, exit_code=EXIT_VALIDATION,
            path=str(out_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)

    used, defined = _scan_anchors(text)
    ok({
        "output": str(out_path),
        "bytes": len(text.encode("utf-8")),
        "overwrote_existing": overwrote,
        "anchors_used": len(used),
        "anchors_defined": len(defined),
        "themes": len(state.get("themes") or []),
        "tensions": len(state.get("tensions") or []),
        "selected_papers": len(state.get("selected_ids") or []),
    })


if __name__ == "__main__":
    main()
