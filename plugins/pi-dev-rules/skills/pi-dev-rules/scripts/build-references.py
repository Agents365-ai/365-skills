#!/usr/bin/env python3
"""Build the combined reference markdown files from a local Pi checkout.

Reads individual .md files from the pi monorepo and combines them into the
grouped reference files used by this skill. Nothing is fetched from the network.

Usage: python3 scripts/build-references.py <pi_repo_root> [output_dir]
"""

import os
import sys

REPO = sys.argv[1]  # path to the pi monorepo checkout
OUT = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references"
    )
)

# (output_file, [(repo-relative source_file, header), ...])
BUNDLES = {
    "cli-and-usage.md": [
        ("packages/coding-agent/docs/quickstart.md", "Quickstart"),
        ("packages/coding-agent/docs/usage.md", "Using Pi"),
        (
            "packages/coding-agent/docs/environment-variables.md",
            "Environment Variables",
        ),
        ("packages/coding-agent/docs/sessions.md", "Sessions"),
        ("packages/coding-agent/docs/keybindings.md", "Keybindings"),
    ],
    "providers-and-models.md": [
        ("packages/coding-agent/docs/providers.md", "Providers"),
        ("packages/coding-agent/docs/llama-cpp.md", "llama.cpp Router Setup"),
        ("packages/coding-agent/docs/models.md", "Custom Models"),
        ("packages/coding-agent/docs/custom-provider.md", "Custom Providers"),
    ],
    "settings-and-compaction.md": [
        ("packages/coding-agent/docs/settings.md", "Settings"),
        ("packages/coding-agent/docs/compaction.md", "Compaction"),
    ],
    "extending-pi.md": [
        ("packages/coding-agent/docs/extensions.md", "Extensions"),
        ("packages/coding-agent/docs/skills.md", "Skills"),
        ("packages/coding-agent/docs/prompt-templates.md", "Prompt Templates"),
        ("packages/coding-agent/docs/themes.md", "Themes"),
        ("packages/coding-agent/docs/packages.md", "Pi Packages"),
    ],
    "tui-components.md": [
        ("packages/coding-agent/docs/tui.md", "TUI Components"),
    ],
    "security-and-containerization.md": [
        ("packages/coding-agent/docs/security.md", "Security"),
        ("packages/coding-agent/docs/containerization.md", "Containerization"),
    ],
    "session-format.md": [
        ("packages/coding-agent/docs/session-format.md", "Session Format"),
    ],
    "programmatic.md": [
        ("packages/coding-agent/docs/sdk.md", "SDK"),
        ("packages/coding-agent/docs/rpc.md", "RPC Mode"),
        ("packages/coding-agent/docs/json.md", "JSON Event Stream Mode"),
    ],
    "platform-setup.md": [
        ("packages/coding-agent/docs/windows.md", "Windows"),
        ("packages/coding-agent/docs/termux.md", "Termux on Android"),
        ("packages/coding-agent/docs/tmux.md", "tmux"),
        ("packages/coding-agent/docs/terminal-setup.md", "Terminal Setup"),
        ("packages/coding-agent/docs/shell-aliases.md", "Shell Aliases"),
    ],
    "development.md": [
        ("packages/coding-agent/docs/development.md", "Development"),
    ],
    "chord.md": [
        ("packages/chord/README.md", "Overview"),
        ("packages/chord/src/delta/README.md", "Delta Tracking"),
        ("packages/chord/PLANNING.md", "Implementation Plan"),
    ],
    "agent-harness.md": [
        ("packages/agent/docs/harness.md", "AgentHarness Implementation Specification"),
        ("packages/agent/docs/plugins.md", "Application Hosts and Facets"),
        ("packages/agent/docs/values.md", "Typed Values and Lists"),
        ("packages/agent/docs/rpc.md", "Facet Service RPC"),
        ("packages/agent/docs/telemetry-schema.md", "Telemetry Schemas"),
        ("packages/agent/docs/telemetry.md", "Invocation Context and Telemetry Notes"),
    ],
}

