"""resolve_search_round() — auto-detects the next round per source.

Closes the trap where every search call defaults to --round 1, every
paper inherits first_seen_round=1, and saturation's max_new_citations
window spans the whole corpus (so a single 932-citation paper blocks
saturation forever). The helper is small but the behavior matters
enough to pin: explicit override wins, missing state defaults to 1,
each source increments independently.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _common import resolve_search_round  # noqa: E402


def _state(path: Path, queries: list[dict]) -> None:
    path.write_text(json.dumps({
        "schema_version": 1,
        "question": "t",
        "archetype": "literature_review",
        "phase": 1,
        "queries": queries,
        "papers": {},
        "selected_ids": [],
        "themes": [],
        "tensions": [],
        "self_critique": {"findings": [], "resolved": [], "appendix": ""},
        "report_path": None,
    }))


class ResolveSearchRoundTest(unittest.TestCase):

    def test_explicit_round_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = Path(tmp) / "s.json"
            _state(s, [{"source": "openalex", "round": 5, "query": "x",
                        "hits": 10, "new": 0}])
            self.assertEqual(
                resolve_search_round(str(s), "openalex", explicit=2), 2)

    def test_missing_state_returns_1(self) -> None:
        self.assertEqual(
            resolve_search_round(None, "openalex", explicit=None), 1)

    def test_unreadable_state_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_search_round(str(Path(tmp) / "missing.json"),
                                     "openalex", explicit=None),
                1)

    def test_corrupt_state_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = Path(tmp) / "s.json"
            s.write_text("{not json")
            self.assertEqual(
                resolve_search_round(str(s), "openalex", explicit=None), 1)

    def test_no_prior_round_for_source_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = Path(tmp) / "s.json"
            _state(s, [{"source": "arxiv", "round": 3, "query": "y",
                        "hits": 1, "new": 1}])
            self.assertEqual(
                resolve_search_round(str(s), "openalex", explicit=None), 1)

    def test_max_round_plus_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = Path(tmp) / "s.json"
            _state(s, [
                {"source": "openalex", "round": 1, "query": "a",
                 "hits": 50, "new": 50},
                {"source": "openalex", "round": 2, "query": "b",
                 "hits": 50, "new": 30},
                {"source": "arxiv", "round": 1, "query": "c",
                 "hits": 50, "new": 50},
            ])
            self.assertEqual(
                resolve_search_round(str(s), "openalex", explicit=None), 3)
            # Per-source independence — arxiv is still on its own counter.
            self.assertEqual(
                resolve_search_round(str(s), "arxiv", explicit=None), 2)

    def test_explicit_round_zero_is_respected(self) -> None:
        # 0 is a legitimate explicit value (None vs 0 distinction matters —
        # this is the whole reason we use None as the sentinel).
        with tempfile.TemporaryDirectory() as tmp:
            s = Path(tmp) / "s.json"
            _state(s, [{"source": "openalex", "round": 5, "query": "x",
                        "hits": 1, "new": 0}])
            self.assertEqual(
                resolve_search_round(str(s), "openalex", explicit=0), 0)


if __name__ == "__main__":
    unittest.main()
