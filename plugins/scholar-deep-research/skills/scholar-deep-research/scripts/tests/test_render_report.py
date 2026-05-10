"""render_report.py — Phase 7 scaffold + anchor lint.

Render mode: produces a markdown skeleton from state.themes /
state.tensions / state.queries / state.ranking / state.self_critique
plus a per-paper anchor index. Agent fills only the prose. Verifies
the output keeps the structural slots (headers, contributing-papers
lists, methodology numbers).

Lint mode: walks an existing report, finds every `[^id]` anchor, and
verifies each refers to a paper in `state.papers`. Pins the orphan-
anchor / unknown-id detection.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _helpers import init_state, run_script  # noqa: E402


def _state_with_synthesis(state_path: Path) -> None:
    """Init state and inject a Phase 5-complete corpus + critique."""
    init_state(state_path,
               question="What are the recent advances in SCFMs?")
    s = json.loads(state_path.read_text())
    s["phase"] = 6
    s["queries"] = [
        {"source": "openalex", "query": "x", "round": 1, "hits": 50, "new": 50},
        {"source": "openalex", "query": "y", "round": 2, "hits": 50, "new": 5},
        {"source": "arxiv", "query": "z", "round": 1, "hits": 30, "new": 30},
    ]
    s["papers"] = {
        "doi:10.1/a": {"id": "doi:10.1/a", "doi": "10.1/a",
                       "title": "Paper A", "authors": ["Alice Smith"],
                       "year": 2024, "tier": "deep", "depth": "full",
                       "score": 0.85},
        "doi:10.1/b": {"id": "doi:10.1/b", "doi": "10.1/b",
                       "title": "Paper B", "authors": ["Bob Jones"],
                       "year": 2025, "tier": "deep", "depth": "full",
                       "score": 0.79},
        "doi:10.1/c": {"id": "doi:10.1/c", "doi": "10.1/c",
                       "title": "Paper C", "authors": ["Carol Lee"],
                       "year": 2023, "tier": "skim", "depth": "shallow",
                       "score": 0.65},
    }
    s["selected_ids"] = ["doi:10.1/a", "doi:10.1/b", "doi:10.1/c"]
    s["ranking"] = {
        "formula": "score = 0.4·rel + 0.3·log10(cit+1)/3 + 0.2·rec + 0.1·v",
        "weights": {"alpha": 0.4, "beta": 0.3, "gamma": 0.2, "delta": 0.1},
    }
    s["themes"] = [
        {"name": "Pretraining and scale",
         "summary": "scFMs differ along architecture and corpus size.",
         "paper_ids": ["doi:10.1/a", "doi:10.1/b"]},
        {"name": "Cross-modal extensions",
         "summary": "Spatial + multi-species pretraining is the new frontier.",
         "paper_ids": ["doi:10.1/b"]},
    ]
    s["tensions"] = [
        {"topic": "Do scFMs beat baselines on perturbation?",
         "sides": [
             {"position": "Headline papers claim SOTA",
              "paper_ids": ["doi:10.1/a"]},
             {"position": "Independent benchmarks contradict",
              "paper_ids": ["doi:10.1/c"]},
         ]},
    ]
    s["self_critique"] = {
        "findings": ["finding 1", "finding 2"],
        "resolved": [1, 2],
        "appendix": "## Self-critique findings\n\nSample appendix text.",
    }
    state_path.write_text(json.dumps(s, indent=2))


class RenderModeTest(unittest.TestCase):

    def test_envelope_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            env = run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            d = env["data"]
            self.assertEqual(d["output"], str(out))
            self.assertEqual(d["themes"], 2)
            self.assertEqual(d["tensions"], 1)
            self.assertEqual(d["selected_papers"], 3)
            self.assertGreater(d["bytes"], 1000)
            self.assertTrue(out.exists())

    def test_themes_emit_with_summary_and_papers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            text = out.read_text()
            self.assertIn("## 2. Pretraining and scale", text)
            self.assertIn("## 3. Cross-modal extensions", text)
            self.assertIn("scFMs differ along architecture", text)
            self.assertIn("[^doi:10.1/a]", text)
            self.assertIn("[^doi:10.1/b]", text)

    def test_tensions_emit_with_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            text = out.read_text()
            self.assertIn("Headline papers claim SOTA", text)
            self.assertIn("Independent benchmarks contradict", text)
            self.assertIn("## Tensions surfaced in synthesis", text)

    def test_methodology_appendix_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            text = out.read_text()
            self.assertIn("3 queries across 2 federated sources", text)
            self.assertIn("openalex (2 queries)", text)
            self.assertIn("arxiv (1 queries)", text)
            self.assertIn("0.4·rel + 0.3·log10(cit+1)/3", text)
            self.assertIn("alpha=0.4", text)

    def test_critique_appendix_copied_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            text = out.read_text()
            self.assertIn("Sample appendix text.", text)

    def test_recommendations_use_score_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            text = out.read_text()
            # Highest-scored paper appears first in the recommendations.
            recs_section = text.split("## Recommendations")[1]
            self.assertLess(recs_section.find("[^doi:10.1/a]"),
                            recs_section.find("[^doi:10.1/b]"))

    def test_default_output_path_uses_slug_and_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            # run_script does not chdir, so the default reports/ path
            # resolves against the test runner's cwd. --force lets the
            # test be re-runnable when an artifact from a prior run
            # exists; the assertion is on path *construction*, not
            # overwrite behavior.
            env = run_script("render_report.py", [
                "--state", str(state), "--force",
            ])
            self.assertIn("reports/", env["data"]["output"])
            self.assertIn("what-are-the-recent-advances-in",
                          env["data"]["output"])


class LintModeTest(unittest.TestCase):

    def test_clean_report_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "clean.md"
            report.write_text(
                "# Test\n\n"
                "Claim with anchor [^doi:10.1/a].\n\n"
                "Another [^doi:10.1/b].\n\n"
                "[^doi:10.1/a]: Paper A definition.\n"
                "[^doi:10.1/b]: Paper B definition.\n"
            )
            env = run_script("render_report.py", [
                "--state", str(state), "--lint", str(report),
            ])
            d = env["data"]
            self.assertTrue(d["ok"])
            self.assertEqual(d["unknown_anchors_used"], [])
            self.assertEqual(d["unknown_anchors_defined"], [])
            self.assertEqual(d["anchors_used"], 2)
            self.assertEqual(d["anchors_defined"], 2)

    def test_unknown_anchor_in_text_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "typo.md"
            report.write_text(
                "Claim with typo [^doi:10.1/typo-here].\n"
                "[^doi:10.1/typo-here]: typo'd anchor that doesn't exist in state.\n"
            )
            env = run_script("render_report.py", [
                "--state", str(state), "--lint", str(report),
            ])
            d = env["data"]
            self.assertFalse(d["ok"])
            self.assertIn("doi:10.1/typo-here", d["unknown_anchors_used"])
            self.assertIn("doi:10.1/typo-here", d["unknown_anchors_defined"])

    def test_undefined_in_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "undef.md"
            # Anchor used but not defined and not in state's known papers.
            # Note: real id "doi:10.1/a" IS in state, so don't use it here.
            report.write_text(
                "Claim with [^doi:10.1/missing].\n"
            )
            env = run_script("render_report.py", [
                "--state", str(state), "--lint", str(report),
            ])
            d = env["data"]
            self.assertIn("doi:10.1/missing", d["undefined_in_text"])

    def test_unused_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "unused.md"
            report.write_text(
                "Claim with [^doi:10.1/a].\n\n"
                "[^doi:10.1/a]: Definition.\n"
                "[^doi:10.1/b]: Also defined but not cited inline.\n"
            )
            env = run_script("render_report.py", [
                "--state", str(state), "--lint", str(report),
            ])
            d = env["data"]
            self.assertTrue(d["ok"])  # both ids are in state — clean
            self.assertIn("doi:10.1/b", d["unused_definitions"])

    def test_missing_report_path_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            env = run_script("render_report.py", [
                "--state", str(state),
                "--lint", str(Path(tmp) / "no-such-file.md"),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "report_not_found")


class OverwriteSafetyTest(unittest.TestCase):
    """R1 follow-up: render must not silently clobber an existing file."""

    def test_default_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            out.write_text("USER EDITS — do not lose")
            env = run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "output_exists")
            self.assertEqual(out.read_text(), "USER EDITS — do not lose")

    def test_force_allows_overwrite_and_reports_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "report.md"
            out.write_text("stale")
            env = run_script("render_report.py", [
                "--state", str(state), "--output", str(out), "--force",
            ])
            self.assertTrue(env["ok"])
            self.assertTrue(env["data"]["overwrote_existing"])
            self.assertIn("Literature Review", out.read_text())
            self.assertNotIn("stale", out.read_text())

    def test_overwrote_existing_false_for_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            out = Path(tmp) / "fresh.md"
            env = run_script("render_report.py", [
                "--state", str(state), "--output", str(out),
            ])
            self.assertTrue(env["ok"])
            self.assertFalse(env["data"]["overwrote_existing"])


class ModeMutexTest(unittest.TestCase):
    """R2 follow-up: --lint and --output are mutually exclusive."""

    def test_lint_with_output_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "report.md"
            report.write_text("body")
            out = Path(tmp) / "out.md"
            env = run_script("render_report.py", [
                "--state", str(state),
                "--lint", str(report),
                "--output", str(out),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "inconsistent_input")
            self.assertFalse(out.exists())

    def test_lint_with_force_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            _state_with_synthesis(state)
            report = Path(tmp) / "report.md"
            report.write_text("body")
            env = run_script("render_report.py", [
                "--state", str(state),
                "--lint", str(report),
                "--force",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "inconsistent_input")


if __name__ == "__main__":
    unittest.main()
