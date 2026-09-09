#!/usr/bin/env python3
"""Fetch the latest Pi changelog from the RSS feed and update changelog.md.

Usage: python3 scripts/fetch-changelog.py [output.md]
"""

import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

OUT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "references",
        "changelog.md",
    )
)

RSS_URL = "https://pi.dev/news.xml"


def extract_highlights(content_html):
    """Pull bullet items from the HTML content for a concise summary."""
    # Remove HTML tags, keep li text
    text = re.sub(r"<[^>]+>", "\n", content_html)
    text = html.unescape(text)
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            lines.append(line[2:])
        elif line.startswith("•"):
            lines.append(line[1:].strip())
    # Filter to the most notable items
    highlights = []
    for l in lines:
        if any(
            kw in l.lower()
            for kw in ["new", "added", "changed", "fixed", "breaking", "removed"]
        ):
            if len(highlights) < 10 and l not in highlights:
                highlights.append(l)
    return highlights


def parse_rss():
    """Fetch and parse RSS feed, return list of (version, date, highlights_dict)."""
    print(f"Fetching {RSS_URL}...", file=sys.stderr)
    req = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except Exception as e:
        raise SystemExit(f"Failed to fetch RSS: {e}")

    root = ET.fromstring(data)
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = []

    for item_elem in root.findall(".//item"):
        title = item_elem.findtext("title", "")
        pubdate = item_elem.findtext("pubDate", "")
        desc = item_elem.findtext("description", "")
        content_enc = item_elem.find("content:encoded", ns)
        content_html = str(content_enc.text or "") if content_enc is not None else ""

        # Parse version from title
        m = re.search(r"Pi\s+([\d.]+)", title)
        version = m.group(1) if m else title

        # Parse date
        try:
            date = parsedate_to_datetime(pubdate).strftime("%Y-%m-%d")
        except Exception:
            date = pubdate[:10] if len(pubdate) >= 10 else ""

        # Extract highlights
        highlights = extract_highlights(content_html)
        # Also extract section headers (h3) for structure
        sections = re.findall(r"<h3[^>]*>(.*?)</h3>", content_html, re.IGNORECASE)
        section_texts = [
            html.unescape(re.sub(r"<[^>]+>", "", s)).strip() for s in sections
        ]

        # Build a concise highlights string
        highlight_parts = []
        for st in section_texts:
            # Find bullets under this section
            pattern = rf"<h3[^>]*>{re.escape(st)}</h3>.*?(?=<h3|</content>)"
            match = re.search(pattern, content_html, re.DOTALL | re.IGNORECASE)
            if match:
                section_html = match.group(0)
                bullets = re.findall(r"<li>(.*?)</li>", section_html, re.DOTALL)
                # Get first 2 bullets max
                for b in bullets[:2]:
                    btext = html.unescape(re.sub(r"<[^>]+>", "", b)).strip()
                    if btext:
                        highlight_parts.append(f"{st}: {btext}")
                        break

        items.append(
            {
                "version": version,
                "date": date,
                "title": title,
                "highlights": "; ".join(highlight_parts[:5])
                if highlight_parts
                else desc,
                "sections": section_texts,
            }
        )

    return items


def build_changelog(entries):
    lines = []
    lines.append("# Pi — Changelog")
    lines.append("")
    lines.append("Source: <https://pi.dev/news> · RSS: `https://pi.dev/news.xml`")
    lines.append("")
    lines.append(
        "A reverse-chronological release-notes feed. Fetched from the RSS feed."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh`"
    )
    lines.append("to refresh both the package catalog and this changelog.")
    lines.append("")
    lines.append("## Recent releases")
    lines.append("")
    lines.append("| Version | Date | Highlights |")
    lines.append("| --------- | ------ | ----------- |")
    for e in entries:
        v = e["version"]
        d = e["date"]
        h = e["highlights"][:120]  # keep table compact
        lines.append(f"| **{v}** | {d} | {h} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Fetch live")
    lines.append("")
    lines.append("```bash")
    lines.append("curl -s 'https://pi.dev/news.xml'")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    entries = parse_rss()
    content = build_changelog(entries)
    try:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise SystemExit(f"failed to write {OUT}: {e}")
    print(f"Wrote {len(entries)} entries -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
