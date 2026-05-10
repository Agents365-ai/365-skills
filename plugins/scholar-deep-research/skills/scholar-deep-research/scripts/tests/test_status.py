"""research_state.py status — compact "where am I, what's next" snapshot.

Replaces the agent's chained `query summary` + `saturation` + `advance
--check-only` workflow at the start of a session. Status is read-only,
must never mutate, and must not throw on partial state (a Phase 1 init
without queries should still return a valid snapshot — just with a
None next_gate when the gate compute fails).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import init_state, run_script


class StatusFreshStateTest(unittest.TestCase):
    """Fresh init: phase=0, empty everything, next_gate=G1 (which passes)."""

    def test_envelope_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "status"])
            d = env["data"]
            self.assertEqual(d["phase"], 0)
            self.assertEqual(d["archetype"], "literature_review")
            self.assertIn("test", d["question"])
            self.assertEqual(d["papers"]["total"], 0)
            self.assertEqual(d["papers"]["selected"], 0)
            self.assertEqual(d["papers"]["by_tier"], {})
            self.assertEqual(d["papers"]["by_depth"], {})
            self.assertEqual(d["queries"]["total"], 0)
            self.assertEqual(d["queries"]["by_source"], {})
            self.assertEqual(d["synthesis"]["themes"], 0)
            self.assertEqual(d["synthesis"]["tensions"], 0)
            self.assertEqual(d["critique"]["findings"], 0)
            self.assertEqual(d["critique"]["resolved"], 0)
            self.assertFalse(d["critique"]["appendix_populated"])
            self.assertIsNone(d["report_path"])

    def test_g1_visible_as_next(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "status"])
            ng = env["data"]["next_gate"]
            self.assertIsNotNone(ng)
            self.assertEqual(ng["target"], 1)
            self.assertTrue(ng["met"])
            self.assertEqual(ng["failing_checks"], [])


class StatusMidWorkflowTest(unittest.TestCase):
    """Hand-crafted mid-workflow state: counts roll up, next_gate names
    the failing checks."""

    def _write_state(self, path: Path, **overrides) -> None:
        state = {
            "schema_version": 1,
            "question": "Q",
            "archetype": "literature_review",
            "phase": 1,
            "queries": [
                {"source": "openalex", "query": "x", "round": 1,
                 "hits": 50, "new": 50},
                {"source": "openalex", "query": "y", "round": 2,
                 "hits": 50, "new": 0},
                {"source": "arxiv", "query": "z", "round": 1,
                 "hits": 5, "new": 5},
            ],
            "papers": {},
            "selected_ids": [],
            "themes": [],
            "tensions": [],
            "self_critique": {"findings": [], "resolved": [], "appendix": ""},
            "report_path": None,
        }
        state.update(overrides)
        path.write_text(json.dumps(state, indent=2))

    def test_queries_grouped_by_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "status"])
            d = env["data"]
            self.assertEqual(d["queries"]["total"], 3)
            self.assertEqual(d["queries"]["by_source"]["openalex"], 2)
            self.assertEqual(d["queries"]["by_source"]["arxiv"], 1)

    def test_g2_failing_checks_surfaced(self) -> None:
        """Phase 1 with only 2 sources fails sources_breadth (need >=3)."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self._write_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "status"])
            ng = env["data"]["next_gate"]
            self.assertEqual(ng["target"], 2)
            self.assertFalse(ng["met"])
            self.assertIn("sources_breadth", ng["failing_checks"])
            # next_commands should carry the recovery hints
            self.assertGreater(len(env["data"]["next_commands"]), 0)


class StatusSelectedTierBreakdownTest(unittest.TestCase):
    """Selected papers' tier and depth breakdown rolls up correctly."""

    def test_tier_and_depth_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            payload = {
                "schema_version": 1,
                "question": "Q",
                "archetype": "literature_review",
                "phase": 3,
                "queries": [],
                "papers": {
                    "p1": {"id": "p1", "tier": "deep", "depth": "full"},
                    "p2": {"id": "p2", "tier": "deep", "depth": "shallow"},
                    "p3": {"id": "p3", "tier": "skim", "depth": "shallow"},
                    "p4": {"id": "p4", "tier": "defer", "depth": "shallow"},
                },
                "selected_ids": ["p1", "p2", "p3"],  # defer not selected
                "themes": [],
                "tensions": [],
                "self_critique": {"findings": [], "resolved": [],
                                  "appendix": ""},
                "report_path": None,
            }
            state.write_text(json.dumps(payload, indent=2))
            env = run_script("research_state.py",
                             ["--state", str(state), "status"])
            d = env["data"]
            self.assertEqual(d["papers"]["by_tier"], {"deep": 2, "skim": 1})
            self.assertEqual(d["papers"]["by_depth"],
                             {"full": 1, "shallow": 2})


class StatusReadOnlyTest(unittest.TestCase):
    """Status must not mutate the state file."""

    def test_state_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            before = state.read_bytes()
            run_script("research_state.py",
                       ["--state", str(state), "status"])
            after = state.read_bytes()
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
