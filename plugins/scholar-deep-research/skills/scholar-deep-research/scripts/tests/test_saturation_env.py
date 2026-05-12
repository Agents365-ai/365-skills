"""F1 — SCHOLAR_SATURATION_* env-var overrides honored by both the CLI
and the G2 gate.

The default 20%-new threshold is unreachable for some moderately broad
CS topics. The 0.13.0 fix lets operators relax it without code changes
by setting env vars; both the standalone `saturation` subcommand and
`gate_2` (called from `advance`) must read them.

These tests construct a minimal state that fails saturation under the
defaults (last round 60% new vs. 50% threshold) and passes when
SCHOLAR_SATURATION_NEW_PCT is bumped to 70. We assert behavior at the
function level (`compute_saturation`) and through the CLI (subprocess)
so a refactor that breaks the wiring on either side gets caught.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from research_state import compute_saturation


def _state_with_round_at_pct(pct: float, *, max_cit: int = 0) -> dict:
    """Return a minimal state where the last source round has `pct`% new."""
    # 2 rounds × 10 hits each, second round has `pct`% new papers.
    new_in_r2 = int(round(pct / 100.0 * 10))
    papers = {}
    for i in range(10):
        # Round 1 papers
        pid = f"openalex:R1-{i}"
        papers[pid] = {
            "id": pid, "title": f"r1 paper {i}",
            "first_seen_round": 1, "source": ["openalex"],
            "authors": [f"AuthorR1_{i}"], "venue": "VenueA",
            "citations": 5,
        }
    for i in range(new_in_r2):
        pid = f"openalex:R2-{i}"
        papers[pid] = {
            "id": pid, "title": f"r2 paper {i}",
            "first_seen_round": 2, "source": ["openalex"],
            "authors": [f"AuthorR2_{i}"], "venue": "VenueA",
            "citations": max_cit,
        }
    return {
        "queries": [
            {"source": "openalex", "round": 1, "query": "q1", "hits": 10, "new": 10},
            {"source": "openalex", "round": 2, "query": "q2",
             "hits": 10, "new": new_in_r2},
        ],
        "papers": papers,
    }


class SaturationEnvOverrideTest(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot env so each test can mutate freely.
        self._env_snapshot = {
            k: os.environ.get(k) for k in (
                "SCHOLAR_SATURATION_NEW_PCT",
                "SCHOLAR_SATURATION_MAX_CITATIONS",
                "SCHOLAR_SATURATION_MIN_ROUNDS",
                "SCHOLAR_SATURATION_NEW_AUTHORS_PCT",
                "SCHOLAR_SATURATION_NEW_VENUES_PCT",
            )
        }
        for k in self._env_snapshot:
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        for k, v in self._env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_threshold_blocks_60pct_new(self) -> None:
        state = _state_with_round_at_pct(60.0)
        out = compute_saturation(state)
        self.assertFalse(out["per_source"]["openalex"]["saturated"])
        self.assertEqual(out["threshold_pct"], 50.0)

    def test_env_override_unsticks_60pct_new(self) -> None:
        os.environ["SCHOLAR_SATURATION_NEW_PCT"] = "70"
        # Authors threshold also needs relaxing because every round-2
        # paper has a unique new author in this synthetic state.
        os.environ["SCHOLAR_SATURATION_NEW_AUTHORS_PCT"] = "100"
        state = _state_with_round_at_pct(60.0)
        out = compute_saturation(state)
        self.assertTrue(out["per_source"]["openalex"]["saturated"])
        self.assertEqual(out["threshold_pct"], 70.0)

    def test_max_citations_env_override(self) -> None:
        os.environ["SCHOLAR_SATURATION_NEW_PCT"] = "70"
        os.environ["SCHOLAR_SATURATION_NEW_AUTHORS_PCT"] = "100"
        # New round-2 papers carry a high citation count → blocks
        # saturation under the default max_cit=100.
        state = _state_with_round_at_pct(60.0, max_cit=500)
        out = compute_saturation(state)
        self.assertFalse(out["per_source"]["openalex"]["saturated"],
                         "max_cit=500 should block under default 100")
        # Now bump the env knob and re-evaluate.
        os.environ["SCHOLAR_SATURATION_MAX_CITATIONS"] = "1000"
        out2 = compute_saturation(state)
        self.assertTrue(out2["per_source"]["openalex"]["saturated"])
        self.assertEqual(out2["max_citations_threshold"], 1000)

    def test_min_rounds_env_override_allows_single_round(self) -> None:
        os.environ["SCHOLAR_SATURATION_MIN_ROUNDS"] = "1"
        state = {
            "queries": [
                {"source": "openalex", "round": 1, "query": "q",
                 "hits": 10, "new": 0},
            ],
            "papers": {},
        }
        out = compute_saturation(state)
        self.assertTrue(out["per_source"]["openalex"]["saturated"],
                        "min_rounds=1 should let a single-round source saturate")
        self.assertEqual(out["min_rounds"], 1)

    def test_explicit_kwarg_beats_env(self) -> None:
        # Caller's explicit kwarg wins over env override.
        os.environ["SCHOLAR_SATURATION_NEW_PCT"] = "70"
        state = _state_with_round_at_pct(60.0)
        out = compute_saturation(state, threshold=10.0)
        self.assertFalse(out["per_source"]["openalex"]["saturated"])
        self.assertEqual(out["threshold_pct"], 10.0,
                         "explicit threshold=10 should override env 70")


class SaturationCLIEnvOverrideTest(unittest.TestCase):
    """End-to-end: the CLI also reads env vars (via compute_saturation)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state_path = Path(self._tmp.name) / "state.json"
        # Hand-write state: avoid relying on init+ingest plumbing.
        state = _state_with_round_at_pct(60.0)
        state.update({
            "schema_version": 1,
            "phase": 1,
            "question": "test", "archetype": "literature_review",
            "selected_ids": [], "themes": [], "tensions": [],
            "self_critique": {"findings": [], "resolved": [], "appendix": ""},
        })
        self._state_path.write_text(json.dumps(state))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_cli_honors_env_override(self) -> None:
        from _helpers import run_script
        env = os.environ.copy()
        env["SCHOLAR_SATURATION_NEW_PCT"] = "70"
        env["SCHOLAR_SATURATION_NEW_AUTHORS_PCT"] = "100"
        envelope = run_script(
            "research_state.py",
            ["--state", str(self._state_path), "saturation"],
            env=env,
        )
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["data"]["threshold_pct"], 70.0)
        self.assertTrue(
            envelope["data"]["per_source"]["openalex"]["saturated"],
            f"CLI didn't pick up env override: {envelope['data']}",
        )


if __name__ == "__main__":
    unittest.main()
