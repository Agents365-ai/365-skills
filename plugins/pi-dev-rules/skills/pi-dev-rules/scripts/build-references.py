#!/usr/bin/env python3
"""Build combined reference markdown files from individual pi doc pages.

Fetches source .md files from the pi GitHub repo, then combines them into the
grouped reference files used by this skill. Run after fetching fresh docs into
a temp directory.

Usage: python3 scripts/build-references.py <src_dir> [output_dir]
"""

import os
import sys

SRC = sys.argv[1]  # temp dir with individual .md files
OUT = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references"
    )
)

# (output_file, [(source_file, header), ...])
BUNDLES = {
    "cli-and-usage.md": [
        ("quickstart.md", "Quickstart"),
        ("usage.md", "Using Pi"),
        ("environment-variables.md", "Environment Variables"),
        ("sessions.md", "Sessions"),
        ("keybindings.md", "Keybindings"),
    ],
    "providers-and-models.md": [
        ("providers.md", "Providers"),
        ("llama-cpp.md", "llama.cpp Router Setup"),
        ("models.md", "Custom Models"),
        ("custom-provider.md", "Custom Providers"),
    ],
    "settings-and-compaction.md": [
        ("settings.md", "Settings"),
        ("compaction.md", "Compaction"),
    ],
    "extending-pi.md": [
        ("extensions.md", "Extensions"),
        ("skills.md", "Skills"),
        ("prompt-templates.md", "Prompt Templates"),
        ("themes.md", "Themes"),
        ("packages.md", "Pi Packages"),
    ],
    "tui-components.md": [
        ("tui.md", "TUI Components"),
    ],
    "security-and-containerization.md": [
        ("security.md", "Security"),
        ("containerization.md", "Containerization"),
    ],
    "session-format.md": [
        ("session-format.md", "Session Format"),
    ],
    "programmatic.md": [
        ("sdk.md", "SDK"),
        ("rpc.md", "RPC Mode"),
        ("json.md", "JSON Event Stream Mode"),
    ],
    "platform-setup.md": [
        ("windows.md", "Windows"),
        ("termux.md", "Termux on Android"),
        ("tmux.md", "tmux"),
        ("terminal-setup.md", "Terminal Setup"),
        ("shell-aliases.md", "Shell Aliases"),
    ],
    "development.md": [
        ("development.md", "Development"),
    ],
}

# Map: output_file → (header_line, source_urls_comment_line)
HEADER_DOCS = {
    "cli-and-usage.md": (
        "# Pi — CLI, Usage, Sessions & Keybindings",
        "Source: https://pi.dev/docs/latest/quickstart, /usage, /environment-variables, /sessions, /keybindings",
    ),
    "providers-and-models.md": (
        "# Pi — Providers & Custom Models",
        "Source: https://pi.dev/docs/latest/providers, /llama-cpp, /models, /custom-provider",
    ),
    "settings-and-compaction.md": (
        "# Pi — Settings & Compaction",
        "Source: https://pi.dev/docs/latest/settings, /compaction",
    ),
    "extending-pi.md": (
        "# Extending Pi — Extensions, Skills, Prompt Templates, Themes, Packages",
        "Source: https://pi.dev/docs/latest/extensions, /skills, /prompt-templates, /themes, /packages\nSee also: `tui-components.md` (custom UI), `session-format.md` (entry/message schema).",
    ),
    "tui-components.md": (
        "# Pi — TUI Components",
        "Source: https://pi.dev/docs/latest/tui",
    ),
    "security-and-containerization.md": (
        "# Pi — Security & Containerization",
        "Source: https://pi.dev/docs/latest/security, /containerization",
    ),
    "session-format.md": (
        "# Pi — Session Format",
        "Source: https://pi.dev/docs/latest/session-format",
    ),
    "programmatic.md": (
        "# Pi — Programmatic Usage (SDK, RPC, JSON)",
        "Source: https://pi.dev/docs/latest/sdk, /rpc, /json",
    ),
    "platform-setup.md": (
        "# Pi — Platform Setup & Development",
        "Source: https://pi.dev/docs/latest/windows, /termux, /tmux, /terminal-setup, /shell-aliases",
    ),
    "development.md": (
        "# Pi — Development (Build from Source)",
        "Source: https://pi.dev/docs/latest/development",
    ),
}

GH_BASE = "https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs"


def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise SystemExit(f"failed to read {path}: {e}")


def write_file(path, content):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise SystemExit(f"failed to write {path}: {e}")
    print(f"  wrote {path}")


def strip_source_comment(lines):
    """Remove the first line if it's a source comment like 'Source: https://...'"""
    while lines and lines[0].strip().startswith("Source:"):
        lines.pop(0)
    return lines


def strip_leading_meta(lines):
    """Remove leading h1 (# Title) and leading blockquote (> ...) lines."""
    while lines:
        stripped = lines[0].strip()
        if stripped == "" or stripped.startswith("# ") or stripped.startswith(">"):
            lines.pop(0)
        else:
            break
    return lines


def strip_trailing_blank_lines(lines):
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def build():
    for out_name, sources in BUNDLES.items():
        hdr = HEADER_DOCS[out_name]
        header = hdr[0] + "\n"
        header += hdr[1] + "\n\n"
        header += "---\n\n"
        header += "> **Auto-built from individual doc pages.**\n"
        header += f"> Sources: {', '.join(GH_BASE + '/' + s[0] for s in sources)}\n\n"

        parts = []
        for src_name, section_header in sources:
            src_path = os.path.join(SRC, src_name)
            if not os.path.exists(src_path):
                print(f"  WARNING: {src_path} not found, skipping", file=sys.stderr)
                continue
            content = read_file(src_path)
            lines = content.split("\n")

            # Remove leading h1, blockquote, and blank lines (we use our own section headers)
            lines = strip_leading_meta(lines)

            # Remove trailing blank lines
            lines = strip_trailing_blank_lines(lines)
            lines = strip_source_comment(lines)

            section_content = "\n".join(lines).strip()
            parts.append(f"## {section_header}\n\n{section_content}")

        full = header + "\n\n---\n\n".join(parts) + "\n"
        out_path = os.path.join(OUT, out_name)
        write_file(out_path, full)

    print("Done building references.")


if __name__ == "__main__":
    build()
