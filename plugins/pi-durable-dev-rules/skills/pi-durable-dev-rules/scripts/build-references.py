#!/usr/bin/env python3
"""Build the vendored reference bundles from a local Pi checkout.

Reads the upstream markdown files of the pi monorepo and writes the bundles this
skill ships. Nothing is fetched from the network.

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

# (output_file, source_file, section_header)
BUNDLES = {
    "durable-guide.md": [
        ("packages/durable/README.md", "Durable Harness Guide"),
    ],
    "durable-spec.md": [
        ("packages/durable/docs/spec.md", "Pico5 Durable Specification"),
    ],
    "pi-ai-models.md": [
        ("packages/ai/README.md", "pi-ai: Models, Providers, and Tools"),
    ],
    "codemode-sandbox.md": [
        ("packages/codemode/README.md", "pi-codemode: QuickJS Sandbox"),
    ],
}

# Map: output_file → (header_line, note_line)
HEADER_DOCS = {
    "durable-guide.md": (
        "# Durable Harness Guide",
        "Source: `packages/durable/README.md` (`@earendil-works/pi-durable`, v1.2.0)\n"
        "The package's own guide: quick start, concepts, extensions, tools, code mode, the system prompt, "
        "the per-conversation agent, settings, the environment, reload, watching, the inbox, reset and handoff, "
        "compaction, agent events, hooks, forks, subagents, child tasks, the task graph, custom documents, usage, "
        "storage backends, errors, and the runnable examples.\n"
        "Repository-relative links inside the bundled text (`../ai/README.md`, `test/examples/...`) point into the pi "
        "monorepo checkout, not into this skill. The examples they name are catalogued in `durable-recipes.md`.",
    ),
    "durable-spec.md": (
        "# Pico5: Durable Harness Specification",
        "Source: `packages/durable/docs/spec.md` (`@earendil-works/pi-durable`, v1.2.0)\n"
        "The normative specification behind the harness: terms and invariants, core records, documents and mutation "
        "ownership, transactions and storage ownership, tasks and the effect sandwich, submissions and the inbox, "
        "extensions/hooks/tools, the built-in tasks, document observation, the storage contract and its failure model, "
        "the backends, API footguns, and non-goals.\n"
        "A design document for an experimental package, not a frozen API contract. Read `durable-guide.md` for the "
        "public surface first; read this when a rule matters, and read section 12 (API footguns) before shipping.",
    ),
    "pi-ai-models.md": (
        "# pi-ai: Models, Providers, and Tools",
        "Source: `packages/ai/README.md` (`@earendil-works/pi-ai`, v1.2.0)\n"
        "The model layer the harness is built on: provider factories and the built-in provider list, querying and "
        "reading the static model catalog, auth and credential stores, environment variables, defining tools with "
        "TypeBox schemas, constrained sampling, the event reference, image input, usage and cost, retries, and the "
        "message types a harness stores in entries.",
    ),
    "codemode-sandbox.md": (
        "# pi-codemode: QuickJS Sandbox",
        "Source: `packages/codemode/README.md` (`@earendil-works/pi-codemode`, v1.2.0)\n"
        "The sandbox behind the harness's `codemode` tool: what a script may call, the globals the sandbox injects, "
        "the module surface, determinism and memory limits, and the difference between the local and the remote "
        "sandbox. See `durable-guide.md` for how the harness wraps it, and `durable-api.md` for the tool's options.",
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


def strip_leading_meta(lines):
    """Remove leading h1, blockquote, badge, and blank lines (the bundle supplies its own header)."""
    while lines:
        stripped = lines[0].strip()
        if (
            stripped == ""
            or stripped.startswith("# ")
            or stripped.startswith(">")
            or stripped.startswith("<")
        ):
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

    for out_name, sources in BUNDLES.items():
        header_line, note_line = HEADER_DOCS[out_name]
        header = header_line + "\n"
        header += note_line + "\n\n"
        header += "---\n\n"
        header += "> **Auto-built from the pi monorepo.** Rebuild with `scripts/refresh.sh`.\n"
        header += f"> Source: {', '.join(GH_BASE + '/' + s[0] for s in sources)}\n\n"

        parts = []
        for src_name, section_header in sources:
            src_path = os.path.join(REPO, src_name)
            if not os.path.exists(src_path):
                raise SystemExit(f"missing source file: {src_path}")
            lines = read_file(src_path).split("\n")
            lines = strip_trailing_blank_lines(strip_leading_meta(lines))
            parts.append(f"## {section_header}\n\n" + "\n".join(lines).strip())

        write_file(os.path.join(OUT, out_name), header + "\n\n---\n\n".join(parts) + "\n")

    print("Done building references.")


if __name__ == "__main__":
    build()
