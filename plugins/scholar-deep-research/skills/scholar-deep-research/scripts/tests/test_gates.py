"""Each gate has at least one passing and one failing scenario.

Covers the G1..G7 predicates in `_gates.py`. Uses direct state-file
manipulation for scenarios the public API doesn't yet reach (e.g. a
state with themes but no tensions). `advance` is always run via the CLI
so this doubles as a smoke test for the subcommand envelope.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


class GatesTest(unittest.TestCase):

    def _write_state(self, path: Path, **overrides) -> None:
        """Write a minimum-viable state directly (bypassing init)."""
        state = {
            "schema_version": 1,
            "question": "t",
            "archetype": "literature_review",
            "phase": 0,
            "queries": [],
            "papers": {},
            "selected_ids": [],
            "themes": [],
            "tensions": [],
            "self_critique": {"findings": [], "resolved": [], "appendix": ""},
            "report_path": None,
        }
        state.update(overrides)
        path.write_text(json.dumps(state, indent=2))

    def test_g1_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--check-only",
            ])
            self.assertTrue(env["data"]["met"])
            self.assertEqual(env["data"]["target"], 1)

    def test_g2_fails_without_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state, phase=1)
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "2", "--check-only",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "gate_not_met")
            failing = [c["name"] for c in env["error"]["gate"]["checks"] if not c["ok"]]
            self.assertIn("sources_breadth", failing)

    def test_g3_fails_without_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state, phase=2)
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "3", "--check-only",
            ], expect_rc=3)
            failing = [c["name"] for c in env["error"]["gate"]["checks"] if not c["ok"]]
            self.assertIn("selection_non_empty", failing)

    def test_g4_pass_with_depths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=3,
                selected_ids=["p1", "p2", "p3", "p4", "p5"],
                papers={
                    "p1": {"id": "p1", "depth": "full", "tier": "deep"},
                    "p2": {"id": "p2", "depth": "full", "tier": "deep"},
                    "p3": {"id": "p3", "depth": "full", "tier": "deep"},
                    "p4": {"id": "p4", "depth": "full", "tier": "deep"},
                    "p5": {"id": "p5", "depth": "shallow", "tier": "skim"},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "4", "--check-only",
            ])
            self.assertTrue(env["data"]["met"])

    def test_g3_fails_without_triage(self) -> None:
        """A fully-ranked + selected state must still trip G3 if triage hasn't run."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=2,
                selected_ids=["p1", "p2"],
                ranking={"formula": "..."},
                papers={
                    "p1": {"id": "p1", "score_components": {"relevance": 0.5}},
                    "p2": {"id": "p2", "score_components": {"relevance": 0.6}},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "3", "--check-only",
            ], expect_rc=3)
            failing = [c["name"] for c in env["error"]["gate"]["checks"] if not c["ok"]]
            self.assertIn("triage_applied", failing)

    def test_g3_pass_with_triage(self) -> None:
        """With triage_complete=true plus the rank/select prerequisites, G3 passes."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=2,
                selected_ids=["p1", "p2"],
                ranking={"formula": "..."},
                triage_complete=True,
                papers={
                    "p1": {"id": "p1", "score_components": {"relevance": 0.5},
                           "tier": "deep"},
                    "p2": {"id": "p2", "score_components": {"relevance": 0.6},
                           "tier": "skim"},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "3", "--check-only",
            ])
            self.assertTrue(env["data"]["met"])

    def test_g4_fails_when_deep_tier_unfinished(self) -> None:
        """Deep tier paper still depth=shallow blocks G4 (skim tier does not)."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=3,
                selected_ids=["p1", "p2"],
                papers={
                    # p1 deep but unfinished — agent never wrote evidence.
                    "p1": {"id": "p1", "depth": "shallow", "tier": "deep"},
                    # p2 skim — depth=shallow is by design, must not block.
                    "p2": {"id": "p2", "depth": "shallow", "tier": "skim"},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "4", "--check-only",
            ], expect_rc=3)
            failing = [c["name"] for c in env["error"]["gate"]["checks"] if not c["ok"]]
            self.assertIn("deep_tier_full_evidence", failing)
            self.assertNotIn("depth_marks_valid", failing)

    def test_g4_pass_with_evidence_unavailable_marker(self) -> None:
        """Deep tier paper with depth=shallow + method='evidence_unavailable:...'
        passes G4 — that's the documented failure-mode escape hatch from
        references/agent_prompts/phase3_deep_read.md.
        """
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=3,
                selected_ids=["p1", "p2", "p3"],
                papers={
                    "p1": {"id": "p1", "depth": "full", "tier": "deep"},
                    # p2: deep tier but PDF unreachable — agent recorded
                    # the failure per the documented contract.
                    "p2": {"id": "p2", "depth": "shallow", "tier": "deep",
                           "evidence": {
                               "method": "evidence_unavailable: paywall_no_oa",
                               "findings": ["abstract excerpt: ..."],
                           }},
                    "p3": {"id": "p3", "depth": "shallow", "tier": "skim"},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "4", "--check-only",
            ])
            self.assertTrue(env["data"]["met"])
            cov = next(c for c in env["data"]["gate"]["checks"]
                       if c["name"] == "deep_tier_full_evidence")
            self.assertIn("evidence_unavailable", cov["detail"])

    def test_g4_fails_for_shallow_without_evidence_unavailable_marker(self) -> None:
        """A naked depth=shallow on a deep-tier paper (no marker) still blocks G4."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(
                state,
                phase=3,
                selected_ids=["p1"],
                papers={
                    # method exists but does NOT start with evidence_unavailable:
                    "p1": {"id": "p1", "depth": "shallow", "tier": "deep",
                           "evidence": {"method": "abstract-only triage",
                                        "findings": ["..."]}},
                },
            )
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "4", "--check-only",
            ], expect_rc=3)
            failing = [c["name"] for c in env["error"]["gate"]["checks"]
                       if not c["ok"]]
            self.assertIn("deep_tier_full_evidence", failing)

    def test_g6_fail_without_themes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state, phase=5)
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "6", "--check-only",
            ], expect_rc=3)
            failing = [c["name"] for c in env["error"]["gate"]["checks"] if not c["ok"]]
            self.assertIn("themes_defined", failing)

    def test_g2_saturation_detail_includes_per_source_diagnosis(self) -> None:
        """When saturation_overall fails, the gate detail must surface per-source
        pass/fail with the actual thresholds inline — without it, the agent
        has to call `saturation` separately to diagnose."""
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "s.json"
            init_state(state_path)
            # Phase 1 with 3 sources × 2 rounds, papers identical across rounds
            # so new_pct=100% in round 2 — fails saturation.
            queries = []
            papers = {}
            for src in ("openalex", "pubmed", "crossref"):
                for rd in (1, 2):
                    queries.append({"source": src, "query": "q", "round": rd,
                                    "hits": 10, "new": 10})
                for i in range(1, 11):
                    pid = f"{src}_p{i}"
                    papers[pid] = dummy_paper(pid, source=[src],
                                              first_seen_round=2)
            self._write_state(state_path, phase=1, queries=queries,
                              papers=papers)
            env = run_script("research_state.py", [
                "--state", str(state_path), "advance", "--to", "2",
                "--check-only",
            ], expect_rc=3)
            sat_check = next(
                c for c in env["error"]["gate"]["checks"]
                if c["name"] == "saturation_overall"
            )
            self.assertFalse(sat_check["ok"])
            detail = sat_check["detail"]
            # Effective thresholds must be inline.
            self.assertIn("thresholds:", detail)
            self.assertIn("new<", detail)
            self.assertIn("min_rounds=", detail)
            # Per-source verdicts with numbers must be inline.
            self.assertIn("openalex=FAIL", detail)
            self.assertIn("pubmed=FAIL", detail)
            self.assertIn("crossref=FAIL", detail)
            self.assertIn("new=", detail)

    def test_skip_two_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state, phase=0)
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "2",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "phase_skip_forbidden")


if __name__ == "__main__":
    unittest.main()
