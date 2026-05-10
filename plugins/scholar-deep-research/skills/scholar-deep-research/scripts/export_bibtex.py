#!/usr/bin/env python3
"""export_bibtex.py — emit a bibliography from research_state.json.

Formats:
  - bibtex   (default)  → @article{key, title={...}, ...}
  - csl-json            → list of CSL-JSON items
  - ris                 → RIS records

By default only `selected: true` papers are exported. Pass --all to export
the entire corpus.

The BibTeX citation key is derived from first-author-last + year + first
significant title word — stable and human-readable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from _common import EXIT_VALIDATION, err, maybe_emit_schema, ok, stdout_is_tty
from research_state import load_state

STOPWORDS = {"the", "a", "an", "of", "and", "in", "on", "for", "to", "with",
             "from", "by", "at", "as", "is", "are"}


def cite_key(p: dict[str, Any]) -> str:
    authors = p.get("authors") or []
    last = "anon"
    if authors:
        first = authors[0]
        parts = re.split(r"[,\s]+", first.strip())
        parts = [x for x in parts if x]
        last = parts[-1].lower() if parts else "anon"
    last = re.sub(r"[^a-z]", "", last) or "anon"

    year = p.get("year") or "n.d."

    word = "untitled"
    title = (p.get("title") or "").lower()
    for tok in re.findall(r"[a-z]+", title):
        if tok not in STOPWORDS and len(tok) >= 3:
            word = tok
            break

    return f"{last}{year}{word}"


def escape_bibtex(s: str) -> str:
    if not s:
        return ""
    return (s.replace("\\", r"\\")
             .replace("{", r"\{")
             .replace("}", r"\}")
             .replace("&", r"\&")
             .replace("%", r"\%")
             .replace("$", r"\$")
             .replace("#", r"\#")
             .replace("_", r"\_"))


def to_bibtex(papers: list[dict[str, Any]]) -> str:
    out = []
    seen_keys: dict[str, int] = {}
    for p in papers:
        base = cite_key(p)
        n = seen_keys.get(base, 0)
        seen_keys[base] = n + 1
        key = base if n == 0 else f"{base}{chr(ord('a') + n)}"

        entry_type = "article"
        if "arxiv" in (p.get("source") or []):
            entry_type = "misc"

        fields = []
        if p.get("title"):
            fields.append(f"  title = {{{escape_bibtex(p['title'])}}}")
        if p.get("authors"):
            authors = " and ".join(escape_bibtex(a) for a in p["authors"])
            fields.append(f"  author = {{{authors}}}")
        if p.get("venue"):
            fields.append(f"  journal = {{{escape_bibtex(p['venue'])}}}")
        if p.get("year"):
            fields.append(f"  year = {{{p['year']}}}")
        if p.get("doi"):
            fields.append(f"  doi = {{{p['doi']}}}")
        if p.get("url"):
            fields.append(f"  url = {{{p['url']}}}")
        if p.get("abstract"):
            fields.append(f"  abstract = {{{escape_bibtex(p['abstract'][:1000])}}}")

        out.append(f"@{entry_type}{{{key},\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(out) + "\n"


def to_csl_json(papers: list[dict[str, Any]]) -> str:
    items = []
    for p in papers:
        item: dict[str, Any] = {
            "id": p["id"],
            "type": "article-journal",
            "title": p.get("title") or "",
        }
        if p.get("authors"):
            item["author"] = [
                {"literal": a} for a in p["authors"]
            ]
        if p.get("year"):
            item["issued"] = {"date-parts": [[p["year"]]]}
        if p.get("venue"):
            item["container-title"] = p["venue"]
        if p.get("doi"):
            item["DOI"] = p["doi"]
        if p.get("url"):
            item["URL"] = p["url"]
        if p.get("abstract"):
            item["abstract"] = p["abstract"]
        items.append(item)
    return json.dumps(items, indent=2, ensure_ascii=False)


def to_ris(papers: list[dict[str, Any]]) -> str:
    out = []
    for p in papers:
        lines = ["TY  - JOUR"]
        if p.get("title"):
            lines.append(f"TI  - {p['title']}")
        for a in (p.get("authors") or []):
            lines.append(f"AU  - {a}")
        if p.get("year"):
            lines.append(f"PY  - {p['year']}")
        if p.get("venue"):
            lines.append(f"JO  - {p['venue']}")
        if p.get("doi"):
            lines.append(f"DO  - {p['doi']}")
        if p.get("url"):
            lines.append(f"UR  - {p['url']}")
        if p.get("abstract"):
            lines.append(f"AB  - {p['abstract']}")
        lines.append("ER  -")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="Export bibliography from state.")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--format", choices=["bibtex", "csl-json", "ris"],
                   default="bibtex")
    p.add_argument("--output", help="Write to file (default: stdout)")
    p.add_argument("--all", action="store_true",
                   help="Export all papers, not just selected ones")
    p.add_argument("--raw", action="store_true",
                   help="Force raw text on stdout (no envelope). Useful for "
                        "shell pipelines like `export_bibtex.py --raw > refs.bib`. "
                        "Default: raw when stdout is a TTY, envelope otherwise.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "export_bibtex")
    args = p.parse_args()

    state = load_state(Path(args.state))
    if args.all:
        papers = list(state["papers"].values())
    else:
        papers = [state["papers"][pid] for pid in state["selected_ids"]
                  if pid in state["papers"]]
    if not papers:
        err("no_papers",
            "No papers to export. Pass --all or run `research_state.py "
            "select` first.",
            retryable=False, exit_code=EXIT_VALIDATION)

    if args.format == "bibtex":
        text = to_bibtex(papers)
    elif args.format == "csl-json":
        text = to_csl_json(papers)
    else:
        text = to_ris(papers)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        ok({"output": str(out), "format": args.format, "count": len(papers)})
        return

    # No --output: decide raw text vs envelope by TTY (unless --raw forced).
    # This preserves the `export_bibtex.py --raw > refs.bib` human pipeline
    # while guaranteeing an envelope when an agent captures stdout without
    # knowing to pass --output. Default on an interactive terminal is raw
    # (the pretty-printed JSON envelope is less useful there); default for
    # a piped / captured stdout is the envelope with the body inline.
    if args.raw or stdout_is_tty():
        sys.stdout.write(text)
    else:
        ok({
            "format": args.format,
            "count": len(papers),
            "body": text,
        })


if __name__ == "__main__":
    main()
