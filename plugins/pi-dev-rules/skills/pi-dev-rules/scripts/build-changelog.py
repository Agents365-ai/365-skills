#!/usr/bin/env python3
"""Build references/changelog.md from the changelog in a local Pi checkout.

Reads packages/coding-agent/CHANGELOG.md and renders a compact, newest-first
release table. Nothing is fetched from the network.

Usage: python3 scripts/build-changelog.py <pi_repo_root> [revision] [output.md]
"""

import os
import re
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else ""
REV = sys.argv[2] if len(sys.argv) > 2 else ""
OUT = (
    sys.argv[3]
    if len(sys.argv) > 3
    else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "references",
        "changelog.md",
    )
)

CHANGELOG_REL = "packages/coding-agent/CHANGELOG.md"
ROW_LIMIT = 25
HIGHLIGHT_LIMIT = 150


def strip_markdown(text):
    """Drop links, link trailers, and emphasis so the cell stays compact."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s*\(\[#\d+\][^)]*\)", "", text)
    text = re.sub(r"\s*by\s+\[?@[\w-]+\]?", "", text)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def with_section_prefix(name, bullet):
    """Prefix the bullet with its section name unless the bullet already says it.

    Without this, an '### Added' bullet that starts with "Added ..." would be
    rendered as "Added: Added ...".
    """
    prefix = name.lower()
    if bullet.lower().startswith(prefix) and not bullet[len(prefix) :][:1].isalnum():
        stripped = bullet[len(prefix) :].lstrip(":").strip()
        if stripped:
            return stripped
    return f"{name}: {bullet}"


def first_highlight(body_lines):
    """First bullet of '### New Features', else the first bullet of any section."""
    sections = {}
    current = None
    for line in body_lines:
        heading = re.match(r"^###\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current and line.startswith("- "):
            sections[current].append(line[2:].strip())

    for name in ("New Features",):
        if sections.get(name):
            return strip_markdown(sections[name][0])
    for name, bullets in sections.items():
        if bullets:
            return with_section_prefix(name, strip_markdown(bullets[0]))
    return "(no notes recorded)"


def parse_releases(text):
    releases = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        lines = block.split("\n")
        head = lines[0].strip()
        m = re.match(r"\[?([^\]]+?)\]?\s*(?:-\s*(\d{4}-\d{2}-\d{2}))?$", head)
        if not m:
            continue
        version = m.group(1).strip()
        date = m.group(2) or "unreleased"
        highlight = first_highlight(lines[1:])
        if len(highlight) > HIGHLIGHT_LIMIT:
            highlight = highlight[: HIGHLIGHT_LIMIT - 3].rstrip() + "..."
        releases.append((version, date, highlight))
    return releases


def build(releases, total):
    source = f"`{CHANGELOG_REL}`" + (f" at pi@{REV}" if REV else "")
    lines = [
        "# Pi: Changelog",
        "",
        f"Source: {source}. Built locally from the repository changelog; no network access.",
        "",
        "A reverse-chronological release list, newest first. The highlight column is the first",
        "bullet of each release's `### New Features` section, or its first bullet when that",
        "section is absent, truncated to fit the table.",
        "",
        "---",
        "",
        "**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh` from a Pi",
        "checkout to rebuild this file and the reference bundles.",
        "",
        "## Recent releases",
        "",
        "| Version | Date | Highlights |",
        "| --------- | ------ | ----------- |",
    ]
    for version, date, highlight in releases[:ROW_LIMIT]:
        label = version if date == "unreleased" else f"**{version}**"
        lines.append(f"| {label} | {date} | {highlight} |")

    lines += [
        "",
        "---",
        "",
        "## Full changelog",
        "",
        f"{total} release sections are recorded in the Pi repository, including `[Unreleased]`.",
        "Read the complete, untruncated history there:",
        "",
        "```bash",
        f'less "$PI_REPO/{CHANGELOG_REL}"   # PI_REPO defaults to ~/github/pi',
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    if not REPO:
        raise SystemExit(
            "usage: build-changelog.py <pi_repo_root> [revision] [output.md]"
        )
    path = os.path.join(REPO, CHANGELOG_REL)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise SystemExit(f"failed to read {path}: {e}")

    releases = parse_releases(text)
    if not releases:
        raise SystemExit(f"no release sections found in {path}")

    content = build(releases, len(releases))
    try:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise SystemExit(f"failed to write {OUT}: {e}")
    print(f"Wrote {len(releases)} releases -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
