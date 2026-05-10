"""Phase 1 ingest is capped to prevent runaway loops.

Two caps, both override-able only via env (P2 trust boundary — agents
cannot raise their own ceiling):
  - SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE (default 20): per-source
    ingest event count.
  - SCHOLAR_PHASE1_MAX_ROUNDS (default 5): distinct discovery rounds.

Caps lift automatically once state.phase >= 2, so Phase 4 citation
chase isn't strangled by a Phase 1 envelope.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from _helpers import init_state, make_payload, run_script


def _dummy_paper(suffix: str, *, source: str = "openalex") -> dict:
    return {
        "doi": None,
        "title": f"Paper {suffix}",
        "authors": [f"A{suffix}"],
        "year": 2024,
        "venue": "V",
        "abstract": f"abs {suffix}",
        "citations": 1,
        "source": [source],
        "openalex_id": f"W{suffix}",
    }


def _ingest(state_path: Path, source: str, round_: int, *, env=None,
            paper_suffix: str | None = None, expect_rc=0) -> dict:
    """One ingest event with a single paper, identified by paper_suffix."""
    suffix = paper_suffix or f"{source}-{round_}"
    payload = make_payload(source, "q", round_, [_dummy_paper(suffix, source=source)])
    payload_path = state_path.parent / f"payload-{suffix}.json"
    payload_path.write_text(json.dumps(payload))
    return run_script("research_state.py", [
        "--state", str(state_path),
        "ingest", "--input", str(payload_path),
    ], expect_rc=expect_rc, env=env)


def _env_with(**overrides) -> dict:
    e = dict(os.environ)
    e.update(overrides)
    return e


class Phase1BudgetTest(unittest.TestCase):

    def test_per_source_cap_blocks_overflow(self) -> None:
        """At default cap=20, the 21st openalex ingest is refused."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = _env_with(SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE="3")
            for i in range(3):
                _ingest(state, "openalex", 1, paper_suffix=f"r1-{i}", env=env)
            envelope = _ingest(state, "openalex", 1, paper_suffix="r1-blocked",
                               env=env, expect_rc=3)
            self.assertEqual(envelope["error"]["code"], "phase1_budget_exhausted")
            self.assertEqual(envelope["error"]["limit_kind"], "max_requests_per_source")
            self.assertEqual(envelope["error"]["limit"], 3)
            self.assertEqual(envelope["error"]["current"], 3)
            self.assertEqual(envelope["error"]["source"], "openalex")

    def test_per_source_caps_are_independent(self) -> None:
        """Hitting cap on openalex does not block arxiv ingests."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = _env_with(SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE="2")
            _ingest(state, "openalex", 1, paper_suffix="oa-1", env=env)
            _ingest(state, "openalex", 1, paper_suffix="oa-2", env=env)
            # arxiv at 0/2 — must succeed.
            envelope = _ingest(state, "arxiv", 1, paper_suffix="ax-1", env=env)
            self.assertTrue(envelope["ok"])

    def test_new_round_blocked_at_round_cap(self) -> None:
        """With max_rounds=2, a 3rd distinct round refuses ingest."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = _env_with(SCHOLAR_PHASE1_MAX_ROUNDS="2")
            _ingest(state, "openalex", 1, paper_suffix="r1", env=env)
            _ingest(state, "openalex", 2, paper_suffix="r2", env=env)
            envelope = _ingest(state, "openalex", 3, paper_suffix="r3",
                               env=env, expect_rc=3)
            self.assertEqual(envelope["error"]["code"], "phase1_budget_exhausted")
            self.assertEqual(envelope["error"]["limit_kind"], "max_rounds")

    def test_existing_round_still_ingests_at_round_cap(self) -> None:
        """Round 2 ingest succeeds even when 2 rounds already exist (not a *new* round)."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = _env_with(SCHOLAR_PHASE1_MAX_ROUNDS="2")
            _ingest(state, "openalex", 1, paper_suffix="r1", env=env)
            _ingest(state, "openalex", 2, paper_suffix="r2-a", env=env)
            # Adding another payload tagged round=2 — total distinct rounds
            # stays at 2, so no new-round refusal.
            envelope = _ingest(state, "arxiv", 2, paper_suffix="r2-b", env=env)
            self.assertTrue(envelope["ok"])

    def test_phase_2_lifts_cap(self) -> None:
        """Once advanced past Phase 1, the cap is irrelevant — Phase 4 ingests work."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = _env_with(SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE="1")
            _ingest(state, "openalex", 1, paper_suffix="r1", env=env)
            # Force phase to 4 (citation-chase land) by direct file write —
            # bypasses the gate machine, fine for this unit boundary check.
            doc = json.loads(state.read_text())
            doc["phase"] = 4
            state.write_text(json.dumps(doc))
            # This would have been the 2nd openalex ingest at cap=1; must now succeed.
            envelope = _ingest(state, "openalex", 1, paper_suffix="post-phase",
                               env=env)
            self.assertTrue(envelope["ok"])

    def test_default_caps_allow_realistic_phase1(self) -> None:
        """No env override → 5 sources × a few queries each fits under defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            # 4 sources × 2 ingests each, all in 2 rounds — well under defaults.
            for src in ("openalex", "arxiv", "pubmed", "crossref"):
                _ingest(state, src, 1, paper_suffix=f"{src}-r1")
                _ingest(state, src, 2, paper_suffix=f"{src}-r2")


if __name__ == "__main__":
    unittest.main()
