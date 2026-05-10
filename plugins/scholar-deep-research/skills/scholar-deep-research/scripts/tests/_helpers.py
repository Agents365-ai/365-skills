"""Shared helpers for the CLI contract smoke tests.

No network. No project-specific dependencies beyond the repo itself.
Each helper creates disposable state files in a tmpdir the caller owns.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # scholar-deep-research/
SCRIPTS = ROOT / "scripts"


def run_script(
    script_name: str,
    args: list[str],
    *,
    expect_rc: int | None = 0,
    env: dict[str, str] | None = None,
) -> dict:
    """Run `python scripts/<script_name> <args...>` and parse stdout as JSON.

    If `expect_rc` is not None, asserts the return code matches. Returns the
    parsed envelope. Raises AssertionError with full diagnostics on mismatch.
    """
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if expect_rc is not None and proc.returncode != expect_rc:
        raise AssertionError(
            f"{script_name} exited {proc.returncode}, expected {expect_rc}.\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout: {proc.stdout[:2000]}\n"
            f"stderr: {proc.stderr[:500]}"
        )
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"{script_name} stdout is not valid JSON: {e}\n"
            f"stdout: {proc.stdout[:2000]}\n"
            f"stderr: {proc.stderr[:500]}"
        )
    envelope["_returncode"] = proc.returncode
    envelope["_stderr"] = proc.stderr
    return envelope


def init_state(path: Path, *, question: str = "test", archetype: str = "literature_review") -> None:
    """Create a fresh state file for a test."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for p in (path, Path(str(path) + ".lock")):
        if p.exists():
            p.unlink()
    env = run_script("research_state.py", [
        "--state", str(path), "init",
        "--question", question, "--archetype", archetype,
    ])
    assert env.get("ok"), f"init failed: {env}"


def make_payload(source: str, query: str, round_: int, papers: list[dict]) -> dict:
    return {"source": source, "query": query, "round": round_, "papers": papers}


def dummy_paper(openalex_id: str, **overrides) -> dict:
    paper = {
        "doi": None, "title": f"Paper {openalex_id}", "authors": ["A"],
        "year": 2021, "abstract": f"abstract {openalex_id}",
        "venue": "Venue", "citations": 10,
        "source": ["openalex"], "url": None, "pdf_url": None,
        "openalex_id": openalex_id,
    }
    paper.update(overrides)
    return paper


def all_script_names() -> list[str]:
    """Every `scripts/*.py` that declares a `main()` via `__main__`.

    Skips helpers (`_common.py`, `_locking.py`, `_gates.py`) and the tests
    directory.
    """
    skip = {"__init__.py"}
    out = []
    for f in sorted(SCRIPTS.glob("*.py")):
        if f.name in skip:
            continue
        if f.name.startswith("_"):
            # helpers / private modules
            continue
        out.append(f.name)
    return out
