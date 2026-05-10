"""F4 — `select --include-ids` injects canonical papers ranking missed.

Three behaviours pinned:

  1. Injected ids occupy the top slots of `selected_ids` regardless of
     their rank score (they were the agent's "I know this is canonical"
     override).
  2. The lowest-rank auto-selections drop so total selection size stays
     at `--top` N.
  3. Unknown ids return `unknown_paper_ids` validation error rather
     than silently corrupting the selection.
  4. The override is logged under `state._selection_overrides` for the
     methodology appendix.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


def _stamp_scores(state_path: Path) -> None:
    """Hand-stamp .score on every paper so `select` has something to sort.

    We deliberately bypass rank_papers.py here — testing the select
    subcommand in isolation, not the rank+select chain.
    """
    state = json.loads(state_path.read_text())
    # Paper W0 highest score, W9 lowest.
    for i, pid in enumerate(state["papers"]):
        state["papers"][pid]["score"] = round(1.0 - 0.05 * i, 3)
        state["papers"][pid]["score_components"] = {
            "relevance": 0.5, "citations": 0.5, "recency": 0.5, "venue": 0.5,
        }
    state["ranking"] = {"formula": "test", "ranked_at": "2026-05-10T00:00:00"}
    state_path.write_text(json.dumps(state))


def _ingest_n_papers(state_path: Path, tmp: Path, n: int) -> list[str]:
    """Ingest N dummy papers; return their normalized ids."""
    payload = tmp / "payload.json"
    papers = [dummy_paper(f"W{i}") for i in range(n)]
    payload.write_text(json.dumps(make_payload("openalex", "q", 1, papers)))
    env = run_script("research_state.py", [
        "--state", str(state_path), "ingest", "--input", str(payload),
    ])
    assert env["ok"], f"ingest failed: {env}"
    state = json.loads(state_path.read_text())
    # Order the way the script normalised them (openalex prefix).
    return [p["id"] for p in state["papers"].values()]


class SelectIncludeIdsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_p = Path(self._tmp.name)
        self._state = self._tmp_p / "state.json"
        init_state(self._state)
        self._ids = _ingest_n_papers(self._state, self._tmp_p, n=10)
        _stamp_scores(self._state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_baseline_select_top5_takes_5_highest_scored(self) -> None:
        env = run_script("research_state.py", [
            "--state", str(self._state), "select", "--top", "5",
        ])
        self.assertTrue(env["ok"])
        self.assertEqual(env["data"]["selected"], 5)
        self.assertEqual(env["data"].get("manual_includes"), [])

    def test_include_ids_injects_low_rank_paper_at_top(self) -> None:
        # Pick the LOWEST-scored paper id; it would never make a rank-5 cut.
        worst_id = self._ids[-1]
        env = run_script("research_state.py", [
            "--state", str(self._state), "select", "--top", "5",
            "--include-ids", worst_id,
        ])
        self.assertTrue(env["ok"], f"select failed: {env}")
        ids = env["data"]["ids"]
        self.assertEqual(len(ids), 5)
        self.assertEqual(ids[0], worst_id, "injected id should be at slot 0")
        self.assertEqual(env["data"]["manual_includes"], [worst_id])

    def test_unknown_id_returns_validation_error(self) -> None:
        env = run_script("research_state.py", [
            "--state", str(self._state), "select", "--top", "5",
            "--include-ids", "doi:nonexistent/xyz",
        ], expect_rc=3)  # EXIT_VALIDATION
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], "unknown_paper_ids")
        self.assertIn("doi:nonexistent/xyz", env["error"].get("unknown", []))

    def test_override_logged_to_state(self) -> None:
        worst_id = self._ids[-1]
        run_script("research_state.py", [
            "--state", str(self._state), "select", "--top", "5",
            "--include-ids", worst_id,
        ])
        state = json.loads(self._state.read_text())
        log = state.get("_selection_overrides", [])
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["include_ids"], [worst_id])
        self.assertEqual(log[0]["top"], 5)
        self.assertIn("when", log[0])

    def test_include_ids_drops_lowest_auto_selected(self) -> None:
        """N=5 with one injected → only top-4 of remaining ranked papers fill."""
        worst_id = self._ids[-1]
        env = run_script("research_state.py", [
            "--state", str(self._state), "select", "--top", "5",
            "--include-ids", worst_id,
        ])
        ids = env["data"]["ids"]
        # Rank-ordered list excluding the injected: top 9 by score.
        # Of those, the top-4 should fill the remaining 4 slots.
        # (The 5th-ranked-of-the-9 should NOT be in the selection.)
        expected_auto = self._ids[:4]   # W0..W3 by construction
        self.assertEqual(set(ids[1:]), set(expected_auto),
                         f"got {ids}, expected injected + {expected_auto}")


if __name__ == "__main__":
    unittest.main()