# Map: output_file → (header_line, source_urls_comment_line)
HEADER_DOCS = {
    "cli-and-usage.md": (
        "# Pi: CLI, Usage, Sessions & Keybindings",
        "Source: https://pi.dev/docs/latest/quickstart, /usage, /environment-variables, /sessions, /keybindings",
    ),
    "providers-and-models.md": (
        "# Pi: Providers & Custom Models",
        "Source: https://pi.dev/docs/latest/providers, /llama-cpp, /models, /custom-provider",
    ),
    "settings-and-compaction.md": (
        "# Pi: Settings & Compaction",
        "Source: https://pi.dev/docs/latest/settings, /compaction",
    ),
    "extending-pi.md": (
        "# Extending Pi: Extensions, Skills, Prompt Templates, Themes, Packages",
        "Source: https://pi.dev/docs/latest/extensions, /skills, /prompt-templates, /themes, /packages\nSee also: `tui-components.md` (custom UI), `session-format.md` (entry/message schema).",
    ),
    "tui-components.md": (
        "# Pi: TUI Components",
        "Source: https://pi.dev/docs/latest/tui",
    ),
    "security-and-containerization.md": (
        "# Pi: Security & Containerization",
        "Source: https://pi.dev/docs/latest/security, /containerization",
    ),
    "session-format.md": (
        "# Pi: Session Format",
        "Source: https://pi.dev/docs/latest/session-format",
    ),
    "programmatic.md": (
        "# Pi: Programmatic Usage (SDK, RPC, JSON)",
        "Source: https://pi.dev/docs/latest/sdk, /rpc, /json",
    ),
    "platform-setup.md": (
        "# Pi: Platform Setup & Development",
        "Source: https://pi.dev/docs/latest/windows, /termux, /tmux, /terminal-setup, /shell-aliases",
    ),
    "development.md": (
        "# Pi: Development (Build from Source)",
        "Source: https://pi.dev/docs/latest/development",
    ),
    "chord.md": (
        "# Chord: Application-Composition Runtime",
        "Source: `packages/chord/README.md`, `src/delta/README.md`, `PLANNING.md`\nNot a Pi package: `@earendil-works/chord` is an application-neutral runtime that depends on no other Pi workspace package, and it is not covered by the Pi user docs. `PLANNING.md` is an active implementation plan, not a stable API contract.",
    ),
    "agent-harness.md": (
        "# Pi Agent Harness, Facets, and Services",
        "Source: `packages/agent/docs/harness.md`, `plugins.md`, `values.md`, `rpc.md`, `telemetry-schema.md`, `telemetry.md`\nInternal architecture of the agent harness, not user documentation. `harness.md`, `plugins.md`, and `rpc.md` are implementation specifications; `telemetry.md` is design input and `telemetry-schema.md` is generated. See the shipped CLI docs in the other reference files for user-facing behavior.",
    ),
}

GH_BASE = "https://raw.githubusercontent.com/earendil-works/pi/main"


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
    if not os.path.isdir(REPO):
        raise SystemExit(f"not a directory: {REPO}")

    missing = []
    for out_name, sources in BUNDLES.items():
        hdr = HEADER_DOCS[out_name]
        header = hdr[0] + "\n"
        header += hdr[1] + "\n\n"
        header += "---\n\n"
        header += "> **Auto-built from individual doc pages.**\n"
        header += f"> Sources: {', '.join(GH_BASE + '/' + s[0] for s in sources)}\n\n"

        parts = []
        for src_name, section_header in sources:
            src_path = os.path.join(REPO, src_name)
            if not os.path.exists(src_path):
                print(f"  WARNING: {src_path} not found, skipping", file=sys.stderr)
                missing.append(src_name)
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

    if missing:
        raise SystemExit(f"missing source files: {', '.join(missing)}")
    print("Done building references.")


if __name__ == "__main__":
    build()
